"""Scrape the parliamentary calendar from parlimen.gov.my.

Fetches the Dewan Rakyat calendar page, parses meeting periods and
sitting dates, then creates/updates ParliamentaryMeeting records.
"""

import logging
import re
from datetime import date
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

CALENDAR_URL = (
    "https://www.parlimen.gov.my/takwim-dewan-rakyat.html?uweb=dr&"
)
DETAIL_URL_TEMPLATE = (
    "https://www.parlimen.gov.my/"
    "takwim-dewan-rakyat.html?uweb=dr&id={meeting}&ssid={penggal}"
)
BASE_URL = "https://www.parlimen.gov.my/"
FETCH_TIMEOUT = 30

# Malay month names → month numbers
MALAY_MONTHS = {
    "januari": 1,
    "februari": 2,
    "mac": 3,
    "april": 4,
    "mei": 5,
    "jun": 6,
    "julai": 7,
    "ogos": 8,
    "september": 9,
    "oktober": 10,
    "november": 11,
    "disember": 12,
}

# Session name → number
SESSION_MAP = {
    "pertama": 1,
    "kedua": 2,
    "ketiga": 3,
}

# Term (penggal) ordinal → number
TERM_ORDINALS = {
    "pertama": 1,
    "kedua": 2,
    "ketiga": 3,
    "keempat": 4,
    "kelima": 5,
    "keenam": 6,
    "ketujuh": 7,
    "kelapan": 8,
    "kesembilan": 9,
    "kesepuluh": 10,
}

# Ordinal suffixes for short names
ORDINAL_SUFFIX = {1: "st", 2: "nd", 3: "rd"}

# Date pattern: DD MonthName YYYY
DATE_PATTERN = re.compile(
    r"(\d{1,2})\s+("
    + "|".join(MALAY_MONTHS.keys())
    + r")\s+(\d{4})",
    re.IGNORECASE,
)

# Date range pattern: DD Month YYYY - DD Month YYYY
DATE_RANGE_PATTERN = re.compile(
    r"(\d{1,2})\s+("
    + "|".join(MALAY_MONTHS.keys())
    + r")\s+(\d{4})\s*-\s*(\d{1,2})\s+("
    + "|".join(MALAY_MONTHS.keys())
    + r")\s+(\d{4})",
    re.IGNORECASE,
)


def _parse_malay_date(day: str, month_name: str, year: str) -> date:
    """Parse a Malay date string into a Python date."""
    return date(int(year), MALAY_MONTHS[month_name.lower()], int(day))


def _fetch_page(url: str) -> str | None:
    """Fetch a page from parlimen.gov.my with SSL verification disabled."""
    try:
        response = requests.get(url, timeout=FETCH_TIMEOUT, verify=False)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        logger.error("Failed to fetch %s: %s", url, e)
        return None


