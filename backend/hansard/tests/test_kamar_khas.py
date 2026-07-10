"""Tests for Kamar Khas (Special Chamber) Hansard ingestion."""

from datetime import date
from unittest.mock import patch

import pytest

from hansard.models import HansardMention, HansardSitting
from hansard.pipeline.downloader import NoPdfAvailable
from hansard.pipeline import kamar_khas


def _sitting(d="2026-06-22", status=None):
    return HansardSitting.objects.create(
        sitting_date=date.fromisoformat(d),
        status=status or HansardSitting.Status.COMPLETED,
        pdf_url="https://x/DR.pdf", pdf_filename="DR.pdf",
    )


def _match(page, speaker, kw="sjk(t)"):
    return {
        "page_number": page, "keyword_matched": kw,
        "verbatim_quote": f"{speaker} spoke about {kw}",
        "context_before": "", "context_after": "",
        "speaker_name": speaker, "speaker_constituency": "Klang",
    }


def test_kamar_khas_urls_format():
    urls = kamar_khas.kamar_khas_urls(date(2026, 6, 22), max_parts=2)
    assert urls[0].endswith("/KKDR-22062026-1.pdf")
    assert urls[1].endswith("/KKDR-22062026-2.pdf")


@pytest.mark.django_db
def test_process_creates_kamar_khas_mentions_and_stamps_checked_at():
    sitting = _sitting()
    # a pre-existing MAIN mention that must NOT be touched
    HansardMention.objects.create(
        sitting=sitting, chamber=HansardMention.Chamber.MAIN,
        page_number=1, verbatim_quote="main chamber mention",
    )

    # part 1 downloads, part 2 is absent → loop stops
    def fake_download(url, dest_dir):
        if url.endswith("-1.pdf"):
            return "/tmp/kk.pdf"
        raise NoPdfAvailable("File does not exist")

    with patch.object(kamar_khas, "download_hansard", side_effect=fake_download), \
         patch.object(kamar_khas, "extract_text", return_value=[(1, "text")]), \
         patch.object(kamar_khas, "get_all_keywords", return_value=["sjk(t)"]), \
         patch.object(kamar_khas, "search_keywords",
                      return_value=[_match(1, "Ganabatirau"), _match(1, "Wong Kah Woh")]):
        result = kamar_khas.process_kamar_khas(sitting)

    assert result == {"parts": 1, "mentions": 2, "matched": 0}
    kk = sitting.mentions.filter(chamber=HansardMention.Chamber.KAMAR_KHAS)
    assert kk.count() == 2
    assert sitting.mentions.filter(chamber=HansardMention.Chamber.MAIN).count() == 1  # untouched
    sitting.refresh_from_db()
    assert sitting.kamar_khas_checked_at is not None
    assert sitting.mention_count == 3


@pytest.mark.django_db
def test_process_is_idempotent():
    sitting = _sitting()
    with patch.object(kamar_khas, "download_hansard",
                      side_effect=lambda u, d: "/tmp/kk.pdf" if u.endswith("-1.pdf") else _raise()), \
         patch.object(kamar_khas, "extract_text", return_value=[(1, "t")]), \
         patch.object(kamar_khas, "get_all_keywords", return_value=["sjk(t)"]), \
         patch.object(kamar_khas, "search_keywords", return_value=[_match(1, "MP A")]):
        kamar_khas.process_kamar_khas(sitting)
        kamar_khas.process_kamar_khas(sitting)  # re-run
    assert sitting.mentions.filter(chamber=HansardMention.Chamber.KAMAR_KHAS).count() == 1


@pytest.mark.django_db
def test_process_stamps_checked_at_even_when_no_pdf():
    """No Kamar Khas PDF → 0 mentions but still checked, so the daily
    pipeline won't retry it forever."""
    sitting = _sitting()
    with patch.object(kamar_khas, "download_hansard",
                      side_effect=NoPdfAvailable("File does not exist")), \
         patch.object(kamar_khas, "get_all_keywords", return_value=["sjk(t)"]):
        result = kamar_khas.process_kamar_khas(sitting)
    assert result == {"parts": 0, "mentions": 0, "matched": 0}
    sitting.refresh_from_db()
    assert sitting.kamar_khas_checked_at is not None


def _raise():
    raise NoPdfAvailable("File does not exist")
