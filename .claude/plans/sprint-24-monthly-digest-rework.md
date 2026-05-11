# Sprint 24 — Monthly Digest Template Rework + Scheduling Resume

**Status**: Planned 2026-05-11, not yet started.
**Predecessor**: Sprint 23 Recovery Cut (commit `65f9720`) — shipped quota check, duplicate-broadcast guard, and recess detection (aggregator side). Schedulers still PAUSED awaiting this sprint's deploy.
**Sibling plan to rename**: `.claude/plans/sprint-24-personalised-digest.md` covers per-subscriber MP personalisation; that work moves to **Sprint 29** per the 2026-05-11 roadmap conversation. Rename to `sprint-29-personalised-digest.md` at this sprint's start.

---

## Context — why this sprint

The April 2026 monthly digest exposed three classes of failure that the Recovery Cut did not address:

1. **Recess clauses live in only one part of the LLM prompt.** `executive_summary` correctly says "if Parliament was not in session, say so explicitly" — but `trend_lines`, `fading_from_view`, and `emerging_signals` have no equivalent clause. Result: April's render emitted *"Parliamentary attention — down — indicating a decrease in legislative focus this period"*. That's the exact mis-framing the executive-summary clause was designed to prevent, leaking through siblings.

2. **The template itself is a terminal node.** Zero outbound `<a href>` links in the 11.9 KB of rendered HTML — readers cannot click through to any source article, brief, or meeting. The CTAs (`donate_url`, `share_url`, `mp_activity_url`) are passed to the template by the compose command and dropped on the floor. Stale lifetime scorecards render as if they're the month's data. News articles only appear as LLM narrative; no actual cards.

3. **No topic clustering.** April had 46 approved news articles; the LLM produced narrative across an unstructured pool. With clustering, "12 articles about the Penang school closure" reads as a single story; without it, the digest fragments.

The Recovery Cut shipped the safety floor (no quota bust, no duplicates). This sprint ships the *quality* floor — what the digest must look like before the 1 June 2026 monthly-blast scheduler is re-enabled.

The footer change (item 7 from the 2026-05-11 roadmap conversation — donation/engagement buttons in the digest footer) is folded in here because `_wrap_broadcast_html` adds the same footer to every broadcast (news, urgent, monthly, parliament). One change benefits all four products.

---

## Deliverable

A monthly digest that (a) tells the truth when Parliament is in recess across **every** section of the analysis, (b) renders actual news article cards with click-through links, (c) clusters related news so a 46-article month reads as a small set of stories, (d) shows real CTAs in body + footer, (e) suppresses or reframes stale lifetime scorecards when there's no in-month activity. Plus: footer CTAs propagated to news digest, urgent alerts, and Parliament Watch broadcasts. Plus: both paused Cloud Schedulers resumed after a clean May 2026 dry-run.

---

## Task breakdown (ordered by dependency)

