# Sprint 23 — Monthly Digest Quality Pass

**Status**: Plan accepted by user 2026-05-02; implementation paused until test-email arrival is verified (Brevo daily-quota delay).
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

## Resume checklist (when work picks up)

When the test email arrives and inspection confirms the previous attempt is recoverable:

1. Confirm the test email's rendered output matches expectations — note any rendering issues to address before task #6 begins.
2. Run task #0 (reconciliation) and append the result to this plan.
3. Mark Sprint 23 "In Progress" in CLAUDE.md Sprint Status table.
4. Commit the working-tree `blast_aggregator.py` recess-detection change (task #4) as the first explicit Sprint 23 commit, with message `feat(sprint 23): recess detection — filter sittings to COMPLETED`. This also gives a clean baseline for the failing test to flip green.
5. Continue sequentially through tasks #3, #4a, #5 remainder, #6, #7, #8, #9, #9a, #10, #11, #12.

## Pre-flight (at original plan creation, 2026-05-01)

- Working tree clean (no uncommitted, no unpushed commits) — **NOTE: no longer true at 2026-05-02; see "Current state on disk" above**
- `docs/lessons.md`, `docs/decisions.md`, `.claude/ARCHITECTURE_MAP.md` all read
- Sprint 22 closed; no in-flight work blocking
- Job timeout already bumped to 1800s in earlier session
