"""Ingest the Kamar Khas (Special Chamber) Hansard for a sitting.

The main Dewan Rakyat Hansard (``DR-<date>.pdf``) and the Special Chamber
Hansard (``KKDR-<date>-N.pdf``) are SEPARATE documents for the same sitting
date. Most Tamil-school debate happens in Kamar Khas — which the main
pipeline never fetched (it only downloads DR-*.pdf), so the June 2026
session showed zero Tamil-school activity despite heavy Kamar Khas debate.

This module fetches every KKDR part for a sitting, searches it for
Tamil-school keywords, and appends ``HansardMention`` rows tagged
``chamber=KAMAR_KHAS`` to the existing sitting (Option A: one sitting row
per date, mentions distinguished by chamber). New mentions flow into the
normal analyse/brief steps automatically (they start with ai_summary="").
"""

import logging
import tempfile

from django.utils import timezone

from hansard.models import HansardMention, SchoolAlias
from hansard.pipeline.downloader import NoPdfAvailable, download_hansard
from hansard.pipeline.extractor import extract_text
from hansard.pipeline.keywords import get_all_keywords
from hansard.pipeline.matcher import match_mentions
from hansard.pipeline.searcher import search_keywords

logger = logging.getLogger(__name__)

BASE_URL = "https://www.parlimen.gov.my/files/hindex/pdf"
MAX_PARTS = 6  # KKDR-<date>-1.pdf .. -6.pdf; stop at first missing part


def kamar_khas_urls(sitting_date, max_parts=MAX_PARTS):
    """Build candidate Kamar Khas PDF URLs for a date (parts 1..N)."""
    ds = sitting_date.strftime("%d%m%Y")
    return [f"{BASE_URL}/KKDR-{ds}-{i}.pdf" for i in range(1, max_parts + 1)]


def process_kamar_khas(sitting, dest_dir=None, match=True):
    """Fetch + process this sitting's Kamar Khas PDF(s).

    Idempotent: clears any existing KAMAR_KHAS mentions for the sitting
    first (MAIN mentions are never touched), then re-creates from the live
    PDFs. Always stamps ``kamar_khas_checked_at`` so the daily pipeline
    won't re-download + re-analyse (repeated Gemini cost) next run.

    Returns ``{"parts": int, "mentions": int, "matched": int}``.
    """
    dest_dir = dest_dir or tempfile.mkdtemp(prefix="kkhansard_")
    keywords = get_all_keywords()

    # Idempotent re-run: drop prior KK mentions only.
    sitting.mentions.filter(chamber=HansardMention.Chamber.KAMAR_KHAS).delete()

    new_mentions = []
    parts = 0
    seen = set()  # dedup within KK by (part, page, speaker)
    for part_no, url in enumerate(kamar_khas_urls(sitting.sitting_date), start=1):
        try:
            pdf_path = download_hansard(url, dest_dir)
        except NoPdfAvailable:
            break  # no (more) Kamar Khas parts for this date
        parts += 1
        pages = extract_text(pdf_path)
        for m in search_keywords(pages, keywords):
            key = (part_no, m["page_number"], m.get("speaker_name", ""))
            if key in seen:
                continue
            seen.add(key)
            new_mentions.append(HansardMention(
                sitting=sitting,
                chamber=HansardMention.Chamber.KAMAR_KHAS,
                page_number=m["page_number"],
                verbatim_quote=m["verbatim_quote"],
                context_before=m["context_before"],
                context_after=m["context_after"],
                keyword_matched=m["keyword_matched"],
                mp_name=m.get("speaker_name", ""),
                mp_constituency=m.get("speaker_constituency", ""),
            ))

    HansardMention.objects.bulk_create(new_mentions)

    sitting.mention_count = sitting.mentions.count()
    sitting.kamar_khas_checked_at = timezone.now()
    sitting.save(update_fields=["mention_count", "kamar_khas_checked_at"])

    matched = 0
    if match and new_mentions and SchoolAlias.objects.exists():
        unmatched = sitting.mentions.filter(matched_schools__isnull=True)
        if unmatched.exists():
            matched = match_mentions(unmatched).get("matched", 0)

    logger.info(
        "Kamar Khas %s: %d part(s), %d mention(s), %d matched",
        sitting.sitting_date, parts, len(new_mentions), matched,
    )
    return {"parts": parts, "mentions": len(new_mentions), "matched": matched}