def parse_calendar_page(html: str) -> list[dict]:
    """Parse the main calendar HTML page.

    Returns a list of meeting dicts with keys:
        session, term, year, start_date, end_date, name, short_name, detail_url
    """
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True)

    # Extract year from "PARLIMEN ... 2026" heading
    year_match = re.search(r"PARLIMEN\b.*?(\d{4})", text, re.IGNORECASE)
    year = int(year_match.group(1)) if year_match else None

    # Extract term from "PENGGAL KELIMA" etc.
    term_match = re.search(
        r"PENGGAL\s+(" + "|".join(TERM_ORDINALS.keys()) + r")",
        text,
        re.IGNORECASE,
    )
    term = TERM_ORDINALS.get(term_match.group(1).lower()) if term_match else None

    if not year or not term:
        logger.warning("Could not parse year or term from calendar page")
        return []

    # Find all "Mesyuarat Pertama/Kedua/Ketiga" occurrences
    meetings = []

    # Find all detail links (Maklumat Lanjut)
    links = soup.find_all("a", href=re.compile(r"id=\d+.*ssid=\d+"))

    for link in links:
        href = link.get("href", "")
        detail_url = urljoin(BASE_URL, href)

        # Extract id and ssid from URL
        id_match = re.search(r"id=(\d+)", href)
        ssid_match = re.search(r"ssid=(\d+)", href)
        if not id_match:
            continue
        session = int(id_match.group(1))

        # Walk backwards/upwards from link to find meeting name
        meeting_name = _find_meeting_name(link, session)
        if not meeting_name:
            # Fallback: construct from session number
            session_names = {1: "Pertama", 2: "Kedua", 3: "Ketiga"}
            meeting_name = f"Mesyuarat {session_names.get(session, str(session))}"

        # Find the date range near this link
        date_range = _find_date_range_near(link)
        if not date_range:
            continue

        start_date, end_date = date_range

        # Build full name and short name
        ordinal = session
        suffix = ORDINAL_SUFFIX.get(ordinal, "th")
        short_name = f"{ordinal}{suffix} Meeting {year}"
        full_name = f"{meeting_name}, Penggal {term_match.group(1).title()} {year}"

        meetings.append({
            "session": session,
            "term": term,
            "year": year,
            "start_date": start_date,
            "end_date": end_date,
            "name": full_name,
            "short_name": short_name,
            "detail_url": detail_url,
        })

    return meetings


def _find_meeting_name(link_tag, session: int) -> str | None:
    """Find the meeting name (Mesyuarat ...) near a detail link."""
    # Search in parent and sibling elements
    parent = link_tag.parent
    while parent:
        text = parent.get_text(" ", strip=True)
        match = re.search(r"Mesyuarat\s+\w+", text, re.IGNORECASE)
        if match:
            return match.group(0)
        parent = parent.parent
        # Don't go too far up
        if parent and parent.name in ("body", "html"):
            break
    return None


def _find_date_range_near(link_tag) -> tuple[date, date] | None:
    """Find a date range (DD Month YYYY - DD Month YYYY) near a link tag."""
    # Search in the parent row/container
    parent = link_tag.parent
    while parent:
        text = parent.get_text(" ", strip=True)
        match = DATE_RANGE_PATTERN.search(text)
        if match:
            start = _parse_malay_date(match.group(1), match.group(2), match.group(3))
            end = _parse_malay_date(match.group(4), match.group(5), match.group(6))
            return start, end
        parent = parent.parent
        if parent and parent.name in ("body", "html"):
            break
    return None


def parse_meeting_detail(html: str) -> list[date]:
    """Parse a meeting detail page to extract sitting dates.

    Returns a sorted list of sitting dates.
    """
    dates = []
    for match in DATE_PATTERN.finditer(html):
        try:
            d = _parse_malay_date(match.group(1), match.group(2), match.group(3))
            if d not in dates:
                dates.append(d)
        except (ValueError, KeyError):
            continue

    return sorted(dates)


def sync_calendar() -> dict:
    """Fetch the calendar and create/update ParliamentaryMeeting records.

    Returns a dict with keys: created, updated.
    """
    from parliament.models import ParliamentaryMeeting

    html = _fetch_page(CALENDAR_URL)
    if not html:
        logger.error("Failed to fetch calendar page")
        return {"created": 0, "updated": 0}

    meetings = parse_calendar_page(html)
    if not meetings:
        logger.warning("No meetings found on calendar page")
        return {"created": 0, "updated": 0}

    created = 0
    updated = 0

    for m in meetings:
        _, was_created = ParliamentaryMeeting.objects.update_or_create(
            term=m["term"],
            session=m["session"],
            year=m["year"],
            defaults={
                "name": m["name"],
                "short_name": m["short_name"],
                "start_date": m["start_date"],
                "end_date": m["end_date"],
            },
        )
        if was_created:
            created += 1
            logger.info("Created: %s", m["short_name"])
        else:
            updated += 1
            logger.info("Updated: %s", m["short_name"])

    return {"created": created, "updated": updated}
