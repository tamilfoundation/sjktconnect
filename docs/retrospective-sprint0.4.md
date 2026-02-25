# Sprint 0.4 Retrospective — Gemini AI Analysis + MP Scorecard

**Date**: 2026-02-25
**Duration**: Single session
**Tests**: 149 passing (38 new)

## What Was Built

- `parliament` app with `MPScorecard` and `SittingBrief` models
- `gemini_client.py` — Gemini Flash wrapper using `google.genai` SDK, structured JSON output, response validation, token budgeting
- `scorecard.py` — idempotent MP scorecard aggregation with school count caching from constituency
- `brief_generator.py` — markdown sitting brief, HTML rendering, social post (max 280 chars)
- `analyse_mentions` management command (with `--dry-run`, `--limit`, `--sitting-date`)
- `update_scorecards` management command
- Admin registration for both models
- `google-genai` and `markdown` added to requirements

## What Went Well

- **Clean build**: All 38 new tests passed on second run (first run had one known issue, fixed immediately)
- **No model migration needed for HansardMention**: AI fields were already added forward in Sprint 0.2, so Sprint 0.4 only needed to populate them
- **Good test coverage**: Every service function, every error path, every edge case (mocked Gemini, idempotent recalculation, stale record cleanup, fallback behaviour)
- **Scorecard design**: `update_or_create` with stale cleanup is clean — no incremental state to get wrong

## What Went Wrong

- **`google.generativeai` is deprecated**: Initially used the old SDK, had to rewrite to `google.genai` after seeing the deprecation warning. Cost: ~10 minutes.
- **`%-d` strftime doesn't work on Windows**: Python's `%-d` (no leading zero) is a Linux-only flag. Had to create `_format_date()` helper. Also needed to handle SQLite returning `sitting_date` as a string instead of a `date` object.

## Design Decisions

1. **`google.genai` over `google.generativeai`**: The old package is deprecated and will stop receiving updates. The new SDK uses a client pattern (`genai.Client(api_key=...)`) instead of global configuration — better for testing and multi-key scenarios.

2. **Response validation with defaults**: Rather than failing on unexpected Gemini output, we clamp enum values to valid options and default missing fields. This makes the pipeline robust to model variance.

3. **Token budgeting at 1500 chars**: Sending only mention + context (not full Hansard) keeps costs down and focuses the model. The budget is enforced at the service level, not the command level.

4. **Brief generator fallback**: If no mentions are APPROVED, falls back to all analysed mentions. This allows the brief to be generated before Sprint 0.5's review queue is built.

5. **Cross-platform date formatting**: Created `_format_date()` to handle Windows (no `%-d`), SQLite (date as string), and PostgreSQL (date as date) uniformly.

## Numbers

- Files created: 15 new, 3 modified
- Tests: 38 new (12 gemini_client + 13 scorecard + 13 brief_generator)
- Total tests: 149
- Dependencies added: 2 (google-genai, markdown)
