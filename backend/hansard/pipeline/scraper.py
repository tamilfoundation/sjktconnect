"""Discover new Hansard PDFs on parlimen.gov.my.

Since parlimen.gov.my has an invalid SSL certificate and the listing page
is hard to parse reliably, we probe candidate URLs using HEAD requests.
The known URL pattern is: DR-DDMMYYYY.pdf

Parliament sits Monday-Thursday during sitting periods (~70-80 days/year).
"""

import logging
from datetime import date, timedelta

import requests

logger = logging.getLogger(__name__)

BASE_URL = "https://www.parlimen.gov.my/files/hindex/pdf"
HEAD_TIMEOUT = 15


def discover_new_pdfs(
    start_date: date,
    end_date: date,
    *,
    skip_weekends: bool = True,
) -> list[dict]:
    """Probe parlimen.gov.my for Hansard PDFs in a date range.

    Args:
        start_date: First date to check (inclusive).
        end_date: Last date to check (inclusive).
        skip_weekends: Skip Saturday (5) and Sunday (6). Parliament
            doesn't sit on weekends.

    Returns:
        List of dicts with keys: sitting_date, pdf_url, pdf_filename.
        Only includes dates where a PDF was found (HTTP 200).
    """
    found = []
    current = start_date

    while current <= end_date:
        if skip_weekends and current.weekday() >= 5:
            current += timedelta(days=1)
            continue

        pdf_url = _build_url(current)
        if _pdf_exists(pdf_url):
            found.append({
                "sitting_date": current,
                "pdf_url": pdf_url,
                "pdf_filename": _build_filename(current),
            })

        current += timedelta(days=1)

    return found


def _build_url(sitting_date: date) -> str:
    """Build the Hansard PDF URL for a given date."""
    filename = _build_filename(sitting_date)
    return f"{BASE_URL}/{filename}"


def _build_filename(sitting_date: date) -> str:
    """Build the PDF filename: DR-DDMMYYYY.pdf."""
    return f"DR-{sitting_date.strftime('%d%m%Y')}.pdf"


def _pdf_exists(url: str) -> bool:
    """Check if a PDF exists at the URL via HEAD request.

    Uses verify=False because parlimen.gov.my has an invalid SSL cert.
    """
    try:
        response = requests.head(url, timeout=HEAD_TIMEOUT, verify=False)
        exists = response.status_code == 200
        if exists:
            logger.info("Found: %s", url)
        return exists
    except requests.RequestException as e:
        logger.warning("HEAD request failed for %s: %s", url, e)
        return False
