# Retrospective — News Digest Stuck-Loop Fix (2026-06-11)

Ad-hoc incident sprint between Sprint 23 and Sprint 24. Investigated, repaired live data, and shipped the code fix in a single day.

## What Was Built

Proof references per lesson 102 — every claim cites the code that landed (commit `d2f6269`, deployed as `sjktconnect-api-00119-92c`, all 7 jobs synced via `update_jobs.sh`).

- **Quota errors are transient, never terminal** — `backend/broadcasts/services/sender.py`: `_quota_allowance()` replaces `_enforce_quota()`; `send_broadcast`/`resume_broadcast` send `min(planned, remaining)` and stay `SENDING`; separate `except BrevoQuotaError` keeps probe failures non-terminal. Generic `except Exception → FAILED` retained for genuinely unexpected errors.
- **Fortnightly cadence anchored in data** — `compose_news_digest.py`: `FORTNIGHT_DAYS = 14`; `_should_skip()` compares today to the last SENT/SENDING/DRAFT digest's `coverage_end_date`. Cron stays weekly Monday; 15 Jun skips, 22 Jun sends 9–22 Jun.
- **Anchor rule codified** — `_get_since_date()` excludes FAILED + CANCELLED: a failed send re-attempts the same window; coverage never silently skips a fortnight.
- **Stuck-anchor tripwires** — compose warns >21-day window, aborts >35 (`CommandError`) unless `--force-window`; checked before Gemini spend.
- **FAILED sweep** — `resume_sending.py` `_fail_on_recent_failed_broadcasts()`: daily job exits non-zero (`BROADCAST_FAILED_ALERT`) while any broadcast is FAILED (updated <7 days), after draining healthy ones.
- **Headline subjects** — `_digest_subject()` uses the big story title, ASCII-sanitised (lesson 21), 150-char cap, dated fallback.
- **Per-kind sender name** — `SENDER_NAMES_BY_KIND`: "SJK(T) News" for NEWS_DIGEST/URGENT_ALERT.
- **`Broadcast.Status.CANCELLED` formalised** — migration `broadcasts/0007` (choices-only); status was already in prod data from two manual repairs.

**Live data repair (pre-sprint, same day):** broadcast 82 subject → headline, FAILED → SENDING, resume job triggered manually → 250 catch-up emails sent 12:14–12:19 MYT (cross-checked against the owner's Brevo log export: zero duplicates; recipient #250 punesselvam9@gmail.com confirmed DELIVERED). Broadcasts 79/80/81 (duplicate stuck digests) + 83/84 (stale urgent alerts) → CANCELLED.

## What Went Well

- **Evidence-first repair.** Every claim was verified against the prod DB before acting: the "Brevo drains over a couple of days" hypothesis was disproven with recipient-level data (zero sends on non-Mondays; the same 248 subscribers pending in all four issues), which changed the catch-up decision.
- **The catch-up cost zero new code.** Broadcast 82 already contained exactly the right content (5 May–8 Jun) and exactly the right audience (the 250 left-out people). Re-opening it beat composing anything new.
- **Owner decisions locked before implementation.** Cadence, catch-up handling, anchor semantics, sender naming, and subject style were all decided in conversation before a line of code changed — the implementation had zero open questions.
- **One deploy.** Within the ≤2 budget; full suite green first (`1375 passed, 37 warnings, 6 subtests passed in 213.09s`).

## What Went Wrong

1. **Four digest issues failed silently for five weeks.**
   - *Symptom:* same ~250 subscribers got nothing 5 May–8 Jun; coverage window frozen and growing.
   - *Root cause:* `resume_broadcast`'s bare `except Exception` treated a transient quota error as terminal (FAILED), and every involved job still exited 0 — the failure was invisible to the job-failure alert, and the skip/anchor logic quietly absorbed the breakage week after week.
   - *System change:* exception classification in sender.py (transient → stay resumable); `resume_sending` now exits non-zero while a FAILED broadcast exists; compose aborts on an impossibly wide window. Lessons added to `docs/lessons.md`.

2. **Sprint 23's quota pre-flight made urgent alerts permanently unsendable.**
   - *Symptom:* broadcasts 83/84 FAILED with all ~335 recipients pending — zero urgent emails sent.
   - *Root cause:* the pre-flight was designed as refuse-at-start (correct goal: never half-send blindly), but with an audience larger than the daily quota, "refuse" meant "never send", and the refusal was then marked FAILED by the same bare except. The fix for one incident (duplicate blast) created the next one — the interaction with audiences > quota was never tested.
   - *System change:* allowance model (send what fits, drain the rest) replaces refuse-at-start; regression test covers audience > quota explicitly.

3. **Production data used a status the model didn't define.**
   - *Symptom:* `CANCELLED` rows existed in prod (manual repair 2026-05-02) while `Broadcast.Status` had no such choice; new code referencing `Status.CANCELLED` would have crashed if the gap hadn't been caught during this sprint.
   - *Root cause:* a manual data repair invented a status ad-hoc and nobody formalised it.
   - *System change:* migration 0007 formalises CANCELLED with documented semantics; rule added to lessons.md — any status value written to prod must exist in the model's choices in the same change.

## Design Decisions

Logged in `docs/decisions.md`: *Weekly cron + data-anchored 14-day guard over a true fortnightly cron* (reverses the plan's initial recommendation; driven by the owner's 22 Jun timeline — a 1st/3rd-Monday cron cannot fire on a 4th Monday — and by the steadier every-14-days cadence).

## Numbers

- Backend tests: `1375 passed, 37 warnings, 6 subtests passed in 213.09s` (+30 new)
- Frontend tests: unchanged by this sprint (no frontend files touched); suite re-run at close for the combined record
- Files changed: 10 (6 modified, 4 added) — commit `d2f6269`
- Deploys: 1 (api `00118-5w4` → `00119-92c`), 7/7 jobs synced (also closes the Sprint 23 "pre-65f9720 job images" follow-up)
- Catch-up emails sent: 250 (12:14–12:19 MYT), 0 duplicates
- Broadcasts repaired: 82 → SENT; 79, 80, 81, 83, 84 → CANCELLED

## Verification due

- **Mon 15 Jun ~09:05 MYT**: `sjktconnect-news-digest` log shows "Skipping — the last digest's coverage ended fewer than 14 days ago".
- **Mon 22 Jun ~09:10 MYT**: new digest composed covering **9 Jun – 22 Jun**, from "SJK(T) News", subject = big-story headline, ~250 sent Monday.
- **Tue 23 Jun ~10:05 MYT**: resume job drains the remaining ~245 → broadcast SENT.
