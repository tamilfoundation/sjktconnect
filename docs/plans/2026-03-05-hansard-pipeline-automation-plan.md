# Hansard Pipeline Automation — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Automate the full Hansard pipeline end-to-end: calendar sync, PDF discovery, mention extraction, school matching, AI analysis, sitting briefs, meeting reports.

**Architecture:** Single `run_hansard_pipeline` management command orchestrates 7 steps in sequence. Each step is a standalone function/service. Failures in one step don't block others. WAT workflow at `_workflows/hansard-pipeline.md` is the living SOP.

**Tech Stack:** Django 5.x, Gemini Flash (google.genai SDK), requests, pdfplumber, Python difflib, markdown

**Design doc:** `docs/plans/2026-03-05-hansard-pipeline-automation-design.md`

---

## Sprint Structure

This work spans 2 sprints:

- **Sprint 5.1**: Pipeline infrastructure — calendar scraper, unified pipeline command, auto brief generator, meeting report generator
- **Sprint 5.2**: Historical rebuild — improved speaker extraction, tighter prompts, one-time re-process of all 97 sittings

This plan covers **Sprint 5.1** only. Sprint 5.2 plan will be written after 5.1 is complete and we can evaluate the quality of the new pipeline on fresh data.

---

## Task 1: Calendar Scraper

**Files:**
- Create: `backend/hansard/pipeline/calendar_scraper.py`
- Test: `backend/hansard/tests/test_calendar_scraper.py`

**Step 1: Write the failing tests**

```python
"""Tests for parliamentary calendar scraper."""

from datetime import date
from unittest.mock import patch, MagicMock

from django.test import TestCase

from hansard.pipeline.calendar_scraper import (
    parse_calendar_page,
    parse_meeting_detail,
    sync_calendar,
)
from parliament.models import ParliamentaryMeeting


SAMPLE_CALENDAR_HTML = """
<html><body>
<td>PARLIMEN Kelima Belas 2026</td>
<td>TAKWIM BAGI PENGGAL KELIMA</td>
<td>Mesyuarat Pertama</td>
<td><a href="https://www.parlimen.gov.my/takwim-dewan-rakyat.html?uweb=dr&amp;id=1&amp;ssid=5">Maklumat Lanjut</a></td>
<td>19 Januari 2026 - 03 Mac 2026</td>
<td>20 Hari</td>
<td>Mesyuarat Kedua</td>
<td><a href="https://www.parlimen.gov.my/takwim-dewan-rakyat.html?uweb=dr&amp;id=2&amp;ssid=5">Maklumat Lanjut</a></td>
<td>22 Jun 2026 - 16 Julai 2026</td>
<td>16 Hari</td>
<td>Mesyuarat Ketiga</td>
<td><a href="https://www.parlimen.gov.my/takwim-dewan-rakyat.html?uweb=dr&amp;id=3&amp;ssid=5">Maklumat Lanjut</a></td>
<td>05 Oktober 2026 - 08 Disember 2026</td>
<td>40 Hari</td>
</body></html>
"""

SAMPLE_DETAIL_HTML = """
<html><body>
<td>Isnin, 19 Januari 2026</td>
<td>Selasa, 20 Januari 2026</td>
<td>Rabu, 21 Januari 2026</td>
<td>Khamis, 22 Januari 2026</td>
<td>Isnin, 26 Januari 2026</td>
</body></html>
"""


class ParseCalendarPageTests(TestCase):
    """Test parsing the main calendar page."""

    def test_extracts_three_meetings(self):
        meetings = parse_calendar_page(SAMPLE_CALENDAR_HTML)
        self.assertEqual(len(meetings), 3)

    def test_first_meeting_dates(self):
        meetings = parse_calendar_page(SAMPLE_CALENDAR_HTML)
        self.assertEqual(meetings[0]["start_date"], date(2026, 1, 19))
        self.assertEqual(meetings[0]["end_date"], date(2026, 3, 3))

    def test_meeting_names(self):
        meetings = parse_calendar_page(SAMPLE_CALENDAR_HTML)
        self.assertEqual(meetings[0]["session"], 1)
        self.assertEqual(meetings[1]["session"], 2)
        self.assertEqual(meetings[2]["session"], 3)

    def test_penggal_and_year(self):
        meetings = parse_calendar_page(SAMPLE_CALENDAR_HTML)
        self.assertEqual(meetings[0]["term"], 5)
        self.assertEqual(meetings[0]["year"], 2026)

    def test_detail_urls(self):
        meetings = parse_calendar_page(SAMPLE_CALENDAR_HTML)
        self.assertIn("id=1", meetings[0]["detail_url"])
        self.assertIn("ssid=5", meetings[0]["detail_url"])


class ParseMeetingDetailTests(TestCase):
    """Test parsing individual sitting dates from detail page."""

    def test_extracts_sitting_dates(self):
        dates = parse_meeting_detail(SAMPLE_DETAIL_HTML)
        self.assertEqual(len(dates), 5)
        self.assertEqual(dates[0], date(2026, 1, 19))
        self.assertEqual(dates[4], date(2026, 1, 26))


class SyncCalendarTests(TestCase):
    """Test calendar sync creates/updates ParliamentaryMeeting records."""

    @patch("hansard.pipeline.calendar_scraper._fetch_page")
    def test_creates_meetings(self, mock_fetch):
        mock_fetch.return_value = SAMPLE_CALENDAR_HTML
        result = sync_calendar()
        self.assertEqual(result["created"], 3)
        self.assertEqual(ParliamentaryMeeting.objects.count(), 3)

    @patch("hansard.pipeline.calendar_scraper._fetch_page")
    def test_idempotent(self, mock_fetch):
        mock_fetch.return_value = SAMPLE_CALENDAR_HTML
        sync_calendar()
        result = sync_calendar()
        self.assertEqual(result["created"], 0)
        self.assertEqual(result["updated"], 3)
        self.assertEqual(ParliamentaryMeeting.objects.count(), 3)

    @patch("hansard.pipeline.calendar_scraper._fetch_page")
    def test_meeting_fields(self, mock_fetch):
        mock_fetch.return_value = SAMPLE_CALENDAR_HTML
        sync_calendar()
        m = ParliamentaryMeeting.objects.get(session=1, term=5, year=2026)
        self.assertEqual(m.start_date, date(2026, 1, 19))
        self.assertEqual(m.end_date, date(2026, 3, 3))
        self.assertIn("Pertama", m.name)
```

**Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest hansard/tests/test_calendar_scraper.py -v`
Expected: FAIL — module does not exist

**Step 3: Write the implementation**

```python
"""Scrape the parliamentary calendar from parlimen.gov.my.

Fetches meeting date ranges and individual sitting dates.
Creates/updates ParliamentaryMeeting records.

URL patterns:
    Main: https://www.parlimen.gov.my/takwim-dewan-rakyat.html?uweb=dr&
    Detail: ...?uweb=dr&id={meeting}&ssid={penggal}
"""

import logging
import re
from datetime import date

import requests

from parliament.models import ParliamentaryMeeting

logger = logging.getLogger(__name__)

CALENDAR_URL = "https://www.parlimen.gov.my/takwim-dewan-rakyat.html?uweb=dr&"

# Malay month names → month numbers
MALAY_MONTHS = {
    "januari": 1, "februari": 2, "mac": 3, "april": 4,
    "mei": 5, "jun": 6, "julai": 7, "ogos": 8,
    "september": 9, "oktober": 10, "november": 11, "disember": 12,
}

# Mesyuarat ordinal → session number
SESSION_MAP = {"pertama": 1, "kedua": 2, "ketiga": 3}

# Penggal ordinal → term number
TERM_MAP = {
    "pertama": 1, "kedua": 2, "ketiga": 3, "keempat": 4,
    "kelima": 5, "keenam": 6, "ketujuh": 7, "kelapan": 8,
}

DATE_PATTERN = re.compile(
    r"(\d{1,2})\s+("
    + "|".join(MALAY_MONTHS.keys())
    + r")\s+(\d{4})",
    re.IGNORECASE,
)

DATE_RANGE_PATTERN = re.compile(
    r"(\d{1,2})\s+("
    + "|".join(MALAY_MONTHS.keys())
    + r")\s+(\d{4})\s*-\s*(\d{1,2})\s+("
    + "|".join(MALAY_MONTHS.keys())
    + r")\s+(\d{4})",
    re.IGNORECASE,
)


def _fetch_page(url: str) -> str:
    """Fetch a page from parlimen.gov.my (SSL verification disabled)."""
    resp = requests.get(url, timeout=30, verify=False)
    resp.raise_for_status()
    return resp.text


def _parse_malay_date(day: str, month_name: str, year: str) -> date:
    """Parse a Malay date string into a date object."""
    month = MALAY_MONTHS[month_name.lower()]
    return date(int(year), month, int(day))


