# Sprint 23 — Monthly Digest Quality Pass

**Status**: Planning — awaiting user go-ahead
**Triggered by**: April 2026 digest post-mortem (2026-05-01)
**Prior plan**: `~/.claude/projects/C--Users-tamil-Python/memory/sjktconnect_sprint23_plan.md` (user-confirmed scope)
**Language scope**: English only (trilingual deferred per user direction)

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

| # | Task | Files | Notes |
|---|---|---|---|
| 1 | ✅ **Investigate "5 articles vs 46 approved" mismatch** — see finding above | — | Done 2026-05-01. |
| 2 | **Aggregator: separate counts from samples + add new outputs** | `broadcasts/services/blast_aggregator.py`, `broadcasts/tests/test_blast_aggregator.py` | New return shape: `news_total: int`, `news_top: queryset[5]`, `schools_mentioned: list[School]` (from union of news + hansard for the month), `sentiment_breakdown: {positive: int, negative: int, neutral: int}`. Same pattern for parliament. Document per-source date + count semantics in module docstring (lesson 109). |
| 2a | **Strip `by_the_numbers` from LLM schema** | `broadcasts/services/monthly_analyst.py`, tests | Remove `by_the_numbers` from REQUIRED_KEYS + ANALYST_PROMPT. Pass true counts as prompt CONTEXT only. LLM returns narrative + trends; Python supplies the numbers. |
| 3 | **Topic clustering for news articles** | `broadcasts/services/topic_clusterer.py` (new), tests | One Gemini call per digest: "group these N articles by which underlying story they cover; return canonical headline + cluster IDs". Falls back to no-clustering if Gemini fails (fail-open per Quality Engine pattern). |
| 4 | **Recess detection** | `broadcasts/services/blast_aggregator.py` or new helper | `ParliamentaryMeeting.sittings` for digest month → if zero, copy = "Parliament was not in session"; if >0 but no SJK(T) mentions, copy = "Parliament sat but did not discuss SJK(T) issues". |
| 5 | **Dynamic subject line** | `broadcasts/management/commands/compose_monthly_blast.py`, tests | Pick the highest-impact trend from aggregator output (highest funding figure OR most novel policy item) → subject. Fallback to generic if no trend-worthy item. |
| 6 | **Template overhaul (v2.html)** | `backend/templates/broadcasts/monthly_blast_v2.html` | Major rework: news clusters section, schools-mentioned-by-state list, recess copy, inline brief excerpts (use `lead_paragraph` field if present), stat captions defining what each number means, click-throughs on stat numbers, three new CTA cards (Donate / Share / Check your MP). HTML entities for any em-dash/curly quotes (lesson 21). |
| 7 | **Stat semantics doc + captions** | `broadcasts/services/blast_aggregator.py` docstring + template captions | Lock down: "Schools mentioned" = ?, "News articles" = cluster count, "Positive sentiment" = ?, "Parliament mentions" = ?. Tiny tooltip-style caption in email. |
| 8 | **Sync v1 template (or deprecate)** | `backend/templates/broadcasts/monthly_blast.html` | Either bring v1 in line or check if `compose_monthly_blast.py` still uses it conditionally. Decide before close. |
| 9 | **End-to-end dry-run against May 2026** | One-off Cloud Run job exec | `compose_monthly_blast --month 2026-05 --dry-run` against prod data. May is also a recess month → exercises the recess copy path. Save HTML output for visual review. |
| 10 | **Test suite green + count recorded literally** | `pytest` (use `--keepdb` per lesson 33) | Per lesson 96: copy actual `passed/total` line from runner output into close commit. Don't write "tests pass" without proof. |
| 11 | **Deploy + verify** | Cloud Run `--source .` + `gcloud run revisions list --limit=2` (lesson 64) | Verify ACTIVE column on new revision. Single deploy if local dry-run was clean. |
| 12 | **Sprint close docs** | `CHANGELOG.md`, `docs/retrospective-sprint23.md`, `docs/lessons.md`, `docs/decisions.md`, project `CLAUDE.md` Next Sprint section | Each retro claim must reference file:line that proves it (lesson 102). |

**File count**: ~10-13 files touched. Within solo budget (<20).

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

## Decisions to capture in `docs/decisions.md` at close

1. **Topic clustering via Gemini one-shot vs deterministic similarity** — choose Gemini if cluster quality matters more than $0.001/digest cost. Document the alternative considered.
2. **Recess copy logic** — chosen detection signal (`ParliamentaryMeeting.sittings` vs Cloud Scheduler-based) and rationale.
3. **Headline-stat semantics** — what each of the four numbers counts, locked.

## Execution approach: **Single agent (solo), sequential**

**Reasoning:**
- Tasks are deeply sequential — task #1 (investigation) determines task #2 (aggregator changes); task #3 (clustering) feeds task #6 (template); task #6 feeds task #9 (dry-run).
- High file overlap — aggregator, command, template all touch each other; parallel agents would collide.
- Risk is medium-high — touching email-send code with 519 active recipients. Solo execution reduces coordination errors and lets each step verify before the next.
- Context budget — sprint fits comfortably; no need to fork.

## Test plan

- After task 1: shell query against prod confirms the "5 vs 46" root cause.
- After task 2: aggregator unit tests pass; assert news cluster shape and schools-list shape.
- After task 3: topic clusterer unit tests pass; assert fail-open path returns un-clustered articles.
- After task 4: recess detection unit tests pass for both branches (no sittings; sittings-but-no-mentions).
- After task 5: subject-line tests pass for trend-found and trend-absent branches.
- After task 6: rendered HTML smoke test — assert all new sections present, no template errors.
- After task 9: dry-run produces a digest that includes recess copy (May is a recess month) AND no Brevo send happens.
- Before task 11: full pytest run, copy literal output line.

## Pre-flight verified

- Working tree clean (no uncommitted, no unpushed commits)
- `docs/lessons.md`, `docs/decisions.md`, `.claude/ARCHITECTURE_MAP.md` all read
- Sprint 22 closed; no in-flight work blocking
- Job timeout already bumped to 1800s in earlier session
