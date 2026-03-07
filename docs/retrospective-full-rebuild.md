# Retrospective: Full Hansard Rebuild (2026-03-07)

## What Was Built

Complete wipe and rebuild of all 15th Parliament Hansard data using the improved pipeline (20-page speaker lookback, tightened Gemini prompt, MP resolver, improved school matching). Covered all 13 past meetings from Dec 2022 to Mar 2026.

No code changes — this was a data operation sprint.

## What Went Well

- **Clean data wipe**: Dependency-aware deletion (MentionedSchool → HansardMention → SittingBrief → MPScorecard → HansardSitting → ParliamentaryMeeting) worked cleanly.
- **Historical meeting discovery**: `check_new_hansards --start --end` successfully discovered PDFs across all 13 meeting periods by probing parlimen.gov.my date ranges.
- **Pipeline reliability**: 220/286 sittings completed (66 correctly failed — non-sitting days returning HTML). 204 mentions extracted, 203 analysed by Gemini.
- **Report quality**: 11 reports generated with Imagen 4.0 illustrations, all properly formatted HTML (2-13KB each).
- **Quick recovery**: 2nd Meeting 2025 report bloat (108KB of dashes) was caught and regenerated in one step.

## What Went Wrong

- **parlimen.gov.my API doesn't filter by meeting**: POST to carian.html with takwimnum parameter returned the same 20 PDFs regardless. Calendar page also returned only current term. Had to use date ranges instead.
- **Gemini rate limiting**: First analysis run stopped at 139/204 mentions. Required a retry run to reach 203/204.
- **One test hung for 34 minutes**: A `process_hansard` integration test appeared to download a real PDF, blocking the test suite. Had to kill and skip full test verification.
- **Pipeline stuck on check_new_hansards**: `run_hansard_pipeline --skip-calendar` still ran check_new_hansards internally, which probed parlimen.gov.my and got stuck. Had to run remaining steps manually.
- **2 sittings stuck in PROCESSING**: From interrupted pipeline runs. Required manual SQL update to COMPLETED.
- **Special meeting session field**: PositiveIntegerField rejected session=-1. Used session=0 instead (matching existing convention).

## Design Decisions

- **Full wipe vs incremental**: Chose full wipe because existing data was extracted with old code (missing speakers, unmatched schools, weak analysis). Clean slate was simpler and more reliable.
- **Date range discovery vs calendar scraping**: Calendar scraper only fetches current term. Historical meetings required manual date ranges derived from parlimen.gov.my archive screenshots.
- **Report regeneration**: Rather than stripping dashes from the bloated report, regenerated fresh via Gemini for better content quality.

## Numbers

| Metric | Before Rebuild | After Rebuild |
|--------|---------------|---------------|
| Meetings | 7 (current term only) | 13 (all 15th Parliament) |
| Sittings | ~154 | 286 (220 completed) |
| Mentions | ~134 | 204 |
| Analysed | ~134 | 203 |
| School matches | 62 | 67 |
| MP Scorecards | 32 | 53 |
| Sitting Briefs | ~30 | 71 |
| Meeting Reports | 5 | 11 |
| Illustrations | 5 | 11 |
| Gemini API calls | — | ~230 (analysis + briefs + reports) |
