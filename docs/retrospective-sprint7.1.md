# Sprint 7.1 Retrospective — Quick Wins (2026-03-09)

## What Was Built

Four independent pipeline quality improvements:

1. **Mention Validation (Speaker Verification)**: `speaker_verified` boolean on HansardMention. Checks if Gemini's extracted `mp_name` appears in the Hansard excerpt (full name or surname fragment). Advisory — doesn't block.

2. **Brief Correction Loop**: Briefs now follow the same evaluate-correct-re-evaluate pattern as reports. Up to 3 attempts with circuit breaker. RED flag on exhaustion, GREEN on pass, auto-publishes only GREEN.

3. **Evaluator Fail-Safe**: API errors now return AMBER (needs human review) instead of silently returning PASS. New `evaluator_error` flag on EvaluationResult. "No API key" still returns PASS (fail-open for dev).

4. **Context Staleness Warning**: Logs a warning when `report-context.json` is >180 days old. Non-blocking, advisory only.

## What Went Well

- **Parallel execution**: Items 3 and 4 were dispatched to parallel agents, completing both in ~90 seconds total.
- **Clean plan**: The Sprint 7.1 plan was precise enough that agents could implement independently with no conflicts.
- **All items genuinely independent**: No merge conflicts, no shared state between items.

## What Went Wrong

- **Pre-existing test fragility exposed**: Two brief generator tests (`test_green_brief_auto_published`, `test_fallback_when_no_api_key`) were environment-dependent — they passed only when GEMINI_API_KEY was absent. The correction loop change amplified the failure (3 attempts → RED instead of single AMBER). Fixed by mocking the evaluator and clearing the env var.
- **Supabase connection pooler**: 4 report generator tests hit "connection already closed" errors during long test runs (~16 minutes). Pre-existing issue, not caused by Sprint 7.1 changes.

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| Speaker verification is advisory (doesn't block) | Many MPs are referred to by informal names; false negatives would reject valid mentions |
| Brief loop mirrors report loop (3 attempts) | Consistency; same circuit breaker pattern across pipeline |
| AMBER vs PASS on API error | PASS was dangerous — broken evaluator silently approved everything |
| Staleness threshold at 180 days | Cabinet reshuffles typically happen annually; 6 months is a reasonable check |

## Numbers

- **Files changed**: 6
- **Lines changed**: +273 / -45
- **New tests**: 13 (5 speaker validation + 2 correction loop + 4 fail-safe + 3 staleness - 1 replaced)
- **Total backend tests**: ~943
- **Total tests**: ~1225 (943 backend + 282 frontend)
- **Duration**: ~2 hours (including test runs with real Gemini API calls)
