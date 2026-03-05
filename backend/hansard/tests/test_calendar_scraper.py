"""Tests for the parliamentary calendar scraper."""

from datetime import date
from unittest.mock import patch

from django.test import TestCase

from hansard.pipeline.calendar_scraper import (
    parse_calendar_page,
    parse_meeting_detail,
    sync_calendar,
)
from parliament.models import ParliamentaryMeeting


# ---------------------------------------------------------------------------
# Sample HTML fixtures
# ---------------------------------------------------------------------------

SAMPLE_CALENDAR_HTML = """
<html>
<body>
<div class="container">
  <h2>PARLIMEN Kelima Belas 2026</h2>
  <h3>TAKWIM BAGI PENGGAL KELIMA</h3>

  <table class="table">
    <tr>
      <td>Mesyuarat Pertama</td>
      <td><a href="takwim-dewan-rakyat.html?uweb=dr&amp;id=1&amp;ssid=5">Maklumat Lanjut</a></td>
      <td>19 Januari 2026 - 03 Mac 2026</td>
      <td>20 Hari</td>
    </tr>
    <tr>
      <td>Mesyuarat Kedua</td>
      <td><a href="takwim-dewan-rakyat.html?uweb=dr&amp;id=2&amp;ssid=5">Maklumat Lanjut</a></td>
      <td>22 Jun 2026 - 16 Julai 2026</td>
      <td>16 Hari</td>
    </tr>
    <tr>
      <td>Mesyuarat Ketiga</td>
      <td><a href="takwim-dewan-rakyat.html?uweb=dr&amp;id=3&amp;ssid=5">Maklumat Lanjut</a></td>
      <td>05 Oktober 2026 - 08 Disember 2026</td>
      <td>40 Hari</td>
    </tr>
  </table>
</div>
</body>
</html>
"""

# Alternative layout: text-based (not table), matching real parlimen.gov.my
SAMPLE_CALENDAR_HTML_TEXT = """
<html>
<body>
<div class="container">
  <h2>PARLIMEN Kelima Belas 2026</h2>
  <h3>TAKWIM BAGI PENGGAL KELIMA</h3>

  <div class="panel">
    <p><strong>Mesyuarat Pertama</strong></p>
    <p><a href="takwim-dewan-rakyat.html?uweb=dr&amp;id=1&amp;ssid=5">Maklumat Lanjut</a></p>
    <p>19 Januari 2026 - 03 Mac 2026</p>
    <p>20 Hari</p>
  </div>

  <div class="panel">
    <p><strong>Mesyuarat Kedua</strong></p>
    <p><a href="takwim-dewan-rakyat.html?uweb=dr&amp;id=2&amp;ssid=5">Maklumat Lanjut</a></p>
    <p>22 Jun 2026 - 16 Julai 2026</p>
    <p>16 Hari</p>
  </div>

  <div class="panel">
    <p><strong>Mesyuarat Ketiga</strong></p>
    <p><a href="takwim-dewan-rakyat.html?uweb=dr&amp;id=3&amp;ssid=5">Maklumat Lanjut</a></p>
    <p>05 Oktober 2026 - 08 Disember 2026</p>
    <p>40 Hari</p>
  </div>
</div>
</body>
</html>
"""

