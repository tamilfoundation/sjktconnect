# Retrospective — Hansard Pipeline Backfill

**Date**: 2026-03-04
**Scope**: Process all 5 Malaysian Parliament sessions (Feb 2025 – Mar 2026) through the full Hansard pipeline

## What Was Built

Bulk processing of Hansard PDFs from parlimen.gov.my through the full pipeline:
- 131 PDFs discovered across 5 parliament sessions
- 97 sittings successfully processed (34 non-sitting days correctly rejected)
- 193 Tamil school mentions found and AI-analysed with Gemini 2.5 Flash
- 36 MP scorecards created/updated
- 33 sitting briefs generated

Code changes: scraper fix (HEAD→GET), Gemini client retry logic, analysis filter fix, brief generator filter fix, updated tests.

## What Went Well

1. **Gemini 2.5 Flash on Paid Tier 1** — 131 mentions analysed in ~15 minutes with zero failures. The 1000 RPM / 10K RPD quota was more than adequate.
2. **Pipeline robustness** — The existing pipeline handled 131 PDFs with only minor fixes needed. The architecture (download → extract → search → store) scaled well.
3. **Test coverage** — All 14 scraper tests, 13 brief generator tests, and full suite (211 tests) passed after fixes.

## What Went Wrong

1. **parlimen.gov.my blocks HEAD requests** — Returned 403 for HEAD but 200 for GET. Wasted time debugging before discovering this. Fix: ranged GET (`Range: bytes=0-0`).

2. **Supabase connection pooler drops writes** — The transaction pooler (port 6543) silently dropped sequential writes. Multiple analysis runs appeared successful (200 OK from Gemini) but DB writes didn't persist. This was the single biggest time sink across 3 sessions.

3. **Misdiagnosed the "unanalysed" bug** — Spent significant time thinking writes were being dropped when the real issue was the `mp_name=''` filter. Gemini legitimately returns empty MP names when the speaker can't be identified from the verbatim quote. The correct "analysed" check is `ai_summary != ''`, not `mp_name != ''`.

4. **Non-sitting day PDFs** — parlimen.gov.my returns HTTP 200 with HTML error pages for non-sitting days (Fridays, recesses). pdfplumber fails with "No /Root object". These aren't corrupted PDFs — parliament simply didn't sit on those days. 34 out of 131 URLs were non-sitting days.

5. **Windows line endings in shell scripts** — `batch_urls.py` output had `\r\n`, causing `%0D` to be appended to URLs. Fix: `tr -d '\r'` in shell scripts.

## Design Decisions

1. **Ranged GET over HEAD** — `Range: bytes=0-0` returns a single byte, almost as cheap as HEAD, but parlimen.gov.my allows it. Also accepts 200 (server ignores Range) and 206 (proper partial content).

2. **`ai_summary` as analysis indicator** — Changed from `mp_name=''` to `ai_summary=''` for detecting unanalysed mentions. This is more semantically correct: a mention is "analysed" when the AI has processed it, regardless of whether it identified the speaker.

3. **`connection.close()` after writes** — Added to `analyse_mentions` command as defence against stale pooled connections. May not be strictly necessary on direct connections but prevents future issues.

4. **No trigram matching this sprint** — 125 mentions with unidentified schools. Trigram similarity over remote Supabase was too slow (343K queries). Deferred to a future sprint — may need batch processing or local DB approach.

## Numbers

| Metric | Value |
|--------|-------|
| Parliament sessions covered | 5 (Feb 2025 – Mar 2026) |
| PDFs discovered | 131 |
| Sittings processed | 97 |
| Non-sitting days rejected | 34 |
| Mentions found | 193 |
| Mentions AI-analysed | 193 (100%) |
| MP scorecards | 36 |
| Sitting briefs | 33 |
| Gemini API calls | ~450 (across multiple runs) |
| Files changed | 6 |
| New tests | 1 (test_returns_true_on_206) |
| Sessions required | 3 (connection pooler issues, context limits) |