def parse_calendar_page(html: str) -> list[dict]:
    """Parse the main calendar page to extract meeting info.

    Returns list of dicts with keys:
        session, term, year, start_date, end_date, name, short_name, detail_url
    """
    # Extract term (penggal) number
    term = 1
    term_match = re.search(r"PENGGAL\s+(\w+)", html, re.IGNORECASE)
    if term_match:
        term_word = term_match.group(1).lower()
        term = TERM_MAP.get(term_word, 1)

    # Extract year
    year = date.today().year
    year_match = re.search(r"(?:PARLIMEN|TAKWIM)[^<]*(\d{4})", html)
    if year_match:
        year = int(year_match.group(1))

    # Extract meetings with date ranges
    meetings = []
    meeting_pattern = re.compile(
        r"Mesyuarat\s+(Pertama|Kedua|Ketiga)"
        r".*?"
        + DATE_RANGE_PATTERN.pattern,
        re.IGNORECASE | re.DOTALL,
    )

    for m in meeting_pattern.finditer(html):
        session_word = m.group(1).lower()
        session = SESSION_MAP.get(session_word, 1)

        start = _parse_malay_date(m.group(2), m.group(3), m.group(4))
        end = _parse_malay_date(m.group(5), m.group(6), m.group(7))

        # Find detail URL
        detail_url = ""
        detail_match = re.search(
            rf'href="([^"]*id={session}[^"]*ssid={term}[^"]*)"',
            html,
        )
        if detail_match:
            detail_url = detail_match.group(1).replace("&amp;", "&")

        ordinal = {"pertama": "1st", "kedua": "2nd", "ketiga": "3rd"}
        short = f"{ordinal.get(session_word, session_word)} Meeting {year}"

        meetings.append({
            "session": session,
            "term": term,
            "year": year,
            "start_date": start,
            "end_date": end,
            "name": f"{'Mesyuarat ' + m.group(1).title()} Penggal {term_match.group(1).title() if term_match else term} {year}",
            "short_name": short,
            "detail_url": detail_url,
        })

    return meetings


def parse_meeting_detail(html: str) -> list[date]:
    """Parse a meeting detail page to extract individual sitting dates."""
    dates = []
    for m in DATE_PATTERN.finditer(html):
        try:
            d = _parse_malay_date(m.group(1), m.group(2), m.group(3))
            if d not in dates:
                dates.append(d)
        except ValueError:
            continue
    return sorted(dates)


