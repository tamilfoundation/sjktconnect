# Sprint 31 Retrospective — Per-school history / origin story

**Closed**: 2026-06-27
**Effort**: ~6h elapsed, ~1.5h of that on a false-positive debugging detour (see below)
**Final state**: api `sjktconnect-api-00137-z5g`, web `sjktconnect-web-00145-tmc`, 7/7 jobs synced

## What Was Built

Every school detail page had carried an empty "History & Story" placeholder since Sprint 1.10. We shipped:

1. **Schema** for per-locale history + provenance (`history`, `history_source_urls`, `history_status`, `history_updated_at`, `history_key_dates`) — migrations 0015 + 0016.
2. **Public-source backfill** for 72 / 528 schools (14%) from `ms.wikipedia.org`, restructured via Gemini 2.5 Flash into 75-100-word two-paragraph form + 3-5 key-date pills per locale (en + ms; ta intentionally deferred per tamil-style-guide).
3. **Display component** rewrite — 3-state SchoolHistory (empty CTA / fallback-to-en banner / populated with pills + prose + single-line provenance footer).
4. **Conditional page placement** — history renders above School Details for the 72 populated schools (most-unique content first); placeholder stays at bottom for the 456 empty ones.
5. **`seed_school_histories` management command** with --dry-run / --force / --skip-human-curated semantics so future Wikipedia refreshes don't trample admin edits.
6. **Tests**: 18 backend (test_school_history.py) + 11 frontend (SchoolHistory.test.tsx).

## What Went Well

- **Decisiveness on coverage**: owner approved "ship infrastructure + accept that 400+ end up empty" upfront. That unblocked the schema-first build instead of negotiating with the long tail.
- **Pivot from parallel agents to direct Python scraper**: the original plan was to fan out research via the Agent tool across states. 4 of 5 agents stalled on stream watchdog. Switching to `requests + BeautifulSoup + Gemini` cleanup completed all 11 state subcategories + ~150 schools in ~5 minutes with zero failures.
- **Owner-driven UX iteration over screenshots**: every layout / copy change was approved against a real Playwright screenshot, not a Figma mock. 5 round-trips (initial → pills below text → drop "not verified" → smaller pills → shorter prose) each took <10 min.
- **Gemini restructure at scale**: 71 schools in one pass (`restructure_all.py`), 0 failures, total cost ~US$0.50. Periodic flush every 10 schools meant a crash would not lose work.

## What Went Wrong

### 1. ~1 hour spent chasing a non-existent SSR bug because `curl` doesn't follow Next.js `redirect()`

**Symptom**: tested the Azad page via curl after deploying the new SchoolHistory; got 498 chars body (nav chrome only). Concluded the populated-branch JSX was throwing during SSR. Reverted code, redeployed, rolled api back, rolled web back through 3 revisions. All still showed 498-char empty bodies.

**Root cause**: the URL I was testing was the *stale* slug `azad-george-town-pbd1082` (city had been imported as "George Town" originally; now stored as "Georgetown" one word). Sprint 28's canonical-slug enforcement called `redirect()` to `azad-georgetown-pbd1082`. Next.js renders an HTML *shell* page (~498 chars, navigation only) that triggers client-side navigation — it does NOT emit an HTTP 30x. `curl` saw 200 + small body and I read "small body" as "render failed". Playwright (which executes JS) followed the redirect and showed the page rendering perfectly.

**What system change prevents recurrence**:
- Added to `docs/lessons.md`: never diagnose Next.js page render via curl alone; use Playwright (or `curl -i` and check for `<noscript><meta http-equiv="refresh">` shell pattern) when the URL might hit a redirect path.
- Operational: when smoke-testing post-deploy, always hit the canonical URL (or use Playwright). If you must curl, follow `curl -L` *and* check the final URL against the request URL.

### 2. Two unnecessary "rollback" cycles while chasing the ghost

