# Implementation Plan — News Watch digest stuck-loop fix

**Status:** ready for a future agent to execute. **Type:** focused sprint (live mailer + data cleanup + deploy). **Do NOT** hot-edit on prod without the steps below.

> Authored 2026-06-11 from a read-only investigation. Confirm every "verify" step against the live DB/logs before changing code — the diagnosis below is evidence-backed but the agent owns final verification.

> **UPDATE 2026-06-11 (afternoon): data repair already executed live + all owner decisions locked.** See §6 for the locked decisions and §4 Step 0/5 for what was already done. Verified facts from prod DB (2026-06-11):
> - **FOUR stuck digests, not three**: broadcast **79** (5–19 May) failed identically. Each sent ~250 on its Monday then zero after; the same **248–250 subscribers** (send order = subscriber signup order) missed ALL four issues.
> - **Urgent alerts are broken too**: broadcasts **83** (8 Jun) and **84** (9 Jun) FAILED with **all ~335 recipients PENDING, zero sent** — the audience exceeds Brevo's 300/day quota, the pre-flight refuses, and the broadcast is marked FAILED. As coded, a full-list urgent alert can NEVER send. Fix in scope (same root cause).
> - **Repair done 2026-06-11**: broadcast 82's subject set to its big-story headline, status flipped FAILED→SENDING, `sjktconnect-resume-sending` triggered manually → its 250 pending recipients received the catch-up (12:14–12:19 MYT); 82 now **SENT** (500/500 processed: 463 delivered, 32 bounced, 5 awaiting webhook). Broadcasts **79/80/81/83/84 set to CANCELLED**. Cross-checked against user's Brevo log export: zero duplicate sends.
> - Step 5's repair command is therefore **no longer needed for 79–84** — but keep a slimmed idempotent version if useful for future incidents, or drop it.

---

## 1. Symptom (confirmed)
The "fortnightly" News Watch digest sends **every Monday**, and every issue covers **"5 May → today"** — a window that never advances and keeps growing (20 → 27 → 34 days across 25 May / 1 Jun / 8 Jun). Roughly the first 250 subscribers receive each issue; the rest never do.

Evidence (Cloud Run job logs, `sjktconnect-news-digest` + `sjktconnect-resume-sending`):
```
2026-05-25  Coverage: 2026-05-05 to 2026-05-25 → Broadcast 80 → first batch sent, 250 pending
2026-06-01  Coverage: 2026-05-05 to 2026-06-01 → Broadcast 81 → first batch sent, 248 pending
2026-06-08  Coverage: 2026-05-05 to 2026-06-08 → Broadcast 82 → first batch sent, 250 pending
resume-sending → QuotaExceededError: Broadcast 80 planned 250 sends but Brevo has 50 remaining
                 today (quota=300, used=250).  [same for 81, 82]
```

## 2. Root cause (the chain)
1. **Cron is weekly, not fortnightly.** `sjktconnect-fortnightly-digest` schedule = `0 9 * * 1` (every Monday). The name lies.
2. **Brevo quota collision.** ~500 subscribers, Brevo free tier = 300/day. Compose sends the first 250 at 09:00 (quota now 50 left). The `resume-sending` job runs at 10:00 **the same day**, needs 250, only 50 remain → `QuotaExceededError`.
3. **Transient error treated as fatal.** `broadcasts/services/sender.py:173-175` (`resume_broadcast`) — a bare `except Exception` marks the broadcast `FAILED` on the quota error. A quota error is *transient* (tomorrow there is quota), not terminal.
4. **FAILED is never retried.** `resume_broadcast` only acts on broadcasts in `SENDING` status (sender.py:130-132). Once `FAILED`, the ~250 pending recipients are never sent, and the row is stuck `FAILED`.
5. **FAILED freezes the anchor.** `compose_news_digest.py._get_since_date()` does `.exclude(status=FAILED)`, so it can't see broadcasts 80/81/82 → it returns the last *good* digest's `coverage_end_date` (4 May) + 1 = **5 May**, forever. And `_should_skip()` only counts `[SENT, SENDING, DRAFT]`, so a FAILED prior digest doesn't suppress the next Monday's run → recompose weekly.

**Net:** weekly recompose of an ever-growing "since 5 May" digest; half the list gets it, the anchor never moves.