def sync_calendar() -> dict:
    """Fetch the parliamentary calendar and sync ParliamentaryMeeting records.

    Returns dict with counts: created, updated, skipped.
    """
    logger.info("Syncing parliamentary calendar...")

    try:
        html = _fetch_page(CALENDAR_URL)
    except Exception as e:
        logger.error("Failed to fetch calendar: %s", e)
        return {"created": 0, "updated": 0, "error": str(e)}

    meetings = parse_calendar_page(html)
    if not meetings:
        logger.warning("No meetings found on calendar page")
        return {"created": 0, "updated": 0}

    created = 0
    updated = 0

    for m in meetings:
        _, is_new = ParliamentaryMeeting.objects.update_or_create(
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
        if is_new:
            created += 1
        else:
            updated += 1

    logger.info("Calendar sync: %d created, %d updated", created, updated)
    return {"created": created, "updated": updated}
```

**Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest hansard/tests/test_calendar_scraper.py -v`
Expected: All 8 tests PASS

**Step 5: Commit**

```bash
git add backend/hansard/pipeline/calendar_scraper.py backend/hansard/tests/test_calendar_scraper.py
git commit -m "feat: add parliamentary calendar scraper

Scrapes parlimen.gov.my for meeting date ranges and individual
sitting dates. Creates/updates ParliamentaryMeeting records.
Handles SSL verification (known invalid cert).

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 2: Auto Brief Generator Function

**Files:**
- Modify: `backend/parliament/services/brief_generator.py`
- Modify: `backend/parliament/tests/test_brief_generator.py`

**Step 1: Write the failing test**

```python
class GenerateAllPendingBriefsTests(TestCase):
    """Test auto-generating briefs for sittings without one."""

    def setUp(self):
        self.sitting1 = HansardSitting.objects.create(
            sitting_date="2026-01-20",
            pdf_url="https://example.com/1.pdf",
            pdf_filename="1.pdf",
            status="COMPLETED",
        )
        self.sitting2 = HansardSitting.objects.create(
            sitting_date="2026-01-21",
            pdf_url="https://example.com/2.pdf",
            pdf_filename="2.pdf",
            status="COMPLETED",
        )
        # sitting1 has analysed mentions, no brief
        HansardMention.objects.create(
            sitting=self.sitting1, verbatim_quote="Q1",
            mp_name="YB Test", ai_summary="Test summary.",
        )
        # sitting2 has analysed mentions AND a brief already
        HansardMention.objects.create(
            sitting=self.sitting2, verbatim_quote="Q2",
            mp_name="YB Test2", ai_summary="Test summary 2.",
        )
        SittingBrief.objects.create(
            sitting=self.sitting2,
            title="Existing brief",
            summary_html="<p>Existing</p>",
        )

    def test_generates_only_for_missing_briefs(self):
        result = generate_all_pending_briefs()
        self.assertEqual(result["generated"], 1)
        self.assertEqual(SittingBrief.objects.count(), 2)

    def test_skips_sittings_without_analysed_mentions(self):
        sitting3 = HansardSitting.objects.create(
            sitting_date="2026-01-22",
            pdf_url="https://example.com/3.pdf",
            pdf_filename="3.pdf",
            status="COMPLETED",
        )
        # Mention with no ai_summary
        HansardMention.objects.create(
            sitting=sitting3, verbatim_quote="Q3",
        )
        result = generate_all_pending_briefs()
        self.assertEqual(result["generated"], 1)  # only sitting1
```

**Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest parliament/tests/test_brief_generator.py::GenerateAllPendingBriefsTests -v`
Expected: FAIL — `generate_all_pending_briefs` not found

**Step 3: Write the implementation**

Add to `brief_generator.py`:

```python
def generate_all_pending_briefs() -> dict:
    """Generate briefs for all sittings that have analysed mentions but no brief.

    Returns dict with count: generated.
    """
    # Sittings with at least one analysed mention but no SittingBrief
    sittings = (
        HansardSitting.objects
        .filter(
            status=HansardSitting.Status.COMPLETED,
            mentions__ai_summary__gt="",
        )
        .exclude(brief__isnull=False)
        .distinct()
    )

    generated = 0
    for sitting in sittings:
        brief = generate_brief(sitting)
        if brief:
            generated += 1
            logger.info("Brief generated for %s", sitting.sitting_date)

    logger.info("Auto-brief: %d briefs generated", generated)
    return {"generated": generated}
```

**Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest parliament/tests/test_brief_generator.py -v`
Expected: All tests PASS (existing + new)

**Step 5: Commit**

```bash
git add backend/parliament/services/brief_generator.py backend/parliament/tests/test_brief_generator.py
git commit -m "feat: add generate_all_pending_briefs for auto brief generation

Finds sittings with analysed mentions but no SittingBrief,
generates briefs automatically. Used by the pipeline command.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 3: Meeting Report Generator

**Files:**
- Create: `backend/parliament/services/report_generator.py`
- Create: `backend/parliament/tests/test_report_generator.py`

**Step 1: Write the failing tests**

```python
"""Tests for meeting report generator."""

from datetime import date
from unittest.mock import patch, MagicMock

from django.test import TestCase

from hansard.models import HansardMention, HansardSitting
from parliament.models import ParliamentaryMeeting, SittingBrief
from parliament.services.report_generator import (
    generate_meeting_report,
    generate_all_pending_reports,
)


class GenerateMeetingReportTests(TestCase):
    """Test Gemini-powered meeting report generation."""

    def setUp(self):
        self.meeting = ParliamentaryMeeting.objects.create(
            name="Mesyuarat Pertama 2025",
            short_name="1st Meeting 2025",
            term=4, session=1, year=2025,
            start_date=date(2025, 2, 4),
            end_date=date(2025, 3, 27),
        )
        self.sitting = HansardSitting.objects.create(
            sitting_date=date(2025, 2, 4),
            pdf_url="https://example.com/1.pdf",
            pdf_filename="1.pdf",
            status="COMPLETED",
            meeting=self.meeting,
        )
        SittingBrief.objects.create(
            sitting=self.sitting,
            title="Brief for 4 Feb",
            summary_html="<p>Two MPs discussed Tamil school funding.</p>",
        )

    @patch("parliament.services.report_generator._call_gemini")
    def test_generates_report(self, mock_gemini):
        mock_gemini.return_value = {
            "report_html": "<h2>Key Findings</h2><p>Test report.</p>",
            "executive_summary": "Test executive summary.",
            "social_post_text": "1 Tamil school mention in 1st Meeting 2025.",
        }
        result = generate_meeting_report(self.meeting)
        self.assertTrue(result)
        self.meeting.refresh_from_db()
        self.assertIn("Key Findings", self.meeting.report_html)
        self.assertEqual(self.meeting.executive_summary, "Test executive summary.")

    @patch("parliament.services.report_generator._call_gemini")
    def test_skips_if_report_exists(self, mock_gemini):
        self.meeting.report_html = "<p>Existing report</p>"
        self.meeting.save()
        result = generate_meeting_report(self.meeting)
        self.assertFalse(result)
        mock_gemini.assert_not_called()

    def test_skips_if_no_briefs(self):
        SittingBrief.objects.all().delete()
        result = generate_meeting_report(self.meeting)
        self.assertFalse(result)


class GenerateAllPendingReportsTests(TestCase):
    """Test auto-detection of meetings needing reports."""

    def setUp(self):
        # Past meeting, no report
        self.past_meeting = ParliamentaryMeeting.objects.create(
            name="Past Meeting", short_name="Past",
            term=4, session=1, year=2025,
            start_date=date(2025, 2, 4),
            end_date=date(2025, 3, 27),
        )
        sitting = HansardSitting.objects.create(
            sitting_date=date(2025, 2, 4),
            pdf_url="https://example.com/1.pdf",
            pdf_filename="1.pdf",
            status="COMPLETED",
            meeting=self.past_meeting,
        )
        SittingBrief.objects.create(
            sitting=sitting, title="Brief",
            summary_html="<p>Content.</p>",
        )
        # Future meeting — should be skipped
        self.future_meeting = ParliamentaryMeeting.objects.create(
            name="Future Meeting", short_name="Future",
            term=5, session=2, year=2026,
            start_date=date(2026, 6, 22),
            end_date=date(2026, 7, 16),
        )

    @patch("parliament.services.report_generator._call_gemini")
    def test_generates_for_past_meetings_only(self, mock_gemini):
        mock_gemini.return_value = {
            "report_html": "<p>Report</p>",
            "executive_summary": "Summary.",
            "social_post_text": "Post.",
        }
        result = generate_all_pending_reports()
        self.assertEqual(result["generated"], 1)
        mock_gemini.assert_called_once()
```

**Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest parliament/tests/test_report_generator.py -v`
Expected: FAIL — module does not exist

**Step 3: Write the implementation**

```python
"""Meeting report generator.

Synthesises all sitting briefs from a meeting period into an
executive-grade report via Gemini Flash.

Triggered when a meeting's end_date has passed and report_html is empty.
"""

import json
import logging
import os
from datetime import date

from google import genai
from google.genai import types

from parliament.models import ParliamentaryMeeting, SittingBrief

logger = logging.getLogger(__name__)

REPORT_PROMPT = """\
You are writing an executive intelligence brief about Tamil schools (SJK(T)) \
in the Malaysian parliament for Tamil school stakeholders — parents, teachers, \
NGOs, and community leaders.

Below are the sitting-by-sitting summaries from {meeting_name} \
({start_date} to {end_date}, {sitting_count} sittings with Tamil school mentions).

Write a meeting report with these sections:
1. **Key Findings** — the 3-5 most important takeaways
2. **MP Activity** — which MPs raised Tamil school issues, how substantive
3. **Policy Signals** — any policy changes, commitments, or budget allocations
4. **What to Watch** — issues likely to resurface or need community attention

Rules:
- Be factual and analytical. Every sentence must add information or insight.
- Length must match substance. A quiet meeting: 200 words. A significant one: up to 1,000.
- Do not repeat what individual briefs say — synthesise and draw connections.
- Do not pad, ramble, or use filler phrases.
- Write in British English.
- Output valid HTML (use <h2>, <p>, <ul>, <li> tags). No markdown.

Also provide:
- executive_summary: 2-3 sentences for a preview card (plain text, no HTML)
- social_post_text: max 280 characters for social media

Return as JSON with keys: report_html, executive_summary, social_post_text

--- SITTING SUMMARIES ---
{briefs}
--- END SUMMARIES ---
"""


def _call_gemini(prompt: str) -> dict | None:
    """Call Gemini Flash and return parsed JSON response."""
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        logger.error("GEMINI_API_KEY not set")
        return None

    client = genai.Client(api_key=api_key)

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.2,
            ),
        )
        return json.loads(response.text.strip())
    except Exception:
        logger.exception("Gemini API call failed for meeting report")
        return None


