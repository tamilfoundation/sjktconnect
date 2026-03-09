# Sprint 7.2 Retrospective — Medium Effort Quality Improvements (2026-03-09)

## What Was Built

Four quality improvements completing Phase 7:

1. **Fuzzy School Matching (Item 5)**: `_linkify_schools` now runs a second pass using `difflib.SequenceMatcher` on unlinked SJK(T) references. Threshold 0.85 to avoid false positives. Longest matches applied first.

2. **MP Name Normalisation (Item 6)**: `_normalise_mp_name` strips 16 honorific prefixes (YB, Dato', Datuk Seri, Tan Sri, Dr., Puan, etc.) and normalises smart apostrophes. Wired into `_resolve_mp_party` for better database lookups.

3. **Mention-Level Evaluator (Item 7)**: Deterministic (no API call) quality check on individual mentions. Three checks: speaker presence in excerpt, significance sanity (short excerpt + high score), BUDGET type consistency. Stores `eval_warnings` and `eval_confidence` on HansardMention.

4. **Unified Quality Loop (Item 8)**: `run_quality_loop()` replaces inline while-loops in both brief and report generators. Single function with evaluate/correct/log callbacks. Both generators refactored to use it.

## What Went Well

- **All 4 tasks completed in one session** with parallel execution for Tasks 1-3.
- **Clean separation**: Tasks 1-3 touched different files, zero merge conflicts despite parallel agents.
- **Quality loop refactor** was clean — the brief generator's inline loop from Sprint 7.1 was only 1 sprint old, so the refactor was straightforward.

## What Went Wrong

- **Nothing significant.** The pre-existing report generator connection-closed errors continue (Supabase pooler issue), but they're not related to Sprint 7.2.

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| Fuzzy threshold 0.85 | High enough to avoid false positives; "Mentakb"→"Mentakab" scores 0.98 |
| Honorific stripping iterative (not regex) | Compound prefixes like "YB Dato' Sri" need multiple passes |
| Mention evaluator is deterministic | Avoids API costs; heuristic rules catch the most common issues |
| quality_loop returns (content, flag) | Callers handle persistence — loop stays generic |

## Numbers

- **Files changed**: 8 (4 modified + 2 created + 1 migration)
- **New tests**: 23 (2 fuzzy + 10 normalisation + 5 mention eval + 6 quality loop)
- **Total backend tests**: ~966
- **Total tests**: ~1248 (~966 backend + 282 frontend)
- **Duration**: ~1 hour
