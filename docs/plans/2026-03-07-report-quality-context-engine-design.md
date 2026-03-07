# Report Quality & Context Engine v2.0 — Design

## Problem

The Hansard pipeline produces three outputs — mentions, sitting briefs, and meeting reports — each via a Gemini API call. Quality issues identified in the 3rd Meeting 2025 report review:

1. **Minister hallucination** (FLAG-001): Gemini generated wrong minister name. No cabinet reference data exists.
2. **Unknown MP in responses** (FLAG-002): Executive response rows lack minister identification.
3. **Unlinked school names** (FLAG-003): 294 schools with "Ladang" in name aren't matched when MPs drop it.
4. **Report not audience-ready** (FLAG-004): Too jargon-heavy, no plain-language summary, no Hansard quotes, acronyms unexpanded.
5. **Impact classification imbalance** (FLAG-005): 10/15 MPs classified as "General Rhetoric".
6. **26% duplicate mentions**: 18/68 same-speaker same-page duplicates not caught.
7. **Brief format**: Database records, not report-like prose. No executive summary or verbatim quotes.
8. **Mention tense inconsistency**: Mix of past and present tense.

## Approach: Three Phased Sprints

### Sprint 6.1 — Foundation & Data Layer
- Versioned context JSON (`data/report-context.json` v2.0)
- `context_builder.py` service (loads JSON + runtime data)
- MP `portfolio` field + migration + scraper update
- `executive_response_attribution` evaluator criterion
- Mention deduplication fix (same-speaker same-page)
- "Without Ladang" alias variant in `seed_aliases`
- WAT workflow for context maintenance

### Sprint 6.2 — Pipeline Prompts
- Mention analysis prompt: enforce past tense
- Brief generator: executive summary → details → verbatim quotes (100-350 words)
- Report generator: layered sections (plain summary, scorecard with legend, RPM-aligned policy signals)
- Wire `context_builder` into all three generators
- Regenerate 3rd Meeting 2025 for validation

### Sprint 6.3 — Frontend & Polish
- Brief detail page (URL, view, template)
- Link briefs from meeting report
- Report template update for new sections
- Commit model upgrade (gemini-3-pro-preview)
- Deploy + end-to-end validation

## Architecture

```
data/report-context.json (v2.0, curated)
        │
        ▼
context_builder.py ──────► loads JSON
        │                  queries MP.portfolio
        │                  queries School names
        │                  returns merged dict
        ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ gemini_client │  │ brief_gen    │  │ report_gen   │
│ (mentions)   │  │ (briefs)     │  │ (reports)    │
└──────────────┘  └──────────────┘  └──────────────┘
        │                │                │
        ▼                ▼                ▼
   evaluator ──► corrector ──► learner (existing quality engine)
```

### WAT Framework Integration
- **Workflow**: `Settings/_workflows/context-maintenance.md` — when to update JSON, version bump rules
- **Agent**: Claude (reads workflow, runs tools)
- **Tool**: `context_builder.py` (deterministic assembly), `data/report-context.json` (reference data)

## Context JSON v2.0 Structure

```json
{
  "version": "2.0",
  "last_updated": "2026-03-07",
  "report_config": { "output_language": "en", "style": "journalistic-neutral" },
  "domain": { "focus": "SJK(T) Tamil vernacular schools", "challenges": [...] },
  "cabinet": { "education": {...}, "finance": {...} },
  "glossary": { "SJK(T)": "...", "PPKI": "...", ... },
  "taxonomy": { "stance": [...], "impact": [...], "verdict": [...] },
  "national_education_plan": { "name": "RPM 2026-2035", "commitments": [...] },
  "national_baseline": { "total_sjkt": 528, ... },
  "session_history": { "15th_parliament": {...} }
}
```

## Out of Scope
- Gemini 3 Pro for mentions/briefs (stays on Flash — cost)
- Frontend redesign beyond brief detail page
- MP profile page (separate feature)