def generate_meeting_report(meeting: ParliamentaryMeeting) -> bool:
    """Generate an AI report for a single meeting.

    Returns True if report was generated, False if skipped.
    """
    if meeting.report_html:
        logger.info("Meeting %s already has a report, skipping", meeting.short_name)
        return False

    # Get all briefs for sittings in this meeting
    briefs = (
        SittingBrief.objects
        .filter(sitting__meeting=meeting)
        .exclude(summary_html="")
        .select_related("sitting")
        .order_by("sitting__sitting_date")
    )

    if not briefs.exists():
        logger.info("No briefs for meeting %s, skipping report", meeting.short_name)
        return False

    # Build the briefs text
    briefs_text = []
    for brief in briefs:
        briefs_text.append(
            f"### {brief.sitting.sitting_date}\n{brief.title}\n{brief.summary_html}"
        )

    prompt = REPORT_PROMPT.format(
        meeting_name=meeting.name,
        start_date=meeting.start_date.strftime("%d %B %Y"),
        end_date=meeting.end_date.strftime("%d %B %Y"),
        sitting_count=briefs.count(),
        briefs="\n\n".join(briefs_text),
    )

    result = _call_gemini(prompt)
    if not result:
        return False

    meeting.report_html = result.get("report_html", "")
    meeting.executive_summary = result.get("executive_summary", "")
    meeting.social_post_text = result.get("social_post_text", "")[:280]
    meeting.save(update_fields=[
        "report_html", "executive_summary", "social_post_text", "updated_at",
    ])

    logger.info("Report generated for meeting %s", meeting.short_name)
    return True


