"""Regression tests for the 2026-07 check-hansards OOM incident.

Root cause: extractor never flushed pdfplumber's per-page cache, so a
122-page Hansard peaked at ~640 MB and OOM-killed the 512 MB job; the
stuck sitting was then orphaned in PROCESSING forever.
"""

from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest
from django.utils import timezone

from hansard.management.commands.run_hansard_pipeline import Command
from hansard.models import HansardSitting
from hansard.pipeline.extractor import extract_text


def _sitting(date, status):
    return HansardSitting.objects.create(
        sitting_date=date,
        status=status,
        pdf_url="https://example.test/x.pdf",
        pdf_filename="x.pdf",
    )


@pytest.mark.django_db
def test_reset_recovers_stuck_processing_regardless_of_age():
    today = timezone.localdate()
    old_proc = _sitting(today - timedelta(days=30), HansardSitting.Status.PROCESSING)
    recent_nopdf = _sitting(today - timedelta(days=2), HansardSitting.Status.NO_PDF)
    old_nopdf = _sitting(today - timedelta(days=40), HansardSitting.Status.NO_PDF)
    completed = _sitting(today - timedelta(days=1), HansardSitting.Status.COMPLETED)

    n = Command()._reset_recent_failures(7)

    for s in (old_proc, recent_nopdf, old_nopdf, completed):
        s.refresh_from_db()

    assert old_proc.status == HansardSitting.Status.PENDING       # stuck crash, any age
    assert recent_nopdf.status == HansardSitting.Status.PENDING   # late-landing PDF
    assert old_nopdf.status == HansardSitting.Status.NO_PDF       # old discovery noise left alone
    assert completed.status == HansardSitting.Status.COMPLETED    # never touch done work
    assert n == 2


def test_extract_text_flushes_each_page_cache(tmp_path):
    """The memory fix: every page's pdfplumber cache must be flushed."""
    pdf_file = tmp_path / "hansard.pdf"
    pdf_file.write_bytes(b"%PDF-1.7 stub")  # only existence is checked; pdfplumber mocked

    page1 = MagicMock(); page1.extract_text.return_value = "page one"
    page2 = MagicMock(); page2.extract_text.return_value = "page two"
    fake_pdf = MagicMock(); fake_pdf.pages = [page1, page2]
    ctx = MagicMock(); ctx.__enter__.return_value = fake_pdf; ctx.__exit__.return_value = False

    with patch("hansard.pipeline.extractor.pdfplumber.open", return_value=ctx):
        result = extract_text(pdf_file)

    assert result == [(1, "page one"), (2, "page two")]
    page1.flush_cache.assert_called_once()
    page2.flush_cache.assert_called_once()