## 3. Files in scope
- `backend/broadcasts/services/sender.py` — `resume_broadcast` quota handling (the core fix).
- `backend/broadcasts/management/commands/compose_news_digest.py` — `_get_since_date` / `_should_skip` robustness.
- The Cloud Scheduler `sjktconnect-fortnightly-digest` cron (GCP, via `gcloud` or `backend/scripts/update_jobs.sh` if schedules are managed there).
- A one-off **data-repair** management command (new) for the stuck broadcasts + anchor.
- Tests under `backend/broadcasts/tests/`.

## 4. Fix steps (ordered)

### Step 0 — stop the bleed — NOT NEEDED (superseded 2026-06-11)
The scheduler can stay ENABLED: with broadcast 82 now SENT (11 Jun), the old code's own `_should_skip` (7-day window vs SENT) correctly skips Mon 15 Jun, and the anchor now reads 82's coverage_end (8 Jun) so it no longer rewinds to 5 May. **Hard deadline instead: deploy the fix before Mon 22 Jun 09:00 MYT** (see Step 4). If the sprint slips past 21 Jun, THEN pause the scheduler with the command below and un-pause after deploy:
`gcloud scheduler jobs pause sjktconnect-fortnightly-digest --location=asia-southeast1 --project=sjktconnect --account=admin@tamilfoundation.org`

### Step 1 — make a transient quota error non-fatal (the key fix)
In `resume_broadcast` (sender.py), catch `QuotaExceededError` **separately** from the generic `except Exception`. On quota exhaustion the broadcast must stay `SENDING` (not `FAILED`) so the **next day's** resume run completes it. Only truly unexpected errors should set `FAILED`.
- Verify `QuotaExceededError` is the class raised (search sender.py for its definition).
- Same review for `send_broadcast`'s initial-send path (sender.py:102-103) — a quota error there should also leave the broadcast resumable, not `FAILED`.

### Step 2 — confirm the drain-over-days then works
With Step 1, the intended behaviour returns: compose sends 250 (day 1), the broadcast stays `SENDING`, next day's 10:00 resume sends the remaining ~250 (quota reset to 300) → `SENT`. **Verify** the daily `resume-sending` job actually targets all `SENDING` broadcasts (not just the latest). If it only resumes one, fix it to drain all `SENDING` rows.

### Step 3 — make the anchor robust (don't let a failure freeze coverage)
Decide and implement the intended semantics (owner decision in §6):
- **Recommended:** `_get_since_date` should anchor on the coverage of the last digest that **was actually composed** (SENT *or* SENDING *or* even FAILED), so a hiccup never rewinds the window to a months-old date. A failed *send* should re-attempt the **same** window, not start a new growing one.
- Correspondingly, `_should_skip` should treat a recent FAILED/SENDING digest as "already covered" so it doesn't recompose a fresh window each run.
- The `7`-day skip window is half a fortnight — replace it with the **14-day coverage-anchored guard defined in Step 4** (skip unless `today − last coverage_end ≥ 14 days`). This guard is now load-bearing (it IS the fortnightly cadence), so it needs solid regression tests.

### Step 4 — fix the cadence (DECIDED: weekly cron + 14-day coverage guard)
**Owner locked 2026-06-11: keep the weekly Monday cron (`0 9 * * 1`) unchanged; the fortnightly logic lives in the skip guard.** Rationale: the owner wants the next full digest on **Monday 22 June** (covering 9–22 Jun), which is the 4th Monday — a 1st/3rd-Monday cron could never fire then.
- Guard rule (precise): **skip unless `today − last_digest.coverage_end_date >= 14 days`**, anchored on **coverage_end_date** of the latest non-cancelled NEWS_DIGEST — NOT on `sent_at` (82 finished sending 11 Jun; a sent_at-based 13/14-day guard would wrongly skip 22 Jun: 22−11 = 11 days. Coverage-based: 22−8 = 14 → sends). This yields a clean every-14-days cadence: 22 Jun, 6 Jul, 20 Jul…
- Expected behaviour with TODAY's deployed (old) code, before the sprint lands: Mon 15 Jun → `_should_skip` sees 82 SENT within 7 days → skips (correct). **The sprint MUST deploy before Mon 22 Jun**, otherwise the old resume-at-10:00-same-day quota collision recurs on the 22 Jun send.
- The scheduler name `sjktconnect-fortnightly-digest` is now accurate-by-guard; optionally leave as is.

