# Small-Change Lane — Consolidation Log

Per `Settings/_workflows/small-change-lane.md`. Each small-lane change appends one line under `## Pending`. Every ~10 entries triggers a Consolidation Review under `## Reviews`.

## Pending

- 2026-06-26 ops(cloudflare): legacy /claim + ASPX URLs 301 to root (Cloudflare ruleset `1af056d066e44a5885c933227a413981`, no repo code changes; closes 148+ of 157 GSC 404s from the 2026-06-26 SEO audit)
- 2026-06-27 fix(suggest-form): success-state button label "Cancel" → "Close" — owner-flagged UX bug. New i18n key `close` added across en/ms/ta (commit `cf09c7d`, 4 files)
- 2026-06-27 test(hansard): close TD-12 — new `backend/hansard/tests/test_extractor.py` (8 tests, reportlab fixture PDFs into tmp_path); coverage 26% → 100% on `extract_text()`
- 2026-07-23 fix(news): dates rendered a day early — shared `lib/dates.ts` pins Asia/Kuala_Lumpur; jest TZ pinned to UTC (frontend: NewsCard, NewsWatchSection, jest.config, +5 tests). Same ambient-zone bug still open on ModerationQueue / MySuggestions / school-edit page
- 2026-06-27 ops(monitoring): close TD-06 + TD-24 — pulled Cloud Run egress via MQL for last 7 days; baseline 53-87 MB/day on web well under the 150 MB/day target; 6/27 spike from FB launch is expected. TD register swept: all 25 items now ✅ RESOLVED

## Reviews

_(none yet — review triggers when wat_lint flags the backlog)_