| # | Task | Files | Notes |
|---|---|---|---|
| 1 | **Recess prompt — propagate across all sections** | `backend/broadcasts/services/monthly_analyst.py` | Add recess clause to `trend_lines` (must NOT emit `direction="down"` for parliamentary attention when `parliament_was_in_session=False`), `fading_from_view` (must NOT list parliamentary discourse as "fading" in a recess month), `emerging_signals` (skip parliamentary signals). `opportunity_watch` may still recommend MP outreach (recess is when MPs are most reachable). |
| 1a | **News triage relevance fix — stop off-topic articles reaching `approved`** | `backend/newswatch/services/analyser.py` (or wherever Gemini relevance scoring lives), `backend/newswatch/management/commands/analyse_news_articles.py`, `backend/newswatch/management/commands/reclassify_existing_articles.py` (new), `backend/newswatch/tests/test_relevance.py` | **Surfaced by 2026-05-03 render audit**: 4 of 5 articles in the April digest's news cards were real-estate listings — KIIP Kapar industrial factory (edgeprop.my), Kulai IOI Piccolo terrace (edgeprop.my), Mirai Residences condo (edgeprop.my), one more EdgeProp rental — all scored relevance ≥3 by Gemini and auto-approved per Sprint 2.6's auto-triage rule. The single real Tamil-school article was `SJK(T) Ladang Kulai Besar` (themalaysiapress.com). Steps: (a) **Diagnose** — run `analyse_news_articles --dry-run` against the 4 known-bad URLs and capture relevance scores + Gemini reasoning. (b) **Fix — LOCKED 2026-05-11: prompt + blocklist**: (i) tighten Gemini prompt to require article *subject matter* to be a Tamil school, not merely contain "tamil" or "SJK(T)" in passing (real-estate listings probably matched on "Tamil Bazaar" location names or "SJKT nearby" amenity bullets); (ii) add `DOMAIN_BLOCKLIST = ["edgeprop.my", "propertyguru.com.my", "iproperty.com.my", "mudah.my"]` checked before Gemini is called — blocklisted articles auto-REJECT with `analysis_notes="blocklisted_domain"`. Auto-approve threshold stays at ≥3. (c) **Regression test** — `test_known_bad_april_urls` asserts the 4 captured URLs are either blocklisted OR score below threshold after prompt tightening. (d) **Backfill** — new one-shot `reclassify_existing_articles --since 2026-04-01 --status APPROVED` command reruns the new logic over April's 99 approved articles and bulk-rejects the off-topic ones. Expect 30–50% reduction. |
| 2 | **Topic clustering — Gemini one-shot** | `backend/broadcasts/services/topic_clusterer.py` (new), `backend/broadcasts/tests/test_topic_clusterer.py` (new) | One Gemini call per digest: "group these N articles by which underlying story they cover; return canonical headline + cluster IDs". Fail-open per existing Quality Engine pattern in `news_digest.py` — if Gemini fails or returns malformed JSON, return un-clustered articles with a single "Other" bucket. Wire into `compose_monthly_blast.py` between aggregator and template render. **Depends on #1a** — clustering operates on cleaned approved-article inputs; if half the inputs are real-estate junk, clusters will be junk too. |
| 3 | **Aggregator — schools-by-state breakdown + stat-semantics docstring** | `backend/broadcasts/services/blast_aggregator.py`, `backend/broadcasts/tests/test_blast_aggregator.py` | Add `schools_by_state: dict[str, list[School]]` to aggregate output (groups `schools_mentioned` by `school.state`). Lock down stat semantics in the module docstring: what "Schools mentioned" counts, what "News articles" counts (cluster count vs raw count — pick one), what "Parliament mentions" counts, what `positive_sentiment` counts. Lesson 109 — per-source date semantics also documented here. |
| 4 | **Template overhaul — `monthly_blast_v2.html`** | `backend/templates/broadcasts/monthly_blast_v2.html` | Major rework: (a) recess banner shown when `parliament_was_in_session=False`; (b) three CTA cards in body (Donate / Forward / See full Parliament Watch — pull from `donate_url` / `share_url` / `mp_activity_url`); (c) every news/brief/meeting wrapped in `<a href>` to its source URL; (d) when `scorecards_are_lifetime_fallback=True`, either suppress the scorecard section or reframe heading as "All-time MP champions — this month was quiet" — pick one and lock; (e) schools-mentioned section grouped by state from #3; (f) caption text under each headline number defining what it counts; (g) all em-dash/curly-quote characters use HTML entities (`&mdash;`, `&ldquo;` etc.) per lesson 21. |
| 5 | **News article cards inline (top-N)** | `backend/templates/broadcasts/monthly_blast_v2.html`, `backend/broadcasts/services/blast_aggregator.py` | Within #4 above but called out separately: render top-N news articles (from clusters in #2) as compact cards — title + source publication + date + source link. Empty-state collapses gracefully when `news_total=0`. |
| 6 | **v1 template — sync or deprecate** | `backend/templates/broadcasts/monthly_blast.html`, possibly `backend/broadcasts/management/commands/compose_monthly_blast.py` | `compose_monthly_blast` falls back to v1 when Gemini is unavailable. Decide at sprint start: either bring v1 in line (recess banner, source links, footer CTAs) or remove the v1 fallback entirely and treat Gemini-unavailable as "abort the compose, log the failure". Recommend remove — Gemini has been stable for months, the fallback path is barely tested, and a half-quality fallback is worse than a clean error. |
| 7 | **Global footer CTA — every broadcast type** | `backend/broadcasts/services/sender.py` (`_wrap_broadcast_html`), `backend/broadcasts/tests/test_sender.py` | Add Donate + Forward links to the existing footer template (currently just Unsubscribe + Preferences). One change improves news digest, urgent alerts, Parliament Watch, AND monthly blast footers. Two new params on `_wrap_broadcast_html` with sensible defaults so existing callers don't break. |
| 8 | **Render smoke test** | `backend/broadcasts/tests/test_compose_command.py` | After #4-#7, add an assertion-based smoke test: dry-run May 2026 → assert recess banner present, assert ≥1 `<a href>` per news/brief, assert footer Donate link present, assert no `{{ template_var }}` tokens (regression for template errors), assert no Unicode em-dash unescaped. Replaces "eyeball the rendered HTML" with a structural check. |
| 9 | **Full pytest run — record literal output** | — | Per lesson 96: copy actual `passed/failed` line into the close commit message. Target: `1248 + ~20-30 new = ~1275+` backend (+5 over original target from task #1a's relevance/blocklist/threshold/backfill tests), `320` frontend (unchanged — sprint is backend-only). |
| 10 | **Local dry-run against May 2026** | `python manage.py compose_monthly_blast --month 2026-05 --dry-run` | Writes to file, asserts known content. Zero Brevo calls (verified by S23's quota check refusing in dev mode). May is also a recess month → exercises the recess copy path one more time before deploy. |
| 11 | **Deploy + verify revision active** | `gcloud run deploy sjktconnect-api --source . --account=admin@tamilfoundation.org --project=sjktconnect --region=asia-southeast1 --update-env-vars=...` | Verify `ACTIVE` column on new revision via `gcloud run revisions list --limit=2`. Sprint discipline: max two deploys. If first deploy reveals an issue, fix locally, deploy second time, and we're done — anything beyond that is a process failure. |
| 12 | **Manual prod smoke (read-only)** | Django shell via `gcloud run jobs execute` or `gcloud run services proxy` | Run `aggregate_month(2026, 5)` and confirm: `schools_by_state` is a populated dict; `parliament_was_in_session` is `False`; no exceptions raised. No actual send. |
| 13 | **Resume both Cloud Schedulers** | `gcloud scheduler jobs resume sjktconnect-monthly-blast` + `gcloud scheduler jobs resume sjktconnect-resume-sending` (commands in `sjktconnect_incident_2026_05_02_duplicate_blast.md`) | Only after #11 + #12 pass. Record timestamp + commit SHA in the retrospective. Updates the incident memo to mark schedulers re-enabled. |
| 14 | **Sprint close docs** | `CHANGELOG.md`, `docs/retrospective-sprint24.md`, `docs/lessons.md`, `docs/decisions.md`, `backend/CLAUDE.md` (Sprint Status table + Next Sprint section) | Mark sprint Done. Per lesson 102, each retro line cites file:line. Update memory `sjktconnect.md` per workflow step 10. |
| 15 | **Run `release` workflow** | `docs/release-notes-v2.0.md`, `git tag -a v2.0` | Per the 2026-05-11 roadmap decision — Sprint 24 close IS the v2.0 milestone (Recovery Cut + Quality Overhaul as one coherent v2.0 narrative). Tag after #13. |

**File count**: ~19 files touched (within solo budget of 20 — +3 from news-triage task #1a: analyser, analyse_news_articles command, reclassify_existing_articles new command, test_relevance).

---

## Acceptance criteria

- [ ] April 2026 re-render shows NO `direction="down"` trend for parliamentary attention; no `fading_from_view` entry mentioning parliamentary discourse; no `emerging_signals` mentioning parliamentary patterns.
- [ ] The 4 known-bad April URLs (KIIP Kapar, Kulai IOI Piccolo, Mirai Residences, EdgeProp rental) are REJECTED after the new triage logic runs. `reclassify_existing_articles --since 2026-04-01` reduces April's approved-article count to ≤70 (from 99 — at least 30% bulk-rejected). The April re-render's news cards section shows only Tamil-school-related articles.
- [ ] May 2026 dry-run produces a rendered HTML that contains: a recess banner, ≥1 `<a href>` for every news/brief/meeting referenced, three CTA cards in the body, a Donate link in the footer, no `{{...}}` template tokens, no unescaped em-dashes.
- [ ] Topic clusterer either groups news articles into named clusters or fails open with a single "Other" bucket — no exception bubbles up to the compose command.
- [ ] `_wrap_broadcast_html` adds Donate + Forward links to news_watch_digest.html, news_watch_urgent.html, parliament_watch.html footers — verified by reading the rendered HTML for one broadcast of each kind.
- [ ] Stat-semantics docstring on `aggregate_month()` defines each headline number, and the v2.html template carries a caption tooltip beside each number.
- [ ] Full pytest run is green; literal `N passed` line copied into close commit.
- [ ] `sjktconnect-api` revision deployed; `gcloud run revisions list` shows the new revision as `ACTIVE`.
- [ ] Both `sjktconnect-monthly-blast` and `sjktconnect-resume-sending` Cloud Schedulers are `ENABLED` in `gcloud scheduler jobs list`.
- [ ] Retrospective records the resume timestamp + deployed commit SHA.

---

## Out of scope (explicitly deferred)

- **Per-subscriber MP personalisation + state-by-state slicing per recipient.** Originally drafted as Sprint 24 in `sprint-24-personalised-digest.md`; now Sprint 29. The schools-by-state breakdown in #3 of this sprint is a global section, not per-recipient.
- **Dry-run hardening + `--test-recipients` flag with 24h idempotency** (was Sprint 23 #9/#9a). Sprint 25.
- **`resume_sending` ↔ `compose_*` interaction trace** (was Sprint 23 #4c). Sprint 25.
- **Urgent-alert random-send bug** (item 1 from roadmap). Sprint 25.
- **Parliament Watch preview UI + scheduling** (item 2). Sprint 25.
- **School page edit + search bugs** (items 3, 5). Sprint 26.
- **Auth / profile cleanup** (item 6). Sprint 27.
- **Egress Round 3 + image proxy** (item 4). Sprint 28.

---

## Lessons applied (from `docs/lessons.md`)

| Lesson | How applied this sprint |
|---|---|
| 21 — HTML entities in email | Every em-dash, curly quote, ampersand added to v2.html or the global footer uses `&mdash;` / `&ldquo;` / `&amp;` etc. The render smoke test #8 asserts this. |
| 33 — `pytest --reuse-db` | All local test runs use `--reuse-db` to avoid Supavisor session conflicts. |
| 39 — review-gated APIs hide data | The aggregator's news filter is `exclude(REJECTED)` not `=APPROVED` per the Sprint 18 fix. Topic clusterer must mirror that filter, not re-derive a stricter one. |
| 64 — verify revision ACTIVE | Step #11 explicitly verifies via `gcloud run revisions list --limit=2`, not just "deploy succeeded". |
| 96 — literal test count | Step #9 copies the exact `passed/failed` line. |
| 102 — retro must reference code | Step #14 cites file:line in every retro claim. |
| 104 — manual monitoring slips | No "remember to check on 1 June" — step #10's dry-run is the structural check. |
| 108 — aggregator filters mirror public site | News clustering uses the same `exclude(REJECTED)` filter the public news API uses. |
| 109 — per-source date semantics documented | Step #3 explicitly lands the docstring. |
| 110 — new content types added to digest | News clusters and schools-by-state are new abstractions — added to aggregator output AND tested. |
| **NEW (S22 close)** — single dated checkpoints replace open-ended monitoring | Step #10 produces a file at sprint validation; no "remember on June 1" reminder. |
| **NEW (S23 start)** — Brevo free-tier 300/day cap is recurring | The quota check from S23 stays in place; this sprint does not bypass it. The send path through `_wrap_broadcast_html` flows through `send_broadcast` which already enforces quota. |

---

## Decisions to capture in `docs/decisions.md` at close

1. **Topic clustering — Gemini vs deterministic similarity.** Recommend Gemini for cluster *quality* (~$0.001/digest). Alternative considered: token-overlap clustering (free but produces strange clusters when articles share boilerplate like "Tamil school").
2. **v1 template — kept-and-synced vs removed.** LOCKED 2026-05-11: REMOVED. Gemini-unavailable aborts the compose with an ops alert. Half-quality fallback is worse than a clean error.
3. **Recess copy detection signal.** S23 chose `HansardSitting.status=COMPLETED` for the digest month. This sprint propagates that signal to every prompt section — lock the rationale.
4. **Footer CTA destinations.** LOCKED 2026-05-11: Donate → `https://tamilschool.org/donate`. Forward → `mailto:?subject=Tamil%20Schools%20Intelligence%20Blast&body=Have%20a%20look%20at%20this%20month%27s%20digest%20from%20tamilschool.org`. Mailto chosen over share-page to keep engineering cost low; no Brevo link-redirector wrap.
5. **Stat headline definitions.** What "Schools mentioned" / "News articles" / "Parliament mentions" / "Positive sentiment" each count. Locked in #3's docstring.
6. **News triage — auto-approve threshold + domain blocklist.** LOCKED 2026-05-11: tighten Gemini prompt (article must BE about a Tamil school, not merely mention it) + add domain blocklist `[edgeprop.my, propertyguru.com.my, iproperty.com.my, mudah.my]` as pre-Gemini filter. Auto-approve threshold stays at ≥3. Per lesson 46 (fix source data not downstream workarounds): prompt + blocklist are source-side; threshold tweak would be downstream. Reasoning: April render audit's 4 known-bad URLs were all from edgeprop.my — the blocklist catches them cheaply, the prompt tightening catches future unknown classifieds.

---

## Execution approach — **single agent, sequential**

- Tasks #1 → #3 → #2 → #4 → #5 → #7 are deeply sequential. Topic clusters from #2 feed cards in #5; schools-by-state from #3 feeds template in #4. Footer in #7 is independent and can fold in at any point.
- High file overlap (aggregator, command, template all touch each other).
- Risk medium — touching the live monthly digest that 519 subscribers will read on 1 June. Solo execution reduces coordination errors.
- Context budget fits comfortably.

---

## Verification flow (end-of-sprint)

1. Local: `cd backend && pytest broadcasts/ -v` → 0 failures, expected new test count ≥ 1248 + 15.
2. Local: `cd backend && pytest` (full suite) → 0 failures.
3. Local: `cd backend && python manage.py compose_monthly_blast --month 2026-05 --dry-run` → writes file, manual visual check + automated assertions all pass.
4. Deploy: `gcloud run deploy sjktconnect-api --source backend/ --account=admin@tamilfoundation.org --project=sjktconnect --region=asia-southeast1` → revision uploaded.
5. Verify: `gcloud run revisions list --service=sjktconnect-api --account=admin@tamilfoundation.org --project=sjktconnect --region=asia-southeast1 --limit=2` → new rev ACTIVE.
6. Smoke: `gcloud run services proxy sjktconnect-api --port=8080 --account=admin@tamilfoundation.org --project=sjktconnect --region=asia-southeast1` then `curl localhost:8080/health/` → 200 ok.
7. Resume: the two `gcloud scheduler jobs resume` commands from the incident memo.
8. Confirm: `gcloud scheduler jobs list --account=admin@tamilfoundation.org --project=sjktconnect --location=asia-southeast1 | grep -E "monthly-blast|resume-sending"` → both show `ENABLED`.
9. Tag: `git tag -a v2.0 -m "Release v2.0 — incident recovery + monthly digest quality"` + `git push origin v2.0`.
10. Update memory: incident memo notes resume-timestamp + commit SHA.

---

## Open questions — LOCKED at kickoff 2026-05-11

1. **Forward CTA target** → ✅ `mailto:?subject=Tamil%20Schools%20Intelligence%20Blast&body=...` — prefilled mail compose. Lowest engineering cost; matches the 2026-05-03 prototype. No share page or Brevo link-redirector.
2. **v1 template** → ✅ **Delete**. `compose_monthly_blast` aborts cleanly + logs an ops alert when Gemini is unavailable. Half-quality fallback is worse than a clean error.
3. **Schools-by-state layout** → ✅ **Table** (State | Schools | Examples). Matches the prototype. Accordion needs JS/CSS that breaks in many mail clients (Outlook, Gmail web vs app, dark mode).
4. **News triage approach (task 1a)** → ✅ **Combination a + c**: (a) tighten Gemini prompt — article subject must BE a Tamil school, not merely mention "tamil"/"SJK(T)" in passing; (c) add domain blocklist `[edgeprop.my, propertyguru.com.my, iproperty.com.my, mudah.my]` as pre-Gemini filter. Auto-approve threshold stays at ≥3 (no change to threshold). Per lesson 46 — fix source data (prompt + blocklist) not downstream workarounds (threshold).
