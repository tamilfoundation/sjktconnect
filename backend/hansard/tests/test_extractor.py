"""Tests for hansard/pipeline/extractor.py (TD-12, 2026-06-27).

Coverage target: 26% → 100%. The function `extract_text` was previously
untested directly (only via integration paths that mocked it out).

Fixture PDFs are generated programmatically with reportlab into tmp_path
so no binary blobs land in git. Each test creates exactly the shape it
needs (size, content, validity).
"""

from pathlib import Path

import pytest
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from hansard.pipeline.extractor import extract_text


# ─── PDF fixture generators ─────────────────────────────────────────────


def _make_pdf(path: Path, pages: list[str]) -> None:
    """Generate a PDF at `path` with one page per string in `pages`.

    Each page contains the corresponding string at (100, 750). An empty
    string produces a page with no text content (matching real-world
    Hansard PDFs that occasionally have blank pages).
    """
    c = canvas.Canvas(str(path), pagesize=A4)
    for text in pages:
        if text:
            c.drawString(100, 750, text)
        c.showPage()
    c.save()


# ─── Tests ──────────────────────────────────────────────────────────────


def test_file_not_found_raises(tmp_path):
    """Non-existent path raises FileNotFoundError with a clear message."""
    missing = tmp_path / "does_not_exist.pdf"
    with pytest.raises(FileNotFoundError) as exc:
        extract_text(missing)
    assert str(missing) in str(exc.value)


def test_accepts_str_and_path(tmp_path):
    """Function accepts both str and pathlib.Path."""
    pdf = tmp_path / "tiny.pdf"
    _make_pdf(pdf, ["hello"])

    via_path = extract_text(pdf)
    via_str = extract_text(str(pdf))

    assert via_path == via_str
    assert len(via_path) == 1


def test_single_page_extraction(tmp_path):
    """Single-page PDF returns one (page_number, text) tuple."""
    pdf = tmp_path / "single.pdf"
    _make_pdf(pdf, ["SJK(T) Subramaniya Barathee mentioned in Parliament"])

    result = extract_text(pdf)

    assert len(result) == 1
    page_num, text = result[0]
    assert page_num == 1
    assert "SJK(T) Subramaniya Barathee" in text


def test_multi_page_extraction_order(tmp_path):
    """Multi-page PDF returns pages in order, page numbers 1-based."""
    pdf = tmp_path / "multi.pdf"
    _make_pdf(pdf, ["page one alpha", "page two beta", "page three gamma"])

    result = extract_text(pdf)

    assert len(result) == 3
    assert [p[0] for p in result] == [1, 2, 3]
    assert "alpha" in result[0][1]
    assert "beta" in result[1][1]
    assert "gamma" in result[2][1]


def test_blank_pages_yield_empty_string(tmp_path):
    """Blank pages return an empty string, never None."""
    pdf = tmp_path / "blanks.pdf"
    _make_pdf(pdf, ["has text", "", "more text"])

    result = extract_text(pdf)

    assert len(result) == 3
    assert "has text" in result[0][1]
    assert result[1][1] == ""  # not None
    assert "more text" in result[2][1]


def test_large_pdf_triggers_progress_logging(tmp_path, caplog):
    """≥20 pages exercises the periodic progress-log branch."""
    import logging
    pdf = tmp_path / "large.pdf"
    _make_pdf(pdf, [f"page {i}" for i in range(1, 26)])  # 25 pages

    with caplog.at_level(logging.INFO, logger="hansard.pipeline.extractor"):
        result = extract_text(pdf)

    assert len(result) == 25
    # Periodic log fires at i=20; final summary always logs.
    progress_logs = [r for r in caplog.records if "Processed" in r.message]
    summary_logs = [r for r in caplog.records if "Extraction complete" in r.message]
    assert len(progress_logs) >= 1, "Expected periodic progress log at page 20"
    assert len(summary_logs) == 1


def test_malformed_pdf_raises(tmp_path):
    """A non-PDF file (random bytes) raises some exception — does not
    silently return empty. The exact exception class depends on the
    pdfplumber/pdfminer version; we assert that an exception IS raised."""
    bogus = tmp_path / "not_actually.pdf"
    bogus.write_bytes(b"this is not a PDF, just random bytes\x00\x01\x02")

    with pytest.raises(Exception):
        extract_text(bogus)


def test_summary_log_counts_non_empty_pages(tmp_path, caplog):
    """Final summary log reports total pages + count of non-empty pages."""
    import logging
    pdf = tmp_path / "mixed.pdf"
    _make_pdf(pdf, ["alpha", "", "gamma", ""])  # 4 pages, 2 with text

    with caplog.at_level(logging.INFO, logger="hansard.pipeline.extractor"):
        extract_text(pdf)

    summary = [r for r in caplog.records if "Extraction complete" in r.message]
    assert len(summary) == 1
    msg = summary[0].message
    assert "4 pages" in msg
    assert "2 with text" in msg
