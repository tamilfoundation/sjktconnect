# Retrospective — Sprint 0.3: School Name Matching

**Date**: 2026-02-25
**Sprint goal**: Link Hansard mentions to specific School records using alias table + trigram matching.

---

## What Was Built

- `SchoolAlias` model — stores multiple name variants per school (OFFICIAL, SHORT, COMMON, HANSARD types)
- `MentionedSchool` bridge model — links HansardMention to School with confidence score, match method, and review flag
- `seed_aliases` management command — auto-generates ~4 aliases per school from official/short names
- `stop_words.py` — 20 high-frequency words excluded from fuzzy matching
- `matcher.py` — two-pass matching: exact alias lookup then trigram similarity (pg_trgm on PostgreSQL, difflib on SQLite)
- pg_trgm extension migration (conditional — skips on SQLite)
- Matcher integrated into `process_hansard` pipeline as Step 7

## What Went Well

- **Progressive shortening solved the boundary problem.** The regex over-captures (e.g., "SJK(T) Ladang Bikam memerlukan peruntukan") but trimming word-by-word from the right finds "SJK(T) Ladang Bikam" via exact alias match. Clean separation of concerns: extractor captures generously, matcher handles precision.
- **Malay boundary words are effective.** Stopping candidate extraction at "dan", "di", "yang", "untuk", etc. catches most sentence-level boundaries without complex NLP.
- **SQLite fallback works seamlessly.** difflib.SequenceMatcher provides reasonable trigram-like similarity for local development. No PostgreSQL needed to run the full test suite.
- **All 111 tests pass first time** (after the two matcher fixes). The test-driven approach from Sprint 0.2 carried over well.

## What Went Wrong

- **Regex terminator included `(` and `)`.** The initial regex `(?:\s*[,\.\(\)]|$)` consumed the `(` in `SJK(T)`, breaking multi-school detection. Text like "SJKT Ladang Bikam dan SJK(T) Batu Arang" would only find the first school because the `(` of the second `SJK(T)` was consumed as a terminator for the first match. Fixed by switching to a prefix-based extractor that doesn't use consuming terminators.
- **Word count limit too restrictive.** Initial `<= 6 words` filter rejected valid candidates that had trailing non-name words (7+ words captured by the regex). The real fix was the boundary word approach, which naturally limits capture length.
- **Test failure: exact match returned 0 results.** The candidate "ladang bikam memerlukan peruntukan sebanyak rm2 juta" (7 words) was rejected by the word count filter, so no candidate was passed to the matcher at all. Only caught by running the test.

## Design Decisions

1. **Prefix-based extraction, not regex terminator.** Find the prefix pattern, then grab words after it until a boundary word appears. Simpler, more robust, and handles multi-school text correctly.
2. **Progressive shortening for boundary detection.** Rather than trying to detect school name boundaries in the extractor, let the alias database decide. Try "sjk(t) ladang bikam memerlukan" → "sjk(t) ladang bikam" → "sjk(t) ladang" until an exact match is found.
3. **Two-pass matching.** Exact first (fast, 100% confidence), trigram second (slower, lower confidence). Most real matches will be exact — trigram is a safety net for abbreviations and OCR errors.
4. **Conditional pg_trgm migration.** RunPython checks `connection.vendor` — no-op on SQLite. This means local dev works without PostgreSQL while production gets native trigram support.
5. **HANSARD alias type preserved during re-seed.** Manual aliases discovered from actual Hansard text should survive `seed_aliases --clear`.

## Numbers

| Metric | Value |
|--------|-------|
| New tests | 41 |
| Total tests | 111 |
| New files | 8 |
| Modified files | 6 |
| New models | 2 (SchoolAlias, MentionedSchool) |
| New migrations | 2 |
| New pipeline modules | 2 (matcher.py, stop_words.py) |
| New management commands | 1 (seed_aliases) |
| Aliases per school | ~4 (official, short, stripped, SJKT variant) |
| Boundary words | 20 (Malay conjunctions/prepositions/verbs) |
| Stop words | 20 (school prefixes + location words) |
