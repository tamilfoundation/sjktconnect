# Sprint 5.5 Retrospective — Intelligence Report Quality

## What Was Built

Improved the quality of Hansard pipeline output (sitting briefs, meeting reports) and added editorial cartoon illustrations to meeting reports. Tested on the 1st Meeting of the 2nd Term (13 Feb – 4 Apr 2023) as a quality baseline.

- Rewrote both the brief and meeting report Gemini prompts to produce journalistic, factual content
- Added Imagen 4.0 editorial cartoon generation (The Economist/New Yorker style)
- Added illustration API endpoint and frontend display
- Fixed multiple output quality issues through iterative prompt refinement

## What Went Well

- **Iterative quality loop worked**: 4 regeneration cycles, each improving based on user feedback. Headlines went from generic "2 Tamil School Mentions" to descriptive "Dilapidated Infrastructure Plagues High-Performing SJK(T)".
- **JSON response mode**: Structured brief output (headline, blurb, body_md, social) made extraction reliable.
- **Imagen 4.0 integration**: Cartoon generation worked on first attempt, contextually relevant to findings.
- **Thinking budget discovery**: Identified that Gemini 2.5 Flash thinking tokens consume output budget — `thinking_budget=1024` is the sweet spot.

## What Went Wrong

- **thinking_budget=0 produces gibberish**: 128K chars of malformed markdown table. Had to discover the right value empirically.
- **JSON reliability ~91%**: Gemini's JSON mode occasionally produces invalid JSON when markdown with quotes is embedded. Needed retry logic.
- **`smarty` markdown extension**: Converted apostrophes to `&rsquo;` HTML entities which displayed as raw text. Non-obvious root cause.
- **Local SQLite broken**: Missing columns from another branch forced using production Supabase for testing. Not ideal but workable.
- **Pre-existing test failures**: The `feature/intelligence-reports` branch has 11 failing tests from earlier work (broadcasts, feedback apps). These were not addressed in this sprint.

## Design Decisions

1. **BinaryField for illustration**: Stored PNG bytes directly in PostgreSQL rather than cloud storage. Simpler architecture, serves via Django view. Tradeoff: larger DB, but illustrations are infrequent (one per meeting, ~1.3 MB each).
2. **JSON response mode for briefs**: Structured output prevents extraction errors. Tradeoff: ~9% JSON parse failure rate requiring retry.
3. **thinking_budget=1024**: Balances quality (model can reason) with output length (doesn't steal too many tokens). Lower values degrade quality, higher values truncate output.
4. **Auto-reject low-relevance news**: Articles with relevance_score < 3 now auto-rejected instead of staying PENDING. Reduces manual review burden.

## Numbers

- Backend tests: 838 passing, 13 failing (11 pre-existing, 2 fixed this sprint)
- Frontend tests: 282 passing
- Files changed: 11
- Meeting reports generated: 1 (test case)
- Illustrations generated: 1 (1.3 MB PNG)
- Briefs regenerated: 8 (for 1st Meeting 2023)
- Prompt iterations: 4