Rolled api 00136 → 00135 and back; rolled web through 00128 → 00127 → 00130 → 00128 trying to find the "regression". Each rollback was a 5-minute deploy + an ISR-bust. Total wasted: ~25 min of Cloud Run build time + multiple stale-traffic-pin gotchas.

**Root cause**: didn't apply Sprint 17's own lesson ("`x-nextjs-cache: HIT` doesn't mean the page is broken — it means *this* revision rendered it once that way"). I was treating ISR-cached empty bodies as proof of code regression instead of as proof that the *first render* on that revision produced an empty body — which was the redirect shell, not a SSR failure.

**What system change prevents recurrence**: before any rollback, **state the falsifiable hypothesis** ("if I roll back, the page renders 2800+ chars; if it still renders 498, the bug is downstream of code"). The first rollback to 00127 produced 498 — that immediately falsified "Sprint 31 code is the regression" but I kept rolling back anyway. Always treat a falsified hypothesis as the *new* signal, not as noise.

### 3. Test file kept temporarily as-stale-as-the-revert

When I reverted the frontend Sprint 31 changes mid-debug, I also `rm`ed `frontend/__tests__/components/SchoolHistory.test.tsx`. After restoring the Sprint 31 code via `git checkout 2976066 -- ...`, the test file came back too — but the schema had since gained `history_key_dates` and the prop set the test passed didn't include it. Tests still pass (the prop is optional with `?`) but the test doesn't exercise the new pills branch.

**Follow-up**: add 2 tests for pills (`renders pills when historyKeyDates populated` / `falls back to en when ms key dates empty`). Filed as small-change-lane candidate.

## Design Decisions

### Why per-locale JSON instead of separate columns

Considered `history_en TextField`, `history_ms TextField`, `history_ta TextField`. Chose JSONField dict because:
- Adding a 4th locale (e.g. Tamil) is data-only, no migration.
- Locale-fallback logic (`pickText`) is cleaner against a dict.
- Storage cost identical (PG TOASTs the JSON column the same as text).

Trade-off: lose per-locale uniqueness constraints and per-column indexes. Neither matters here — the field is read by moe_code path lookup only.

### Why a separate `history_key_dates` field instead of bundling into `history`

Considered storing key dates as a special key in the history JSON (e.g. `{"en": "...", "_key_dates_en": [...]}`). Chose a separate JSONField because:
- Clean separation of structured (pills) vs prose (history).
- Future "what changed in the last edit" diffs are easier when fields are typed.
- API consumers can request the pills without fetching the full history blob (not used yet, but useful for a future timeline view).

Trade-off: one extra column, one extra migration. Cheap.

### Why conditional placement vs always-top

Considered always rendering history at the top of the left column. Rejected because 456 of 528 schools have no history — putting an empty-state placeholder above the address on 86% of pages looks bad. The conditional in `page.tsx` is one block of Boolean logic and adds zero render cost.

### Why two-paragraph 75-100 word cap

Owner asked to shorten the original Gemini output (~225 words, single paragraph) to mobile-readable size. Tested two cuts:
- 50 words → too thin, loses naming origin / patron context
- 75-100 words → keeps founding + identity + modern-era milestone with 2 paragraphs of breathing room

Locked at 75-100 words / 2 paragraphs after owner approved on Azad reference.

### Why drop "not yet verified by the school" from the footer

Original footer: `Source: Wikipedia (ms) — not yet verified by the school. Help improve →`. Owner asked to drop the "not verified" clause because the source link (Wikipedia) is self-evidently a public source — calling it "unverified" reads as defensive copy. Final: `Source: Wikipedia (ms) — Help improve →`. The verified pill at top-right still fires for `VERIFIED` schools (school-admin or SUPERADMIN approved).

## Numbers

- 528 total schools
- 72 with full restructured history live
- 5 key-date pills average per populated school
- 79 words EN / 77 words MS average for restructured prose
- 18 backend tests added; 11 frontend tests added
- ~US$0.50 total Gemini cost (cleanup + restructure passes combined)
- 9 web deploys + 1 api deploy + 0 jobs failure
- 1 false-positive debugging detour costing ~1h
