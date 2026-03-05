"""Tests for meeting report generator service."""

import datetime
from unittest.mock import patch

from django.test import TestCase

from hansard.models import HansardSitting
from parliament.models import ParliamentaryMeeting, SittingBrief
from parliament.services.report_generator import (
    generate_all_pending_reports,
    generate_meeting_report,
)


FAKE_GEMINI_RESPONSE = {
    "report_html": "<h2>Key Findings</h2><p>Test report content.</p>",
    "executive_summary": "Two Tamil school issues were raised during this meeting.",
    "social_post_text": "Parliament discussed Tamil school funding and teacher shortages.",
}


class GenerateMeetingReportTests(TestCase):
    """Tests for generate_meeting_report."""

    def setUp(self):
        self.meeting = ParliamentaryMeeting.objects.create(
            name="Test Meeting for Report Gen",
            short_name="Test Meeting 9999",
            term=99,
            session=1,
            year=9999,
            start_date=datetime.date(2025, 3, 10),
            end_date=datetime.date(2025, 4, 10),
        )
        self.sitting = HansardSitting.objects.create(
            sitting_date=datetime.date(2025, 3, 15),
            meeting=self.meeting,
            pdf_url="https://example.com/test.pdf",
            pdf_filename="test.pdf",
        )
        SittingBrief.objects.create(
            sitting=self.sitting,
            title="Brief for 15 Mar 2025",
            summary_html="<p>MP raised Tamil school funding.</p>",
        )

    @patch("parliament.services.report_generator._call_gemini")
    def test_generates_report(self, mock_gemini):
        """Gemini returns valid dict — meeting fields are populated."""
        mock_gemini.return_value = FAKE_GEMINI_RESPONSE

        result = generate_meeting_report(self.meeting)

        self.assertTrue(result)
        self.meeting.refresh_from_db()
        self.assertEqual(self.meeting.report_html, FAKE_GEMINI_RESPONSE["report_html"])
        self.assertEqual(
            self.meeting.executive_summary, FAKE_GEMINI_RESPONSE["executive_summary"]
        )
        self.assertEqual(
            self.meeting.social_post_text, FAKE_GEMINI_RESPONSE["social_post_text"]
        )
        mock_gemini.assert_called_once()

    @patch("parliament.services.report_generator._call_gemini")
    def test_skips_if_report_exists(self, mock_gemini):
        """Meeting already has report_html — returns False, Gemini not called."""
        self.meeting.report_html = "<p>Existing report.</p>"
        self.meeting.save(update_fields=["report_html"])

        result = generate_meeting_report(self.meeting)

        self.assertFalse(result)
        mock_gemini.assert_not_called()

    @patch("parliament.services.report_generator._call_gemini")
    def test_skips_if_no_briefs(self, mock_gemini):
        """Meeting has no briefs — returns False."""
        # Delete the brief created in setUp
        SittingBrief.objects.all().delete()

        result = generate_meeting_report(self.meeting)

        self.assertFalse(result)
        mock_gemini.assert_not_called()

    @patch("parliament.services.report_generator._call_gemini")
    def test_generates_for_past_meetings_only(self, mock_gemini):
        """Past meeting gets report, future meeting is skipped."""
        mock_gemini.return_value = FAKE_GEMINI_RESPONSE

        # Create a future meeting with a brief
        future_meeting = ParliamentaryMeeting.objects.create(
            name="Future Meeting",
            short_name="Future 2099",
            term=99,
            session=2,
            year=9999,
            start_date=datetime.date(2099, 1, 1),
            end_date=datetime.date(2099, 12, 31),
        )
        future_sitting = HansardSitting.objects.create(
            sitting_date=datetime.date(2099, 6, 1),
            meeting=future_meeting,
            pdf_url="https://example.com/future.pdf",
            pdf_filename="future.pdf",
        )
        SittingBrief.objects.create(
            sitting=future_sitting,
            title="Brief for future",
            summary_html="<p>Future brief.</p>",
        )

        stats = generate_all_pending_reports()

        # Past meeting (2025) should be generated, future (2099) skipped
        self.assertEqual(stats["generated"], 1)
        self.meeting.refresh_from_db()
        self.assertTrue(self.meeting.report_html)
        future_meeting.refresh_from_db()
        self.assertFalse(future_meeting.report_html)

    @patch("parliament.services.report_generator._call_gemini")
    def test_returns_false_on_gemini_failure(self, mock_gemini):
        """_call_gemini returns None — returns False, meeting unchanged."""
        mock_gemini.return_value = None

        result = generate_meeting_report(self.meeting)

        self.assertFalse(result)
        self.meeting.refresh_from_db()
        self.assertEqual(self.meeting.report_html, "")
        self.assertEqual(self.meeting.executive_summary, "")
        self.assertEqual(self.meeting.social_post_text, "")
