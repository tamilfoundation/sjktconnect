# Sprint 24 — Personalised Monthly Digest

**Status**: Proposed; awaiting Sprint 23 close + user go-ahead.
**Last updated**: 2026-05-03
**Triggered by**: April 2026 render audit (2026-05-03) — items 3 + 4 of the "five highest-impact mission improvements" list.
**Prerequisite**: Sprint 23 must be fully closed (templates, recess-detection, source links, CTAs, real DB counts) before this sprint can start. Sprint 24 builds on Sprint 23's `monthly_blast_v2.html` template and the `aggregate_month` data shape.
**Language scope**: English only (Tamil/Malay deferred per current project direction).

## Deliverable

Transform the Monthly Intelligence Blast from "519 identical copies of the same national-level digest" into "519 personalised digests, each oriented around the recipient's home constituency". The blast becomes an advocacy trigger rather than a passive newsletter.

Two structural additions:

1. **Per-subscriber MP block** — every recipient sees a "Your MP this month" panel with their constituency MP's mention count, scorecard rank, and a one-click "Write to your MP" mailto with pre-filled subject. Suppressed gracefully when subscriber hasn't set a home constituency.
2. **State-by-state schools-mentioned breakdown** — every recipient sees a national table of schools mentioned, broken down by state, with the recipient's own state visually highlighted. Per-state CTAs ("Penang readers — share this with your ADUN").

These are the two items from the April render audit's "five highest-impact" list that were too substantial to fold into Sprint 23.

## Mission rationale (why this sprint matters more than incremental quality work)

SJK(T) Connect's mission is to convert intelligence about Tamil schools into action by parents, headmasters, MPs, NGOs, and community leaders. Sprint 23 fixes the digest's *trustworthiness* (real numbers, recess-aware framing, source links, CTAs). But trust without personalisation produces 519 readers who all receive the same "stakeholders should engage" copy — and 519 readers who close the email and forget.

Personalisation is the structural change that converts intelligence into advocacy:
- A Penang parent seeing "5 Penang schools were mentioned this month" acts. The same parent seeing "schools_mentioned: 28 nationally" reads passively.
- A Segamat constituent seeing "Your MP, Yuneswaran Ramaraj, didn't mention SJK(T) schools this month — write to them" acts. The same person seeing "Parliamentary mentions = 0 this month" reads passively.