### Step 5 — data repair — DONE 2026-06-11 (manually, verified)
Already executed against prod (see UPDATE block at top): 82 subject→headline, 82 FAILED→SENDING→resumed→**SENT** (all 500 recipients processed, zero duplicates — cross-checked against the owner's Brevo log export), 79/80/81/83/84 → CANCELLED. The anchor now correctly reads coverage_end = 8 Jun from broadcast 82.
Remaining for the agent: nothing mandatory. Optionally generalise this into a small `repair_stuck_digests --dry-run` command for future incidents; otherwise skip.

### Step 6 — tests (regression, must fail before the fix)
- `resume_broadcast` on `QuotaExceededError` → broadcast stays `SENDING`, not `FAILED`; next run with quota available → `SENT`.
- `_get_since_date` advances after a partial/failed send (does not rewind to a stale date).
- `_should_skip` suppresses a duplicate compose within the fortnight window.
- A two-day drain scenario (250 then 250) reaches `SENT` and the next compose starts from `coverage_end + 1`.

### Step 7 — deploy + verify
- Run `pytest` + `npm test`; record the **actual** counts (lesson #96).
- Deploy `sjktconnect-api`, then **MANDATORY** `./backend/scripts/update_jobs.sh` (jobs carry pinned images — skipping this caused the 2026-05-20 silent-rot).
- Apply the scheduler cron change; run the `repair_stuck_digests` command on prod (dry-run first).
- **Un-pause** `sjktconnect-fortnightly-digest`.
- Verify on the next fire: coverage window is ~14 days (not 40+), it reaches `SENT` over ≤2 days, and the following run's `since` = previous `coverage_end + 1`.

### Step 8 — close the monitoring gap
The job exits `0` every week (it "succeeds" while broken), so the job-failure alert never fired. Add a check that catches *this* class:
- Alert / log-metric on any `Broadcast` ending `status=FAILED`, **or**
- A guard in compose that warns/aborts if the computed coverage window exceeds, say, 21 days (a stuck anchor), **or**
- A weekly assertion that the digest `coverage_start` advanced since the last issue.

## 5. Out of scope / related
- `monthly-blast` scheduler is separately **PAUSED** pending Sprint 24 — different issue, don't conflate.
- Brevo capacity: 500 subs vs 300/day is structural. The fortnightly digest **must** fan out over 2 days regardless; Step 1 makes that work. If sends grow, consider a higher Brevo tier (separate decision).

## 6. Owner decisions — ALL LOCKED 2026-06-11 (no open questions for the agent)
1. **Cadence:** weekly Monday cron + **14-day coverage-anchored skip guard** (see Step 4 for the precise rule and why fortnightly-cron was rejected). Target timeline: 15 Jun skip → **22 Jun full digest covering 9–22 Jun** → every 14 days after.
2. **Catch-up:** DONE 2026-06-11 — broadcast 82 resumed to its 250 pending recipients (the people who'd missed every issue since 5 May); 79/80/81 cancelled. No further catch-up needed.
3. **Anchor semantics:** CONFIRMED — coverage only advances when an issue is genuinely delivered; a failed send re-attempts the SAME window. News is never skipped.
4. **Stale urgent alerts 83/84:** CANCELLED 2026-06-11 (news gone cold). Fix-forward only.

## 6b. Additional scope locked 2026-06-11
- **Urgent-alert quota fix:** an alert audience (~335) larger than the daily quota (300) must be allowed to drain across days (stay SENDING / resumable), not refuse-and-FAIL at pre-flight. Same `sender.py` quota-handling fix; verify `send_urgent_alerts` path too.
- **Digest subject = big-story headline:** in `compose_news_digest.py` (line ~183), use `digest["big_story"]["title"]` as the email subject, falling back to `f"News Watch — {period_label}"` when no big story exists. (Owner saw "News Watch — 5 May 2026 – 8 Jun 2026" and prefers the headline; precedent set manually on broadcast 82.)
- **Sender name per broadcast type:** `_send_single_email` in `sender.py` hardcodes `"SJK(T) Connect"`. Change to **"SJK(T) News"** for NEWS_DIGEST and URGENT_ALERT; keep "SJK(T) Connect" for MONTHLY_BLAST and everything else. Email stays noreply@tamilschool.org (DKIM unaffected).

## 7. Definition of done
- Cron fires fortnightly; coverage window ~14 days and advances each issue; broadcasts reach `SENT`; all subscribers receive each issue over ≤2 days; a FAILED digest can no longer freeze the anchor; regression tests cover the quota-resume and anchor-advance paths; a monitor exists for FAILED digests / stuck windows; `update_jobs.sh` run; scheduler un-paused; CHANGELOG + retro written.