def generate_all_pending_reports() -> dict:
    """Generate reports for all past meetings that don't have one yet.

    Returns dict with count: generated.
    """
    today = date.today()
    meetings = (
        ParliamentaryMeeting.objects
        .filter(end_date__lt=today, report_html="")
    )

    generated = 0
    for meeting in meetings:
        if generate_meeting_report(meeting):
            generated += 1

    logger.info("Auto-report: %d reports generated", generated)
    return {"generated": generated}
```

**Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest parliament/tests/test_report_generator.py -v`
Expected: All 5 tests PASS

**Step 5: Commit**

```bash
git add backend/parliament/services/report_generator.py backend/parliament/tests/test_report_generator.py
git commit -m "feat: add Gemini-powered meeting report generator

Synthesises sitting briefs into executive intelligence reports.
Triggered when meeting end_date passes and no report exists.
Structured: Key Findings, MP Activity, Policy Signals, What to Watch.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 4: Unified Pipeline Command

**Files:**
- Create: `backend/hansard/management/commands/run_hansard_pipeline.py`
- Create: `backend/hansard/tests/test_run_hansard_pipeline.py`

**Step 1: Write the failing tests**

```python
"""Tests for the unified hansard pipeline command."""

from io import StringIO
from unittest.mock import patch, MagicMock

from django.core.management import call_command
from django.test import TestCase


class RunHansardPipelineTests(TestCase):
    """Test the unified pipeline orchestrator."""

    @patch("hansard.management.commands.run_hansard_pipeline.generate_all_pending_reports")
    @patch("hansard.management.commands.run_hansard_pipeline.generate_all_pending_briefs")
    @patch("hansard.management.commands.run_hansard_pipeline.update_all_scorecards")
    @patch("hansard.management.commands.run_hansard_pipeline.run_analysis")
    @patch("hansard.management.commands.run_hansard_pipeline.run_matching")
    @patch("hansard.management.commands.run_hansard_pipeline.call_command")
    @patch("hansard.management.commands.run_hansard_pipeline.sync_calendar")
    def test_all_steps_called_in_order(
        self, mock_cal, mock_cmd, mock_match, mock_analyse,
        mock_score, mock_brief, mock_report,
    ):
        mock_cal.return_value = {"created": 0, "updated": 0}
        mock_match.return_value = {"matched": 0, "unmatched": 0, "total": 0}
        mock_analyse.return_value = {"success": 0, "failed": 0}
        mock_score.return_value = {"created": 0, "updated": 0, "deleted": 0}
        mock_brief.return_value = {"generated": 0}
        mock_report.return_value = {"generated": 0}

        out = StringIO()
        call_command("run_hansard_pipeline", stdout=out)
        output = out.getvalue()

        mock_cal.assert_called_once()
        mock_cmd.assert_called_once()  # check_new_hansards
        mock_match.assert_called_once()
        mock_analyse.assert_called_once()
        mock_score.assert_called_once()
        mock_brief.assert_called_once()
        mock_report.assert_called_once()

    @patch("hansard.management.commands.run_hansard_pipeline.sync_calendar")
    def test_step_failure_continues(self, mock_cal):
        """If one step fails, others should still run."""
        mock_cal.side_effect = Exception("Network error")

        out = StringIO()
        err = StringIO()
        # Should not raise
        call_command("run_hansard_pipeline", stdout=out, stderr=err)
        self.assertIn("Step 1", out.getvalue())

    def test_dry_run_does_nothing(self):
        out = StringIO()
        call_command("run_hansard_pipeline", "--dry-run", stdout=out)
        output = out.getvalue()
        self.assertIn("DRY RUN", output)
