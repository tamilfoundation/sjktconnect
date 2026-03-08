# Pipeline Quality Improvements — Design Doc

**Date**: 2026-03-08
**Phase**: 7 (Quality Consolidation)
**Sprints**: 7.1 (quick wins) + 7.2 (medium effort)
**Scope**: 8 improvements across all 3 pipeline stages (mentions, briefs, reports)

---

## Problem Statement

The Hansard pipeline (mentions -> briefs -> reports) produces output with no validation at the mention stage, no correction at the brief stage, and a fail-open evaluator that marks everything GREEN when the API crashes. These gaps mean errors cascade silently through the pipeline.

## Architecture Overview

```
Mention Analysis  -->  Brief Generation  -->  Report Generation
(gemini_client)       (brief_generator)      (generate_meeting_reports)
      |                      |                       |
  [NEW: Item 7]         [NEW: Item 2]          [EXISTS: quality loop]
  Deterministic          Correction loop        3-attempt eval/correct
  eval (no API)          (mirrors reports)
      |                      |                       |
      v                      v                       v
           [NEW: Item 8] Unified quality_loop.py
```

---

## Sprint 7.1 — Quick Wins

### Item 1: Mention Validation

**Problem**: Gemini's extracted `mp_name` is never cross-checked against the actual Hansard excerpt. Wrong names cascade into scorecards and reports.

**Design**:
- Add `_validate_speaker()` function in `gemini_client.py`
- Called from `apply_analysis()` after Gemini returns
- Checks:
  1. Does `mp_name` (or surname fragment) appear in `verbatim_quote` or `context_before`?
  2. Does `mp_constituency` match the MP database for this MP?
- New field on `HansardMention`: `speaker_verified` (BooleanField, default=True)
- Set to `False` when name not found in excerpt; log a warning
- No re-prompting, no blocking — advisory only

**Files touched**:
- `parliament/services/gemini_client.py` — add `_validate_speaker()`, call from `apply_analysis()`
- `hansard/models.py` — add `speaker_verified` field
- `hansard/migrations/` — new migration

### Item 2: Brief Correction Loop

**Problem**: `_run_brief_quality_loop()` evaluates but never corrects. FIX/REJECT verdicts are logged but the brief is published as-is.

**Design**:
- Extend `_run_brief_quality_loop()` in `brief_generator.py` to mirror the report loop:
  1. Evaluate brief
  2. If FIX -> call `correct_brief()` (already exists in `corrector.py`) -> re-convert markdown to HTML -> re-evaluate
  3. Up to 3 total attempts (1 original + 2 corrections)
  4. Circuit breaker: if all 3 fail, set `quality_flag = "RED"`, `is_published = False`
- Each attempt creates a `QualityLog` entry with incrementing `attempt_number`
- `correct_brief()` in `corrector.py` already delegates to `correct_report()` — no changes needed there

**Files touched**:
- `parliament/services/brief_generator.py` — rewrite `_run_brief_quality_loop()`

### Item 3: Evaluator Fail-Safe

**Problem**: Evaluator returns PASS when API call fails. Bad content gets marked GREEN.

**Design**:
- Distinguish two failure modes in `evaluator.py`:
  - **No API key**: Return PASS (unchanged — can't evaluate without API, don't block dev)
  - **API call failure** (timeout, rate limit, JSON parse): Return `EvaluationResult(verdict="AMBER", evaluator_error=True)`
- Add `evaluator_error: bool = False` field to `EvaluationResult` dataclass
- Downstream: AMBER triggers correction loop (FIX path), so content gets another chance
- If correction also fails, content is published as AMBER (needs human review) rather than falsely GREEN

**Files touched**:
- `parliament/services/evaluator.py` — change exception handler, add field

### Item 4: Context Staleness Warning

**Problem**: `report-context.json` has `last_updated: "2026-03-07"`. If cabinet reshuffles, prompts use stale minister names.

**Design**:
- In `context_builder.py`'s `build_context()`, parse `last_updated` from the JSON
- If >180 days old, log `WARNING`: "Context reference is {N} days old -- cabinet/glossary may be stale. Update data/report-context.json."
- No blocking, no new fields — just a visible warning in command output

**Files touched**:
- `parliament/services/context_builder.py` — add staleness check

---

## Sprint 7.2 — Medium Effort

### Item 5: Fuzzy School Matching in Linkification

**Problem**: `_linkify_schools()` uses exact regex matching. Typos and minor name variations miss.

**Design**:
- After the existing exact-match pass in `_linkify_schools()`, collect unlinked `SJK(T) <name>` patterns from the HTML
- For each unlinked name, run `difflib.SequenceMatcher` against all `School.short_name` values
- Match threshold: ratio >= 0.85
- If matched, linkify the school name
- Log fuzzy matches at INFO level for monitoring
- No new dependencies (difflib is stdlib)
- Performance: ~528 schools x ~5 unlinked names = ~2,640 comparisons — negligible

**Files touched**:
- `parliament/management/commands/generate_meeting_reports.py` — extend `_linkify_schools()`

### Item 6: MP Name Normalisation

**Problem**: Gemini returns inconsistent honorifics ("YB Dato' Sri Arul" vs "Dato Sri Arul" vs "Arul"). Same MP appears as different people.

