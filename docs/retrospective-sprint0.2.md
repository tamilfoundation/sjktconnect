# Retrospective — Sprint 0.2: Hansard Download + Text Extraction + Keyword Search

**Date**: 2026-02-25
**Sprint goal**: Build a pipeline that downloads a Hansard PDF, extracts text, and finds Tamil school mentions with context.

---

## What Was Built

- `hansard` Django app with HansardSitting and HansardMention models
- Five pipeline modules: downloader (HTTP with retries), extractor (pdfplumber), normalizer (SJK(T) variant handling), searcher (keyword matching with ±500 chars context), keywords (19 search terms)
- `process_hansard <url>` management command with automatic date extraction from filename
- 44 tests covering all pipeline modules and the management command
- Admin registration for both new models

## What Went Well

- **Pipeline architecture is clean.** Five small, focused modules that are individually testable. The management command just orchestrates them.
- **Real Hansard PDFs worked first try.** pdfplumber extracted text from all 184 pages of a real Hansard without issues. No OCR needed — text-based PDFs as assumed.
- **Normaliser caught real variants.** The SJK(T)/SJKT/S.J.K.(T) normalisation worked correctly on real parliamentary text.
- **Test-driven approach paid off.** Writing tests alongside code caught the dedup bug (searcher was too aggressive) before it hit production.

## What Went Wrong

- **Mock patching on Windows.** `unittest.mock.patch("hansard.management.commands.process_hansard.extract_text")` failed on Python 3.11 Windows due to module path resolution. Fixed by using `patch.object()` on the imported module instead.
- **Dual Python versions.** `pip install` installed to Python 3.13 while pytest runs on 3.11. Lost a few minutes debugging "module not found".
- **parlimen.gov.my SSL certificate is invalid.** Had to add a domain-specific `verify=False` to the downloader. Discovered only at real-data testing time.
- **Current session had no Tamil school mentions.** Scanned 7 PDFs from the Jan-Mar 2026 session before finding mentions in 2 older sittings. Budget debates are more productive — the Jan session was mostly procedural.

## Design Decisions

1. **Normalise then search** (not regex-per-variant). Canonicalising all SJK(T) variants into one form means the keyword list stays simple and new variants just need a normaliser rule.
2. **Store both verbatim and context.** The verbatim quote preserves original casing/formatting for the review UI (Sprint 0.5). Context (±500 chars) feeds the AI in Sprint 0.4.
3. **Dedup by (page, position, keyword).** Initially used position bucketing (pos // 50) which was too aggressive — legitimate nearby mentions got suppressed. Switched to exact (page, pos, keyword) tuples.
4. **Primary vs secondary keywords.** Split keywords into high-confidence (sjk(t), sekolah tamil) and context-dependent (vernacular school, pendidikan tamil). Both searched in Sprint 0.2; Sprint 0.3 matching will weight them differently.
5. **Date extraction from filename.** Hansard PDFs follow DR-DDMMYYYY.pdf pattern. Automatic extraction avoids requiring `--sitting-date` for every run.

## Numbers

| Metric | Value |
|--------|-------|
| New tests | 44 |
| Total tests | 70 |
| New files | 18 |
| Modified files | 4 |
| Real PDFs tested | 3 |
| Real mentions found | 5 |
| Keyword variants found | 2 ("sjk(t)", "sekolah jenis kebangsaan tamil") |
| Pipeline time per PDF | ~10-15 seconds (download + extract + search) |