```

**Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest hansard/tests/test_run_hansard_pipeline.py -v`
Expected: FAIL — command does not exist

**Step 3: Write the implementation**

```python
"""Unified Hansard pipeline: calendar sync through meeting reports.

Usage:
    python manage.py run_hansard_pipeline              # Full pipeline
    python manage.py run_hansard_pipeline --dry-run     # Preview
    python manage.py run_hansard_pipeline --skip-calendar
    python manage.py run_hansard_pipeline --skip-analysis

Steps:
    1. sync_calendar — scrape parlimen.gov.my for meeting dates
    2. check_new_hansards — discover + process new PDFs
    3. match_mentions — link unmatched mentions to schools
    4. analyse_mentions — Gemini AI analysis
    5. update_scorecards — recalculate MP stats
    6. generate_briefs — create sitting summaries
    7. generate_meeting_report — executive synthesis for completed meetings
"""

import logging

from django.core.management import call_command
from django.core.management.base import BaseCommand

from hansard.models import HansardMention
from hansard.pipeline.calendar_scraper import sync_calendar
from hansard.pipeline.matcher import match_mentions
from parliament.services.brief_generator import generate_all_pending_briefs
from parliament.services.report_generator import generate_all_pending_reports
from parliament.services.scorecard import update_all_scorecards

logger = logging.getLogger(__name__)


def run_matching() -> dict:
    """Run school matching on all unmatched mentions."""
    unmatched = HansardMention.objects.filter(matched_schools__isnull=True)
    if not unmatched.exists():
        return {"matched": 0, "unmatched": 0, "total": 0}
    return match_mentions(unmatched)


def run_analysis() -> dict:
    """Run Gemini analysis on all un-analysed mentions.

    Imports analyse_mention inline to avoid requiring GEMINI_API_KEY at import time.
    """
    from django.db import connection
    from parliament.services.gemini_client import analyse_mention, apply_analysis
    import time

    mentions = list(
        HansardMention.objects.filter(ai_summary="")
        .select_related("sitting")
        .order_by("sitting__sitting_date", "page_number")
    )

    if not mentions:
        return {"success": 0, "failed": 0}

    success = 0
    failed = 0

    for mention in mentions:
        analysis = analyse_mention(mention)
        if analysis:
            apply_analysis(mention, analysis)
            connection.close()
            success += 1
        else:
            failed += 1
        time.sleep(0.5)

    return {"success": success, "failed": failed}


class Command(BaseCommand):
    help = "Run the full Hansard pipeline: calendar → discover → match → analyse → scorecards → briefs → reports."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Preview what each step would do.",
        )
        parser.add_argument(
            "--skip-calendar", action="store_true",
            help="Skip calendar sync step.",
        )
        parser.add_argument(
            "--skip-analysis", action="store_true",
            help="Skip Gemini AI analysis step.",
        )

    def handle(self, **options):
        dry_run = options["dry_run"]

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — no changes will be made"))
            self._dry_run(options)
            return

        steps = [
            ("Step 1: Sync calendar", self._step_calendar, options["skip_calendar"]),
            ("Step 2: Discover + process Hansards", self._step_discover, False),
            ("Step 3: Match mentions to schools", self._step_match, False),
            ("Step 4: Analyse mentions (Gemini)", self._step_analyse, options["skip_analysis"]),
            ("Step 5: Update scorecards", self._step_scorecards, False),
            ("Step 6: Generate sitting briefs", self._step_briefs, False),
            ("Step 7: Generate meeting reports", self._step_reports, False),
        ]

        for label, func, skip in steps:
            if skip:
                self.stdout.write(f"{label} — SKIPPED")
                continue
            self.stdout.write(f"\n{label}...")
            try:
                func()
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"  {label} FAILED: {e}"))
                logger.exception("%s failed", label)

        self.stdout.write(self.style.SUCCESS("\nPipeline complete."))

    def _step_calendar(self):
        result = sync_calendar()
        self.stdout.write(
            f"  Calendar: {result.get('created', 0)} created, "
            f"{result.get('updated', 0)} updated"
        )

    def _step_discover(self):
        call_command(
            "check_new_hansards", auto_process=True,
            stdout=self.stdout, stderr=self.stderr,
        )

    def _step_match(self):
        result = run_matching()
        self.stdout.write(
            f"  Matching: {result['matched']}/{result['total']} matched"
        )

    def _step_analyse(self):
        result = run_analysis()
        self.stdout.write(
            f"  Analysis: {result['success']} analysed, {result['failed']} failed"
        )

    def _step_scorecards(self):
        result = update_all_scorecards()
        self.stdout.write(
            f"  Scorecards: {result['created']} created, "
            f"{result['updated']} updated, {result['deleted']} deleted"
        )

    def _step_briefs(self):
        result = generate_all_pending_briefs()
        self.stdout.write(f"  Briefs: {result['generated']} generated")

    def _step_reports(self):
        result = generate_all_pending_reports()
        self.stdout.write(f"  Reports: {result['generated']} generated")

    def _dry_run(self, options):
        """Preview what each step would do."""
        self.stdout.write("Step 1: Sync calendar — would fetch parlimen.gov.my")

        from hansard.models import HansardSitting
        pending = HansardSitting.objects.filter(status="PENDING").count()
        self.stdout.write(f"Step 2: Discover — {pending} pending sittings")

        unmatched = HansardMention.objects.filter(matched_schools__isnull=True).count()
        self.stdout.write(f"Step 3: Match — {unmatched} unmatched mentions")

        unanalysed = HansardMention.objects.filter(ai_summary="").count()
        self.stdout.write(f"Step 4: Analyse — {unanalysed} un-analysed mentions")

        self.stdout.write("Step 5: Scorecards — would recalculate all")

        from parliament.models import SittingBrief
        no_brief = (
            HansardSitting.objects
            .filter(status="COMPLETED", mentions__ai_summary__gt="")
            .exclude(brief__isnull=False)
            .distinct().count()
        )
        self.stdout.write(f"Step 6: Briefs — {no_brief} sittings need briefs")

        from parliament.models import ParliamentaryMeeting
        from datetime import date
        no_report = ParliamentaryMeeting.objects.filter(
            end_date__lt=date.today(), report_html=""
        ).count()
        self.stdout.write(f"Step 7: Reports — {no_report} meetings need reports")
```

**Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest hansard/tests/test_run_hansard_pipeline.py -v`
Expected: All 3 tests PASS

**Step 5: Run full backend test suite**

Run: `cd backend && python -m pytest --tb=short -q`
Expected: All existing tests still pass + 16 new tests

**Step 6: Commit**

```bash
git add backend/hansard/management/commands/run_hansard_pipeline.py backend/hansard/tests/test_run_hansard_pipeline.py
git commit -m "feat: unified Hansard pipeline command

Orchestrates 7 steps: calendar sync, PDF discovery, school matching,
Gemini analysis, scorecards, sitting briefs, meeting reports.
Each step wrapped in try/except — failures don't block others.
Supports --dry-run, --skip-calendar, --skip-analysis.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 5: Update WAT Workflow + Cloud Run Configuration

**Files:**
- Already created: `_workflows/hansard-pipeline.md`
- Modify: `SJKTConnect/CLAUDE.md` — update Next Sprint section

**Step 1: Update CLAUDE.md Next Sprint section**

Replace the Next Sprint section to reflect that pipeline automation is in progress, and document the new command.

**Step 2: Document Cloud Run job update**

Add to CLAUDE.md Commands section:
```bash
# Full pipeline (replaces check_new_hansards --auto-process)
python manage.py run_hansard_pipeline              # Full pipeline
python manage.py run_hansard_pipeline --dry-run     # Preview
python manage.py run_hansard_pipeline --skip-calendar
python manage.py run_hansard_pipeline --skip-analysis
```

**Step 3: Note for deployment**

The Cloud Run job `sjktconnect-check-hansards` needs its command updated from `check_new_hansards --auto-process` to `run_hansard_pipeline`. This requires:
1. Backend deploy (to include new code)
2. `gcloud run jobs update sjktconnect-check-hansards --command "python,manage.py,run_hansard_pipeline" --region asia-southeast1`
3. Set `GEMINI_API_KEY` env var on the job if not already set

**Step 4: Commit**

```bash
git add _workflows/hansard-pipeline.md SJKTConnect/CLAUDE.md
git commit -m "docs: add WAT workflow for Hansard pipeline, update CLAUDE.md

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Summary

| Task | New Tests | What it delivers |
|------|-----------|-----------------|
| 1. Calendar Scraper | 8 | Auto-create ParliamentaryMeeting records from parlimen.gov.my |
| 2. Auto Brief Generator | 2 | Generate sitting briefs for all sittings without one |
| 3. Meeting Report Generator | 5 | Gemini-powered executive reports for completed meetings |
| 4. Unified Pipeline Command | 3 | Single command orchestrating all 7 steps |
| 5. Docs + Cloud Run | 0 | WAT workflow, CLAUDE.md, deployment notes |
| **Total** | **18** | |

Sprint 5.2 (next) will cover: improved speaker extraction, tighter Gemini prompts, historical rebuild command.
