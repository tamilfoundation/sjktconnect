# Sprint 23 — Monthly Digest Quality Pass

**Status**: Plan accepted by user 2026-05-02. Implementation now paused for a STRONGER reason: a duplicate April-blast incident on 2026-05-02 forced both monthly-blast and resume-sending schedulers to be paused. Sprint 23 must land tasks #4a (Brevo quota check) AND #4b (duplicate-broadcast guard) BEFORE the schedulers can be safely re-enabled. See "Incident: duplicate April blast" section below.
**Last updated**: 2026-05-02
**Triggered by**: April 2026 digest post-mortem (2026-05-01)
**Prior plan**: `~/.claude/projects/C--Users-tamil-Python/memory/sjktconnect_sprint23_plan.md` (user-confirmed scope)
**Language scope**: English only (trilingual deferred per user direction)

## Current state on disk (snapshot at 2026-05-02)

This sprint is partly in flight. Some implementation was committed under a Sprint 22 docs label (commit `4fa3873`) before the Sprint 23 plan was formally accepted. Resumption work must reconcile against that commit, not start from a clean slate.

**Already on disk via commit `4fa3873`**:
- `backend/broadcasts/services/blast_aggregator.py` — count/sample separation (most of task #2)
- `backend/broadcasts/services/monthly_analyst.py` — `by_the_numbers` strip (task #2a)
- `backend/broadcasts/management/commands/compose_monthly_blast.py` — partial dynamic-subject work (task #5)
- `backend/broadcasts/tests/test_blast_aggregator.py` — `TestSprint23DeterministicCounts` test class

**In working tree, uncommitted at 2026-05-02**:
- `backend/broadcasts/services/blast_aggregator.py` — recess-detection filter narrowing `HansardSitting` to `status=COMPLETED` (task #4)

**Failing tests at sprint start** (literal pytest output, recorded at Sprint 22 close):
```
backend: 1225 passed, 2 failed in 145.17s
- broadcasts/tests/test_blast_aggregator.py::TestSprint23DeterministicCounts::test_parliament_was_in_session_false_when_no_sittings
- broadcasts/tests/test_compose_command.py::TestComposeMonthlyBlast::test_dry_run_shows_counts
frontend: 320 passed, 320 total
```
Both failures are sprint 23 wip; they clear when this sprint lands. They are not pre-existing or unrelated.

**Held — waiting on observation**:
A test email is believed to have been sent to `tamiliam@gmail.com` during the previous (crashed) attempt. Brevo's free-tier daily quota is 300 sends/day; if the test was wrapped in a real `send_broadcast` flow it may be queued behind earlier traffic. **Do not deploy or trigger any further sends until this email is observed and its rendered output inspected.**

## Plan adjustments accepted at 2026-05-02 (post Brevo-delay surfacing)

These two adjustments were agreed during the Sprint 23 start conversation and must be folded into implementation:

### A. Task #9 hardened — dry-run must not send

The original task #9 was "end-to-end dry-run against May 2026 + save HTML". The Brevo-delay incident showed that the line between "dry-run" and "real send" was thinner than the plan implied. Strengthen as follows:

- `compose_monthly_blast --dry-run` produces the rendered HTML to a file path (e.g. `/tmp/digest-2026-05-dryrun.html`) AND asserts a fixed list of known-content markers are present (e.g. recess copy when expected, schools-mentioned table when ≥1 school, no `{{` template-error tokens). The dry-run path makes ZERO Brevo API calls — verified by either patching `BrevoSender` to raise on `send()` during dry-run, or by structurally separating dry-run from any code path that imports the sender.
- A separate flag, `compose_monthly_blast --test-recipients <email>[,<email>...]`, is the only way to perform a real send with a non-default audience. The flag refuses to run twice in any 24-hour window per recipient (idempotency token persisted in a small `BroadcastTestSendLog` table or equivalent — choose simplest implementation).
- The May 2026 dry-run that's part of acceptance criteria is the file-output variant; no email leaves the system during sprint validation.

### B. New task #4a — pre-send Brevo quota check

Insert a new step before any real-send code path runs:

- New helper `broadcasts/services/brevo_quota.py` that calls Brevo's `GET /v3/account` and returns `{daily_quota: int, used_today: int, remaining: int}`.
- `send_broadcast` (and the new `--test-recipients` flag) calls this helper before sending. If `len(recipients) > remaining`, the command refuses to start and prints the three numbers + a recommendation (wait until tomorrow OR use `--batch-size N` to fit within the remaining budget).
- Cheap (one extra API call before a send), prevents the tail-end 400s the April blast hit at 514/519.
- Document Brevo's 300/day free-tier limit in the helper docstring AND in the project memory file.

### C. New task #4b — duplicate-broadcast guard (added 2026-05-02 after duplicate-blast incident)

Insert a guard in `compose_monthly_blast` (and `compose_news_digest`/`compose_parliament_watch`/`compose_urgent_alert` — all `compose_*` commands) that refuses to create a new Broadcast row if a row already exists with the same `(kind, coverage_start_date, coverage_end_date)` and status SENT or SENDING in the last 7 days.

- New helper `broadcasts/services/duplicate_guard.py` with `check_duplicate(kind, start, end, window_days=7) -> Broadcast | None`.
- Each compose command calls the guard before `Broadcast.objects.create(...)` and aborts with a clear message ("a SENT broadcast for {kind} {coverage} already exists; pass --force-duplicate to override") if a match is found.
- New flag `--force-duplicate` allows override for legitimate cases (e.g., re-send after spam-flag, recipient list correction). Logged at WARNING level.
- New simple admin column on `Broadcast` listing `coverage` derived from start/end so duplicates are visible at a glance.
- Triggered by the 2026-05-02 incident where 4 Broadcast rows for the same April digest were created in a 40-minute window because `compose_monthly_blast` (and possibly `resume_sending`?) had no idempotency check. See "Incident: duplicate April blast" section below for the full forensic.

### D. Investigate `resume_sending` interaction (added 2026-05-02 after duplicate-blast incident)

`resume_sending` is supposed to pick up existing SENDING broadcasts and continue them. Yesterday's logs show 4 manual `sjktconnect-resume-sending` job triggers in a 70-minute window (00:52, 00:56, 01:24, 02:00 UTC) and a corresponding 4 Broadcast rows created in roughly the same window (00:31, 00:41, 01:01, 01:11 UTC for IDs 72-75). The timing doesn't perfectly align (broadcasts were created BEFORE the resume runs that match), so resume_sending isn't directly creating broadcasts — but the pattern needs to be traced. Read `backend/broadcasts/management/commands/resume_sending.py` and the prod execution logs in detail; map the actual control flow that produced 4 duplicate rows.

Likely root cause hypothesis: someone (the previous Claude session?) was running `compose_monthly_blast` from a local CLI multiple times to test the `--backfill-since` flag, each call creating a fresh Broadcast row. The `compose_*` commands have no idempotency check (task #4b above is the fix).

## Deliverable

A monthly digest that surfaces (a) what's actually in the data behind the headline numbers, (b) advocacy CTAs that turn intelligence into action, (c) honest copy when Parliament is in recess, and (d) a subject line that earns the open. Tested against the May 2026 dry-run before the 1 June scheduled send.

## Investigation finding (Task #1, completed 2026-05-01)

**Two-bug chain causing all four headline stats to be untrustworthy:**

1. `blast_aggregator.py:105` — `news` queryset hard-capped at `[:5]` for display. Same caps on `parliament[:5]`, `briefs[:5]`, `meeting_reports[:3]`, `scorecards[:3]`.
2. `monthly_analyst.py:232` — passes `len(news)` (= already-capped 5) to the LLM as `current_news_count`, and the LLM is asked to compute `by_the_numbers` from the text-formatted top-5 sample (lines 85-90 of the prompt).

Result: **`by_the_numbers` is LLM-imputed from a 5-row sample, not real DB counts.** April had 46 approved articles; email said 5. "Schools Affected: 29" is LLM-fabricated from the 5-article sample.

**Architectural fix (replaces task #2 of original plan):**
- Aggregator returns `news_total_count: int` (real DB count) AND `news_top: list[5]` (sample for narrative). Same for parliament, schools-mentioned, sentiment breakdown.
- `by_the_numbers` removed from LLM output schema. Computed in Python from real DB queries, passed to template directly.
- LLM still gets the top-5 sample for narrative, with the TRUE counts as context: e.g. *"Of 46 approved articles this month, here are the top 5 by relevance..."* — so the narrative is honest about what was sampled.

This is a bigger change than the original plan suggested but it's the right fix; surface fixes (just showing the 46) would still leave the LLM-hallucinated schools_affected and sentiment_positive numbers in place.

## Task breakdown (ordered by dependency)

| # | Task | Files | Status / Notes |
|---|---|---|---|
| 0 | **Reconcile working tree against commit `4fa3873`** — verify the smuggled `blast_aggregator.py` + `monthly_analyst.py` + `compose_monthly_blast.py` changes match the plan; surface deltas; mark sub-tasks of #2/#2a/#5 done at code level. | — | Output: a short note appended to this plan listing what's done vs not done at code level. **Do this first when work resumes.** |
| 1 | ✅ **Investigate "5 articles vs 46 approved" mismatch** — see finding above | — | Done 2026-05-01. |
| 2 | **Aggregator: separate counts from samples + add new outputs** | `broadcasts/services/blast_aggregator.py`, `broadcasts/tests/test_blast_aggregator.py` | New return shape: `news_total: int`, `news_top: queryset[5]`, `schools_mentioned: list[School]` (from union of news + hansard for the month), `sentiment_breakdown: {positive: int, negative: int, neutral: int}`. Same pattern for parliament. Document per-source date + count semantics in module docstring (lesson 109). **Mostly done in `4fa3873`** — task #0 confirms remainder. |
| 2a | **Strip `by_the_numbers` from LLM schema** | `broadcasts/services/monthly_analyst.py`, tests | Remove `by_the_numbers` from REQUIRED_KEYS + ANALYST_PROMPT. Pass true counts as prompt CONTEXT only. LLM returns narrative + trends; Python supplies the numbers. **Mostly done in `4fa3873`** — task #0 confirms remainder. |
| 3 | **Topic clustering for news articles** | `broadcasts/services/topic_clusterer.py` (new), tests | One Gemini call per digest: "group these N articles by which underlying story they cover; return canonical headline + cluster IDs". Falls back to no-clustering if Gemini fails (fail-open per Quality Engine pattern). **Not started.** |
| 4 | **Recess detection** | `broadcasts/services/blast_aggregator.py` (working-tree change pending commit) | `HansardSitting` filtered to `status=COMPLETED` for the digest month → if zero, copy = "Parliament was not in session"; if >0 but no SJK(T) mentions, copy = "Parliament sat but did not discuss SJK(T) issues". Closes the failing `test_parliament_was_in_session_false_when_no_sittings` test. **In working tree, uncommitted.** |
| 4a | **NEW — Brevo quota check before send** | `broadcasts/services/brevo_quota.py` (new), `broadcasts/services/sender.py`, `broadcasts/management/commands/compose_monthly_blast.py`, tests | Pre-flight check on Brevo `/v3/account`. Refuses send if `len(recipients) > remaining`. See plan adjustment B. **Not started.** |
| 4b | **NEW — Duplicate-broadcast guard** | `broadcasts/services/duplicate_guard.py` (new), all `compose_*.py` commands, tests | Refuses to create a new Broadcast row if a SENT/SENDING row exists for the same `(kind, coverage_start_date, coverage_end_date)` within the last 7 days. New `--force-duplicate` flag allows override. See plan adjustment C. **Not started — added 2026-05-02 after duplicate April blast incident.** |
| 4c | **NEW — Trace `resume_sending` interaction with `compose_*`** | `broadcasts/management/commands/resume_sending.py` (read-only investigation) | Map the actual code paths that allowed 4 Broadcast rows to be created for the same April digest in a 40-minute window on 2026-05-01. See plan adjustment D. Output: a written explanation in the sprint-23 retrospective. **Not started.** |
| **REQUIRED BEFORE RE-ENABLING `sjktconnect-resume-sending` AND `sjktconnect-monthly-blast` SCHEDULERS** — both currently PAUSED as of 2026-05-02 02:11 UTC after the duplicate blast incident. Do NOT resume schedulers until tasks #4a + #4b ship and the #4c investigation has a written explanation. | | | |
| 5 | **Dynamic subject line** | `broadcasts/management/commands/compose_monthly_blast.py`, tests | Pick the highest-impact trend from aggregator output (highest funding figure OR most novel policy item) → subject. Fallback to generic if no trend-worthy item. Closes the failing `test_dry_run_shows_counts` test. **Partially done in `4fa3873`** — task #0 confirms remainder. |
| 6 | **Template overhaul (v2.html)** | `backend/templates/broadcasts/monthly_blast_v2.html` | Major rework: news clusters section, schools-mentioned-by-state list, recess copy, inline brief excerpts (use `lead_paragraph` field if present), stat captions defining what each number means, click-throughs on stat numbers, three new CTA cards (Donate / Share / Check your MP). HTML entities for any em-dash/curly quotes (lesson 21). **Not started.** |
| 7 | **Stat semantics doc + captions** | `broadcasts/services/blast_aggregator.py` docstring + template captions | Lock down: "Schools mentioned" = ?, "News articles" = cluster count, "Positive sentiment" = ?, "Parliament mentions" = ?. Tiny tooltip-style caption in email. **Not started.** |
| 8 | **Sync v1 template (or deprecate)** | `backend/templates/broadcasts/monthly_blast.html` | Either bring v1 in line or check if `compose_monthly_blast.py` still uses it conditionally. Decide before close. **Not started.** |
| 9 | **End-to-end dry-run against May 2026 — FILE OUTPUT ONLY, NO BREVO CALLS** | One-off local exec | `compose_monthly_blast --month 2026-05 --dry-run` against prod-shape data; writes to `/tmp/digest-2026-05-dryrun.html`; asserts known content markers; **zero Brevo API calls** (see plan adjustment A). May is also a recess month → exercises the recess copy path. **Not started.** |
| 9a | **NEW — controlled real send via `--test-recipients`** | `compose_monthly_blast.py`, tests | Single-recipient test send to `tamiliam@gmail.com` ONLY after quota check passes AND task #9 file-output dry-run is clean. Idempotent within 24h per recipient. **Not started.** |
| 10 | **Test suite green + count recorded literally** | `pytest --reuse-db` (per lesson 33; pytest-django uses `--reuse-db`, not `--keepdb` which is Django's runner flag) | Per lesson 96: copy actual `passed/total` line from runner output into close commit. Don't write "tests pass" without proof. |
| 11 | **Deploy + verify** | Cloud Run `--source .` + `gcloud run revisions list --limit=2` (lesson 64) | Verify ACTIVE column on new revision. Single deploy if local dry-run was clean. |
| 12 | **Sprint close docs** | `CHANGELOG.md`, `docs/retrospective-sprint23.md`, `docs/lessons.md`, `docs/decisions.md`, project `CLAUDE.md` Next Sprint section | Each retro claim must reference file:line that proves it (lesson 102). |

**File count**: ~12-15 files touched (was ~10-13 pre-adjustment; added `brevo_quota.py` + sender wiring + a small test-send log table or equivalent for #4a/#9a). Within solo budget (<20).

## Lessons from `lessons.md` being explicitly applied

| Lesson | How applied this sprint |
|---|---|
| **21** (HTML entities in email) | Any em-dash/curly quote added to v2 template uses `&mdash;`/`&ldquo;` etc. |
| **33** (`--keepdb` for tests) | `pytest --keepdb` to avoid Supavisor session conflict. |
| **39** (review-gated APIs hide data) | The "5 vs 46" investigation will likely surface this exact pattern again. If auto-triage threshold is the cause, document the threshold and decide whether to relax. |
| **96** (test counts must be runner output, not intent) | Sprint close commit copies literal `Tests: N passed, N total` line. |
| **102** (retros must reference code, not claim) | Every retro line cites file:line. |
| **104** (manual monitoring slips) | Sprint introduces "monitor May 2026 send" — replaced by the pre-send dry-run in task #9 + a backend test that asserts known-content presence in the rendered HTML. No "remember on May 31" reminder. |
| **108** (aggregator filters mirror public site) | Investigation A1 + every new filter added to the aggregator double-checked against `news/api/views.py` public listing. |
| **109** (per-source date semantics documented) | Task #7 explicitly lands the docstring. |
| **110** (new content types added to digest) | News clusters are a new abstraction — added to aggregator output AND tested. |
| **NEW — Sprint 22 close** (deferral-target sprints accept explicitly) | This sprint IS that explicit acceptance for the "5 vs 46" investigation work and for the recess detection that was previously drifting. |
| **NEW — Sprint 22 close** (single dated checkpoints replace open-ended monitoring) | Task #9 produces a file at sprint validation; no "remember on May 31" reminder. |
| **NEW — Sprint 23 start** (dry-run must structurally exclude real send) | Task #9 separated from #9a; dry-run path makes ZERO Brevo calls verified by either patching `BrevoSender` or by structural separation. |
| **NEW — Sprint 23 start** (Brevo free-tier 300/day cap is recurring) | Task #4a adds a pre-flight quota check to every send code path. Documented in `brevo_quota.py` docstring + project memory. |

## Decisions to capture in `docs/decisions.md` at close

1. **Topic clustering via Gemini one-shot vs deterministic similarity** — choose Gemini if cluster quality matters more than $0.001/digest cost. Document the alternative considered.
2. **Recess copy logic** — chosen detection signal (`HansardSitting.status=COMPLETED` vs `ParliamentaryMeeting.sittings` vs Cloud Scheduler-based) and rationale.
3. **Headline-stat semantics** — what each of the four numbers counts, locked.
4. **Dry-run vs test-send separation** — why `--dry-run` and `--test-recipients` are distinct flags rather than `--dry-run` defaulting to a test send. Trade-off: extra friction for "send me one to look at" workflow vs zero risk of accidental real send during sprint validation.
5. **Brevo quota check semantics** — refuse-at-start vs warn-and-proceed. Trade-off: hard refusal blocks legitimate batch-of-300 sends near quota; warn-and-proceed risks the tail-end 400s the April blast hit.

## Execution approach: **Single agent (solo), sequential**

**Reasoning:**
- Tasks are deeply sequential — task #1 (investigation) determines task #2 (aggregator changes); task #3 (clustering) feeds task #6 (template); task #6 feeds task #9 (dry-run).
- High file overlap — aggregator, command, template all touch each other; parallel agents would collide.
- Risk is medium-high — touching email-send code with 519 active recipients. Solo execution reduces coordination errors and lets each step verify before the next.
- Context budget — sprint fits comfortably; no need to fork.

## Test plan

- After task 0: short note appended below this section listing what's done at code level vs not done.
- After task 1: shell query against prod confirms the "5 vs 46" root cause.
- After task 2: aggregator unit tests pass; assert news cluster shape and schools-list shape.
- After task 3: topic clusterer unit tests pass; assert fail-open path returns un-clustered articles.
- After task 4: recess detection unit tests pass for both branches (no sittings; sittings-but-no-mentions). The currently-failing `test_parliament_was_in_session_false_when_no_sittings` flips to green.
- After task 4a: brevo_quota tests pass — happy path, refuse-when-exceeded, refuse-on-API-error (fail-closed for safety).
- After task 5: subject-line tests pass for trend-found and trend-absent branches. The currently-failing `test_dry_run_shows_counts` flips to green.
- After task 6: rendered HTML smoke test — assert all new sections present, no template errors.
- After task 9: dry-run produces a digest at `/tmp/digest-2026-05-dryrun.html` that includes recess copy (May is a recess month) AND zero Brevo HTTP calls observed (assert via mocked sender).
- After task 9a: `--test-recipients tamiliam@gmail.com` sends exactly one email AFTER quota check passes; second invocation within 24h refuses with a clear message; idempotency log row exists.
- Before task 11: full pytest run, copy literal output line.

## Incident: duplicate April blast (2026-05-02)

**Discovered**: 2026-05-02 ~17:00 MYT, when the user reported receiving the April digest a second time.

**Scope**:
- 4 Broadcast rows created in a 40-minute window on 2026-05-01 (UTC), all for "Monthly Intelligence Blast — April 2026":

  | ID | Status | Created (UTC) | sent_at (UTC) | Total | Sent (DB) | Failed (DB) |
  |---|---|---|---|---|---|---|
  | 72 | SENT | 00:31 | 00:53 | 519 | 0 | 15 |
  | 73 | SENT | 00:41 | 01:25 | 519 | 423 | 0 |
  | 74 | SENT | 01:01 | 01:25 | 519 | 509 | 10 |
  | 75 | SENT | 01:11 | 01:20 | 519 | 519 | 0 |
  | 76 | DRAFT→CANCELLED | 05:43 | — | 0 | 0 | 0 |

- Each row's `BroadcastRecipient.status='SENT'` reflects "201 received from Brevo's `sendTransacEmail`" (Brevo accepted into queue), NOT "delivered to inbox".
- Brevo's actual aggregated delivery: 2026-05-01 = 300 requests / 285 delivered; 2026-05-02 = 300 requests / 288 delivered. Total 600 sends to ~519 unique subscribers ⇒ ~80-300 subscribers received the April digest twice.
- Brevo queue may continue trickle-delivery from the backlog; worst-case bound is each subscriber receiving the digest 4 times.

**Forensic evidence**:
- `gcloud run jobs executions list` for `sjktconnect-monthly-blast`: 5 runs on 2026-05-01 between 05:08 and 06:32 UTC. None at 00:31, 00:41, 01:01, or 01:11 UTC where the duplicate Broadcast rows were created. Conclusion: duplicates were NOT created by the scheduled Cloud Run job.
- `gcloud run jobs executions list` for `sjktconnect-resume-sending`: 4 runs on 2026-05-01 (00:52, 00:56, 01:24, 02:00 UTC). The 02:00 UTC was scheduled; the other three were manual re-triggers.
- Today's `sjktconnect-resume-sending` (2026-05-02 02:00 UTC, scheduled) logged "No broadcasts in SENDING status" — it correctly found nothing to resume. So today's 300 emails are NOT from a fresh trigger; they're Brevo draining its accepted-but-rate-limited queue from yesterday's bursts.
- Verified specific addresses received TWO delivered events (yesterday + today, ~24h apart):
  - `tamiliam@gmail.com`: delivered 2026-05-01T08:31:45 + 2026-05-02T08:15:02
  - `amutasubramaniam@gmail.com`: delivered 2026-05-01T08:31:51 + 2026-05-02T08:15:03

**Most likely root cause**: a local CLI execution of `compose_monthly_blast` (presumably the previous Claude session attempting `--backfill-since` testing) was repeated 4 times in a 40-minute window. Each execution created a fresh Broadcast row with no idempotency check, queued 519 sends to Brevo, Brevo accepted all of them into queue, then rate-limited delivery at ~300/day. Resume-sending runs around the same time were a coincidence (they correctly look for SENDING-status rows; the duplicates were created in DRAFT then transitioned to SENT directly by the compose+send pipeline).

**Containment actions taken 2026-05-02 ~02:11 UTC**:
1. ✅ `sjktconnect-resume-sending` scheduler PAUSED.
2. ✅ `sjktconnect-monthly-blast` scheduler PAUSED.
3. ✅ Broadcast 76 (DRAFT) status set to `CANCELLED` (sentinel value not in `Broadcast.Status` TextChoices; effectively orphans the row from all send paths since `resume_sending` only picks SENDING and `sender.send_broadcast` only picks DRAFT/SENDING).
4. Brevo queue cannot be halted from our side; will continue draining over 1-3 days. Filing a Brevo support ticket is low ETA and unlikely to halt mid-queue.

**System changes required before re-enabling schedulers** (encoded as tasks #4a, #4b, #4c above):
- #4a — Brevo quota check (already in plan from earlier — would have prevented Brevo accepting beyond daily quota and at least surfaced the over-send earlier).
- #4b — Duplicate-broadcast guard (added in response to this incident — prevents same-month rows being created within 7 days).
- #4c — Trace `resume_sending` ↔ `compose_*` interaction in detail; write findings into the sprint-23 retrospective. The hypothesis above is plausible but not verified.

**Lesson candidates for `docs/lessons.md` at sprint close**:
- Compose commands MUST have idempotency checks. "Don't create a new Broadcast row if one already exists for the same coverage period" is the cheapest possible guard and would have prevented this entire incident with one extra DB query before `Broadcast.objects.create(...)`.
- "201 received from Brevo" ≠ "delivered to inbox". `BroadcastRecipient.status='SENT'` should arguably be renamed `QUEUED_WITH_PROVIDER` or supplemented with a separate `delivered_at` field that the Brevo webhook updates. Prevents future "we sent N" claims that reflect API acceptance, not actual delivery.
- Production schedulers that create irreversible side effects (real emails to real subscribers) must default-pause when their compose path lacks idempotency. The cost of a paused scheduler is missed cadence; the cost of a stuck-on scheduler is subscriber annoyance + Brevo quota burn + reputation. Default to paused.

## Resume checklist (when work picks up)

When work resumes (no longer waiting for the test email — Brevo state is now understood):

1. Inspect a sample of the duplicate emails subscribers received yesterday + today. Confirm rendered output matches what the new aggregator was supposed to produce. Note any rendering issues for task #6.
2. Run task #0 (reconciliation) — verify the smuggled `4fa3873` work matches the plan's intent for #2/#2a/#5.
3. Mark Sprint 23 "In Progress" in CLAUDE.md Sprint Status table.
4. Commit the working-tree `blast_aggregator.py` recess-detection change (task #4) as the first explicit Sprint 23 commit, with message `feat(sprint 23): recess detection — filter sittings to COMPLETED`.
5. Land task #4a (Brevo quota check) AND #4b (duplicate-broadcast guard) AND complete #4c investigation **before** any further compose/send work.
6. Continue sequentially through tasks #3, #5 remainder, #6, #7, #8, #9, #9a, #10, #11, #12.
7. **Before sprint close**: re-enable the two paused schedulers (`gcloud scheduler jobs resume sjktconnect-monthly-blast` + `gcloud scheduler jobs resume sjktconnect-resume-sending`) ONLY after #4a + #4b are verified live in prod. The retrospective must explicitly note "schedulers re-enabled at <timestamp> after verification of <commit_sha>".

## Pre-flight (at original plan creation, 2026-05-01)

- Working tree clean (no uncommitted, no unpushed commits) — **NOTE: no longer true at 2026-05-02; see "Current state on disk" above**
- `docs/lessons.md`, `docs/decisions.md`, `.claude/ARCHITECTURE_MAP.md` all read
- Sprint 22 closed; no in-flight work blocking
- Job timeout already bumped to 1800s in earlier session