This sprint also unlocks per-subscriber engagement metrics (Sprint 8.5's Brevo webhook pipeline already records open + click events; once each digest has personalised CTAs, click-through-by-MP becomes a lead indicator of which constituencies have engaged subscribers).

## Task breakdown (ordered by dependency)

| # | Task | Files | Notes |
|---|---|---|---|
| 1 | **Add `home_constituency` FK to `Subscriber`** | `subscribers/models.py`, `subscribers/migrations/0007_*.py` | `ForeignKey(Constituency, null=True, blank=True, on_delete=SET_NULL, related_name="home_subscribers")`. Optional — not required at signup. Backfill nothing; new field defaults to NULL for existing 519 subscribers. |
| 2 | **Subscribe form: add constituency selector** | `frontend/components/SubscribeForm.tsx`, `frontend/lib/api.ts` (`subscribe()` payload), `subscribers/api/serializers.py` (accept new field) | Single dropdown listing all 222 parliamentary constituencies, sorted by state then name. Optional (not required). Helper text: "Used to personalise your monthly digest with your MP's activity. You can change this later." |
| 3 | **Preferences page: editable constituency** | `frontend/app/[locale]/preferences/[token]/page.tsx`, `subscribers/api/views.py` (PATCH preferences endpoint) | Same dropdown as task #2, pre-populated with current value. Save updates `Subscriber.home_constituency`. |
| 4 | **Aggregator extension: per-MP monthly stats** | `broadcasts/services/blast_aggregator.py`, tests | New helper `aggregate_mp_month(mp_id, year, month) -> dict`: returns `{mention_count: int, mention_examples: list[3], rank_in_month: int | None, total_mps_with_mentions: int}`. Cheap query (HansardMention filtered by sitting_date + speaker_mp). Cached per-call within compose run. |
| 5 | **Aggregator extension: schools-by-state** | `broadcasts/services/blast_aggregator.py`, tests | New return field `schools_mentioned_by_state: dict[str, list[School]]`. Reuses existing `schools_mentioned` set; just groups by `school.state`. Sorted by school count desc within each state. |
| 6 | **Per-recipient template injection in compose pipeline** | `broadcasts/services/sender.py` (or new helper `personaliser.py`), `broadcasts/management/commands/compose_monthly_blast.py` | Today: one `html_content` is rendered once and reused for all 519 recipients. New: render a base `html_content` (national sections), then for each recipient with `home_constituency` set, inject a personalised "Your MP this month" + "Your state" block via Django template `Inclusion Tag` or string replacement on a marker token. Recipients without `home_constituency` see the base. Performance: ~519 small renders, <2s total. |
| 7 | **MP block template** | `backend/templates/broadcasts/_mp_block.html` (new include) | Renders: MP name + photo (from MP.profile_url), mentions this month (count + 1-line excerpt of one), scorecard rank ("4th of 18 active MPs this month" or "no active MPs spoke this month if recess"), one-click mailto button "Write to your MP" with pre-filled subject + body. Recess-aware (shows "Parliament was in recess this month — your MP had no opportunity to speak"). |
| 8 | **State block template** | `backend/templates/broadcasts/_state_block.html` (new include) | Renders: schools-mentioned table with state column, school count column, top-2 schools per state. Recipient's own state row visually highlighted. Per-state CTA: mailto link to state ADUN with pre-filled "Share this digest" subject. |
| 9 | **Brevo webhook engagement tracking — extend per-broadcast metrics** | `broadcasts/services/webhook_handler.py`, dashboard | Already tracks `open_count` + `click_count` per `BroadcastRecipient`. Add a new `personalised_link_clicked` event: when a recipient clicks the "Write to your MP" mailto, that's a strong advocacy signal. Track per-MP click rate over time (admin dashboard). |
| 10 | **End-to-end dry-run + test-render across diverse subscribers** | One-off local exec | Render the digest for 5 representative subscribers: (a) home_constituency=NULL, (b) home in P140 Segamat, (c) home in a Penang constituency, (d) home in a "no SJK(T) schools" constituency, (e) home in a constituency where MP is from opposing party. Inspect each. Save to `/tmp/digest-personalised-{label}.html`. **Zero Brevo calls.** |
| 11 | **Test suite green + count recorded literally** | `pytest --reuse-db` | Lessons 33 + 96. |
| 12 | **Deploy + verify** | Cloud Run `--source .` + revision check | Single deploy; verify ACTIVE on new revision. |
| 13 | **Sprint close docs** | CHANGELOG, retrospective, lessons, decisions, project CLAUDE.md | Per-sprint-close workflow. |

**File count**: ~12-15 files touched. Within solo budget (<20).

## Lessons applied

| Lesson | How applied |
|---|---|
| **#21** (HTML entities in email) | New `_mp_block.html` and `_state_block.html` templates use `&mdash;` etc. |
| **#33** (`--reuse-db` for tests) | Same. |
| **#96** (test counts from runner output) | Sprint close commit copies literal `passed/total`. |
| **#102** (retros must reference code) | Each retro line cites file:line. |
| **#108** (aggregator filters mirror public site) | New `aggregate_mp_month` filter set verified against `parliament/api/views.py` MP-detail endpoint. |
| **#109** (per-source date semantics documented) | New aggregator helpers add docstrings on date-window semantics. |
| **#110** (new content types in digest) | Per-subscriber MP block + state block are new content types — added to test coverage. |
| **NEW (Sprint 22 close)** — single dated checkpoints | Task #10 produces files at sprint validation; no "remember to monitor" reminder. |
| **NEW (Sprint 23 start)** — dry-run structurally excludes real send | Task #10 produces local files; no Brevo calls. Inherits Sprint 23's separation between `--dry-run` and `--test-recipients`. |
| **NEW (Sprint 23 incident)** — duplicate-broadcast guard required | Sprint 24 inherits Sprint 23 task #4b. Personalisation does NOT introduce a separate compose path; reuses Sprint 23's guarded `compose_monthly_blast`. |

## Decisions to capture in `docs/decisions.md` at close

1. **Per-recipient template injection vs per-recipient full render** — chose injection on marker tokens (cheaper, ~2s vs ~30s for 519 full renders) vs whole-template-per-recipient. Trade-off: less flexibility per recipient (can only personalise the marked sections, not arbitrary template logic). Acceptable because the personalisation surface is intentionally bounded to MP block + state block.
2. **Optional vs required `home_constituency`** — chose optional. Trade-off: ~50% of subscribers will have NULL and see the base digest. Acceptable because requiring it at signup adds friction and would lose subscribers; preferences page lets motivated subscribers add it later.
3. **MP mailto CTA vs deeper integration (in-app message form)** — chose mailto. Trade-off: opens recipient's mail client, less trackable than a form. Acceptable for v1 because mail client is the action surface community already uses; in-app form is a Sprint 25+ consideration.

## Execution approach: **Single agent (solo), sequential**

Same reasoning as Sprint 23: deeply sequential tasks, high file overlap (aggregator → compose → template → personaliser), medium-high risk (touching 519-recipient send pipeline), fits solo context budget.

## Test plan

- After task 1 + 2 + 3: subscribe form + preferences page accept and persist `home_constituency`. Verified locally.
- After task 4: `aggregate_mp_month` returns correct counts for known MPs in known months (e.g. P140 Segamat MP, March 2026).
- After task 5: `schools_mentioned_by_state` returns correct grouping for April 2026 (3 Penang, 1 Selangor, 1 Perak per current data).
- After task 6 + 7 + 8: render-only dry-run for 5 representative subscribers (task #10 list) produces visibly distinct HTML; recipient with NULL `home_constituency` sees no MP/state block; recipient with `home_constituency=P140` sees Yuneswaran Ramaraj's data.
- After task 9: webhook click event for a personalised mailto increments `personalised_link_clicked` field on the `BroadcastRecipient`.
- Before task 12: full pytest run, copy literal output line.

## Resume conditions

When this sprint starts:
1. Sprint 23 must be fully closed (CHANGELOG, retro, lessons, decisions all updated; both schedulers re-enabled with verification timestamp + commit SHA recorded).
2. Confirm `Subscriber` model + Brevo webhook pipeline are in their post-Sprint-23 state.
3. Read this plan. Mark Sprint 24 "In Progress" in CLAUDE.md.

## Out of scope for Sprint 24

- Per-subscriber school personalisation (e.g. "your child's school was mentioned"). Requires `Subscriber.watched_schools: ManyToManyField(School)`. Sprint 25 candidate.
- Tamil/Malay digest variants. Requires per-locale Gemini analyst calls + per-locale template. Sprint 25+ candidate.
- In-app advocacy message composer (replacing mailto). Sprint 25+.
- Donor-tier or supporter-only digest variants. Out of current product scope.