SAMPLE_DETAIL_HTML = """
<html>
<body>
<div class="container">
  <h2>Mesyuarat Pertama, Penggal Kelima</h2>
  <table class="table">
    <tr><td>1</td><td>Isnin, 19 Januari 2026</td></tr>
    <tr><td>2</td><td>Selasa, 20 Januari 2026</td></tr>
    <tr><td>3</td><td>Rabu, 21 Januari 2026</td></tr>
    <tr><td>4</td><td>Khamis, 22 Januari 2026</td></tr>
    <tr><td>5</td><td>Isnin, 26 Januari 2026</td></tr>
  </table>
</div>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# parse_calendar_page tests
# ---------------------------------------------------------------------------


class ParseCalendarPageTests(TestCase):
    """Test parsing of the main calendar page HTML."""

    def test_extracts_three_meetings(self):
        meetings = parse_calendar_page(SAMPLE_CALENDAR_HTML)
        self.assertEqual(len(meetings), 3)

    def test_session_numbers(self):
        meetings = parse_calendar_page(SAMPLE_CALENDAR_HTML)
        self.assertEqual(meetings[0]["session"], 1)
        self.assertEqual(meetings[1]["session"], 2)
        self.assertEqual(meetings[2]["session"], 3)

    def test_term_parsed(self):
        meetings = parse_calendar_page(SAMPLE_CALENDAR_HTML)
        for m in meetings:
            self.assertEqual(m["term"], 5)

    def test_year_parsed(self):
        meetings = parse_calendar_page(SAMPLE_CALENDAR_HTML)
        for m in meetings:
            self.assertEqual(m["year"], 2026)

    def test_start_dates(self):
        meetings = parse_calendar_page(SAMPLE_CALENDAR_HTML)
        self.assertEqual(meetings[0]["start_date"], date(2026, 1, 19))
        self.assertEqual(meetings[1]["start_date"], date(2026, 6, 22))
        self.assertEqual(meetings[2]["start_date"], date(2026, 10, 5))

    def test_end_dates(self):
        meetings = parse_calendar_page(SAMPLE_CALENDAR_HTML)
        self.assertEqual(meetings[0]["end_date"], date(2026, 3, 3))
        self.assertEqual(meetings[1]["end_date"], date(2026, 7, 16))
        self.assertEqual(meetings[2]["end_date"], date(2026, 12, 8))

    def test_detail_urls(self):
        meetings = parse_calendar_page(SAMPLE_CALENDAR_HTML)
        self.assertIn("id=1", meetings[0]["detail_url"])
        self.assertIn("ssid=5", meetings[0]["detail_url"])
        self.assertIn("id=2", meetings[1]["detail_url"])
        self.assertIn("id=3", meetings[2]["detail_url"])

    def test_meeting_names(self):
        meetings = parse_calendar_page(SAMPLE_CALENDAR_HTML)
        self.assertIn("Pertama", meetings[0]["name"])
        self.assertIn("Kedua", meetings[1]["name"])
        self.assertIn("Ketiga", meetings[2]["name"])

    def test_short_names(self):
        meetings = parse_calendar_page(SAMPLE_CALENDAR_HTML)
        self.assertEqual(meetings[0]["short_name"], "1st Meeting 2026")
        self.assertEqual(meetings[1]["short_name"], "2nd Meeting 2026")
        self.assertEqual(meetings[2]["short_name"], "3rd Meeting 2026")

    def test_text_layout(self):
        """Parser also works with non-table layout."""
        meetings = parse_calendar_page(SAMPLE_CALENDAR_HTML_TEXT)
        self.assertEqual(len(meetings), 3)
        self.assertEqual(meetings[0]["session"], 1)
        self.assertEqual(meetings[0]["start_date"], date(2026, 1, 19))

    def test_empty_html(self):
        meetings = parse_calendar_page("<html><body></body></html>")
        self.assertEqual(meetings, [])


# ---------------------------------------------------------------------------
# parse_meeting_detail tests
# ---------------------------------------------------------------------------


class ParseMeetingDetailTests(TestCase):
    """Test parsing of the meeting detail page HTML."""

    def test_extracts_sitting_dates(self):
        dates = parse_meeting_detail(SAMPLE_DETAIL_HTML)
        self.assertEqual(len(dates), 5)

    def test_dates_sorted(self):
        dates = parse_meeting_detail(SAMPLE_DETAIL_HTML)
        self.assertEqual(dates, sorted(dates))

    def test_correct_dates(self):
        dates = parse_meeting_detail(SAMPLE_DETAIL_HTML)
        self.assertEqual(dates[0], date(2026, 1, 19))
        self.assertEqual(dates[-1], date(2026, 1, 26))

    def test_empty_html(self):
        dates = parse_meeting_detail("<html><body></body></html>")
        self.assertEqual(dates, [])


# ---------------------------------------------------------------------------
# sync_calendar tests
# ---------------------------------------------------------------------------


class SyncCalendarTests(TestCase):
    """Test calendar sync with mocked HTTP fetching."""

    def setUp(self):
        # Clear seed data from migrations so tests start clean
        ParliamentaryMeeting.objects.all().delete()

    @patch("hansard.pipeline.calendar_scraper._fetch_page")
    def test_creates_meetings(self, mock_fetch):
        """sync_calendar creates ParliamentaryMeeting records."""
        mock_fetch.return_value = SAMPLE_CALENDAR_HTML

        result = sync_calendar()

        self.assertEqual(result["created"], 3)
        self.assertEqual(result["updated"], 0)
        self.assertEqual(ParliamentaryMeeting.objects.count(), 3)

    @patch("hansard.pipeline.calendar_scraper._fetch_page")
    def test_idempotent(self, mock_fetch):
        """Running sync_calendar twice doesn't duplicate records."""
        mock_fetch.return_value = SAMPLE_CALENDAR_HTML

        sync_calendar()
        result = sync_calendar()

        self.assertEqual(result["created"], 0)
        self.assertEqual(result["updated"], 3)
        self.assertEqual(ParliamentaryMeeting.objects.count(), 3)

    @patch("hansard.pipeline.calendar_scraper._fetch_page")
    def test_meeting_fields(self, mock_fetch):
        """Created meetings have correct field values."""
        mock_fetch.return_value = SAMPLE_CALENDAR_HTML

        sync_calendar()

        m1 = ParliamentaryMeeting.objects.get(term=5, session=1, year=2026)
        self.assertEqual(m1.start_date, date(2026, 1, 19))
        self.assertEqual(m1.end_date, date(2026, 3, 3))
        self.assertIn("Pertama", m1.name)
        self.assertEqual(m1.short_name, "1st Meeting 2026")

    @patch("hansard.pipeline.calendar_scraper._fetch_page")
    def test_updates_changed_dates(self, mock_fetch):
        """sync_calendar updates existing records when dates change."""
        mock_fetch.return_value = SAMPLE_CALENDAR_HTML
        sync_calendar()

        # Change end_date manually
        m = ParliamentaryMeeting.objects.get(term=5, session=1, year=2026)
        m.end_date = date(2026, 4, 1)
        m.save()

        # Re-sync should update it back
        result = sync_calendar()
        m.refresh_from_db()
        self.assertEqual(m.end_date, date(2026, 3, 3))
        self.assertEqual(result["updated"], 3)

    @patch("hansard.pipeline.calendar_scraper._fetch_page")
    def test_fetch_failure_returns_zeros(self, mock_fetch):
        """sync_calendar handles fetch failure gracefully."""
        mock_fetch.return_value = None

        result = sync_calendar()

        self.assertEqual(result["created"], 0)
        self.assertEqual(result["updated"], 0)
