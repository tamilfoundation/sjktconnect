# Retrospective — Sprint 0.3: School Name Matching

**Date**: 25 February 2026
**Sprint duration**: Single session
**Version**: Part of Phase 0 — Parliament Watch

---

## What Was Built

- **SchoolAlias model** — stores multiple name variants per school (official, short, common, SJKT, Hansard-discovered)
- **MentionedSchool model** — bridge linking HansardMention to School with confidence score and match method
- **seed_aliases command** — auto-generates ~4 aliases per school from official/short names
- **Matcher pipeline** — two-pass: exact alias lookup (100% confidence), then trigram similarity with difflib fallback on SQLite
- **Stop words module** — 20 high-frequency words excluded from fuzzy matching
- **Code simplification pass** — 12 improvements across 8 files (dead code removal, constant hoisting, caching)
- 41 new tests (111 total)

## What Went Well

1. **Two-pass matching design** worked cleanly — exact match first (cheap, high confidence), trigram only for unresolved mentions
2. **Malay boundary word detection** solved the school name extraction problem elegantly — MPs say "SJK(T) Ladang Bikam di kawasan..." and the boundary words ("di", "yang", "untuk") naturally delimit the school name
3. **Progressive shortening** (trimming candidates word-by-word from the right) handles cases where context words get captured after the school name
4. **Difflib fallback** means the matcher works identically on SQLite (dev) and PostgreSQL (prod) — no need for pg_trgm locally
5. **Code simplification** caught real issues: constants recreated per call, signals resolving models on every save, unused imports/variables

## What Went Wrong

1. **Nothing significant** — Sprint 0.3 was well-scoped and matched the roadmap closely

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| Two-pass matching (exact then trigram) | Exact match is fast and definitive; trigram only needed for partial/fuzzy names |
| Confidence < 80% = needs_review | Avoids false positives reaching the public page without human review |
| HANSARD alias type preserved during re-seeding | Human-discovered aliases from real data are valuable; don't delete them |
| Boundary words in Malay | Hansard text is in Malay; English boundary words would miss everything |
| Module-level constants for regex/sets | Avoid per-call compilation overhead in hot paths |
| Cached tracked models in signals | `_get_tracked_models()` was called on every post_save/post_delete across all models |

## Numbers

| Metric | Value |
|--------|-------|
| Tests added | 41 |
| Total tests | 111 |
| Files created | 4 (matcher, stop_words, models, seed_aliases) |
| Files modified by simplifier | 8 |
| Simplifications applied | 12 |
| Pipeline steps | 7 (download → extract → normalise → search → match → store → report) |
