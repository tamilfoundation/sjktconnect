"""Tests for the compose_parliament_watch management command."""

from unittest.mock import patch, Mock
from io import StringIO

from django.test import TestCase, override_settings
from django.core.management import call_command

from parliament.models import ParliamentaryMeeting
from broadcasts.models import Broadcast


class ComposeParliamentWatchTest(TestCase):
    def setUp(self):
        self.meeting = ParliamentaryMeeting.objects.create(
            name="First Meeting of the Fourth Term 2026",
            short_name="1st Meeting 2026",
            term=4,
            session=1,
            year=2026,
            start_date="2026-02-24",
            end_date="2026-03-20",
            report_html="<h2>Report</h2><p>Content</p>",
            executive_summary="Summary.",
            is_published=True,
        )

    @patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"})
    @patch("broadcasts.services.parliament_digest.genai")
    def test_creates_draft_broadcast(self, mock_genai):
        mock_response = Mock()
        mock_response.text = (
            '{"headlines": "Parliament addressed funding.", '
            '"developments": [{"topic": "Funding", "summary": "YB X raised RM2M.", '
            '"actions": {"school_boards": "Write to PPD.", "parents": "Ask school.", '
            '"ngos": "Submit memo.", "community": "Share."}}], '
            '"scorecard_summary": "3 MPs spoke.", '
            '"one_thing": "Contact your MP."}'
        )
        mock_genai.Client.return_value.models.generate_content.return_value = (
            mock_response
        )

        out = StringIO()
        call_command(
            "compose_parliament_watch",
            "--meeting-id",
            str(self.meeting.pk),
            stdout=out,
        )

        broadcast = Broadcast.objects.first()
        self.assertIsNotNone(broadcast)
        self.assertEqual(broadcast.status, Broadcast.Status.DRAFT)
        self.assertIn("Parliament Watch", broadcast.subject)
        self.assertEqual(
            broadcast.audience_filter, {"category": "PARLIAMENT_WATCH"}
        )
        self.assertIn("Funding", broadcast.html_content)

    @patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"})
    @patch("broadcasts.services.parliament_digest.genai")
    def test_dry_run_does_not_create_broadcast(self, mock_genai):
        mock_response = Mock()
        mock_response.text = (
            '{"headlines": "Test.", "developments": [], '
            '"scorecard_summary": "Test.", "one_thing": "Test."}'
        )
        mock_genai.Client.return_value.models.generate_content.return_value = (
            mock_response
        )

        out = StringIO()
        call_command(
            "compose_parliament_watch",
            "--meeting-id",
            str(self.meeting.pk),
            "--dry-run",
            stdout=out,
        )
        self.assertEqual(Broadcast.objects.count(), 0)
        self.assertIn("DRY RUN", out.getvalue())

    def test_fails_if_meeting_not_found(self):
        err = StringIO()
        call_command(
            "compose_parliament_watch",
            "--meeting-id",
            "9999",
            stderr=err,
        )
        self.assertEqual(Broadcast.objects.count(), 0)
