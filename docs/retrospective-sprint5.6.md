# Sprint 5.6 Retrospective — Report Quality Fixes

**Date**: 2026-03-06
**Duration**: ~1 session (continuation of Sprint 5.5 quality review)

## What Was Built

Fixed 12 quality issues identified during user review of Hansard intelligence reports:

1. **PDF text artefact cleanup** — `clean_extracted_text()` in normalizer strips garbled fragments, double periods, orphaned punctuation from pdfplumber output
2. **SJK(T) bracket post-processing** — regex `(SJK(T))` → `SJK(T)` in both brief and report generators
3. **Meeting report prompt rewrite** — journalistic headline, hook lead paragraph, structured MP Scorecard with predefined taxonomy
4. **Illustration prompt fix** — Tamil Indian ethnicity specification, positive-only text constraint
5. **Blurb extraction fix** — `extractSummary()` in BriefsList.tsx now uses lead paragraph

## What Went Well

- User's systematic quality review identified concrete, fixable issues across text, content, and illustration
- External AI review provided the MP Scorecard taxonomy idea (Stance/Impact/Ministerial Response) which replaced subjective labels
- Regenerated 1st Meeting 2025 as test case — all improvements verified working
- Clean commit: 5 files changed, 136 insertions, 56 deletions

## What Went Wrong

- 2nd Meeting 2023 (intended test target) had only 1 Tamil school mention across 19 sittings — too sparse for meaningful testing. Had to pivot to 1st Meeting 2025.
- Background tasks from previous session were lost at session boundary — had to re-check state manually.

## Design Decisions

- **Structured taxonomy over free text** — MP Scorecard uses predefined values (Advocacy/Inquiry/Critical for Stance) instead of letting Gemini hallucinate labels like "Substantive" or "Routine"
- **Lead paragraph as blurb** — The hook paragraph before Key Findings is better for reader engagement than bullet-point summaries
- **Positive illustration constraints** — "MUST contain ONLY X" works better than "do NOT include Y" with Imagen 4.0

## Numbers

- 5 files modified
- 6 sitting briefs regenerated (1st Meeting 2025)
- 1 meeting report + illustration regenerated
- 0 new tests (prompt/content quality changes, not testable with unit tests)
- All 1120 existing tests pass