**Design**:
- Add `_normalise_mp_name(name: str) -> str` in `gemini_client.py`
- Strip honorific prefixes in order (longest first): "Yang Berhormat", "Tan Sri", "Dato' Sri", "Dato Sri", "Datuk Seri", "Datuk", "Dato'", "Dato", "Tun", "Dr.", "Puan", "Encik", "Tuan", "YB"
- Normalise apostrophes: right single quote -> ASCII apostrophe
- Strip extra whitespace
- Call in `apply_analysis()` before saving mp_name
- Call in `_resolve_mp_party()` before database lookup (normalise both sides of comparison)
- Also use in report evaluator's MP name matching

**Files touched**:
- `parliament/services/gemini_client.py` — add `_normalise_mp_name()`, use in `apply_analysis()` and `_resolve_mp_party()`

### Item 7: Mention-Level Evaluator

**Problem**: Mentions have zero quality checks. Wrong speaker, inflated significance, misclassified type — all pass silently.

**Design**:
- Add `evaluate_mention()` in `evaluator.py` — deterministic, no API call
- Checks:
  1. **Speaker presence**: Is mp_name (or surname) in the excerpt? (reuses Item 1 logic)
  2. **Constituency cross-check**: Does MP database confirm this MP for this constituency?
  3. **Significance sanity**: Excerpt <100 chars + significance >3 = suspicious
  4. **Type consistency**: mention_type=BUDGET but no financial keywords in excerpt = flag
- Returns `MentionEvaluation` dataclass: `warnings: list[str]`, `confidence: float` (0.0-1.0)
- New fields on `HansardMention`:
  - `eval_warnings` (JSONField, default=[])
  - `eval_confidence` (FloatField, default=1.0)
- Called from `apply_analysis()` after all fields are set
- Advisory only — does not block or re-prompt

**Files touched**:
- `parliament/services/evaluator.py` — add `MentionEvaluation`, `evaluate_mention()`
- `hansard/models.py` — add `eval_warnings`, `eval_confidence` fields
- `hansard/migrations/` — migration (combined with Item 1 field)
- `parliament/services/gemini_client.py` — call `evaluate_mention()` from `apply_analysis()`

### Item 8: Unified Quality Framework

**Problem**: Reports have a 3-attempt loop, briefs get evaluate-only (corrected in Item 2), mentions have nothing. Three different patterns doing the same thing.

**Design**:
- New file: `parliament/services/quality_loop.py`
- Single reusable function:

```python
def run_quality_loop(
    content_type: str,       # "mention", "brief", "report"
    content: str,            # current text/HTML
    evaluate_fn,             # callable(content) -> EvaluationResult
    correct_fn=None,         # callable(content, eval_result) -> str | None
    max_attempts: int = 3,
    log_entry_fn=None,       # callable(attempt, eval_result) -> None
) -> tuple[str, str]:        # (final_content, quality_flag)
```

- Logic:
  1. Evaluate content
  2. If PASS -> return (content, "GREEN")
  3. If FIX/REJECT and correct_fn exists -> correct -> re-evaluate
  4. Repeat up to max_attempts
  5. If exhausted -> return (best_content, "RED" or "AMBER")
  6. Call log_entry_fn at each step
- Refactor `generate_meeting_reports.py` inline loop -> `run_quality_loop()` call
- Refactor `brief_generator.py` `_run_brief_quality_loop()` -> `run_quality_loop()` call
- Mentions: use with deterministic evaluator, no correct_fn

**Files touched**:
- `parliament/services/quality_loop.py` — new file
- `parliament/management/commands/generate_meeting_reports.py` — refactor to use `run_quality_loop()`
- `parliament/services/brief_generator.py` — refactor to use `run_quality_loop()`

---

## Testing Strategy

Each item includes tests:

| Item | Test File | Tests |
|------|-----------|-------|
| 1. Mention validation | `parliament/tests/test_gemini_client.py` | speaker found/not-found in excerpt, constituency mismatch |
| 2. Brief correction loop | `parliament/tests/test_brief_generator.py` | FIX triggers correction, REJECT circuit breaker, QualityLog count |
| 3. Evaluator fail-safe | `parliament/tests/test_evaluator.py` | API error returns AMBER not PASS, evaluator_error flag set |
| 4. Context staleness | `parliament/tests/test_context_builder.py` | old date warns, recent date silent |
| 5. Fuzzy matching | `parliament/tests/test_report_generator.py` | typo matches with ratio>=0.85, low ratio skipped |
| 6. MP normalisation | `parliament/tests/test_gemini_client.py` | honorifics stripped, apostrophes normalised |
| 7. Mention evaluator | `parliament/tests/test_evaluator.py` | confidence scores, warning generation |
| 8. Unified loop | `parliament/tests/test_quality_loop.py` | PASS/FIX/REJECT paths, circuit breaker, logging |

## Risks & Mitigations

- **Fuzzy matching false positives** (Item 5): 0.85 threshold is conservative. Log all fuzzy matches for review.
- **MP normalisation over-stripping** (Item 6): "Dr. Mah Hang Soon" should keep "Mah Hang Soon". Only strip prefix, never surname.
- **Unified loop refactor** (Item 8): Changing working code. Mitigated by existing test suite (1212 tests) + new tests.
- **Migration on production** (Items 1, 7): New nullable fields with defaults — zero-risk migration.

## Dependencies

- Sprint 7.1 has no inter-item dependencies (all 4 can be built in parallel)
- Sprint 7.2: Items 5-7 are independent. Item 8 depends on Item 2 (brief loop) being done first.
- No new pip dependencies. All use stdlib (difflib, re, dataclasses).
