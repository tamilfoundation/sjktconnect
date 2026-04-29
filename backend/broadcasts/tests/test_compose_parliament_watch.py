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

    def test_errors_if_neither_meeting_id_nor_auto(self):
        err = StringIO()
        call_command("compose_parliament_watch", stderr=err)
        self.assertIn("either --meeting-id", err.getvalue())
        self.assertEqual(Broadcast.objects.count(), 0)

    def test_errors_if_both_meeting_id_and_auto(self):
        err = StringIO()
        call_command(
            "compose_parliament_watch",
            "--meeting-id", str(self.meeting.pk),
            "--auto",
            stderr=err,
        )
        self.assertIn("mutually exclusive", err.getvalue())
        self.assertEqual(Broadcast.objects.count(), 0)

    @patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"})
    @patch("broadcasts.services.parliament_digest.genai")
    def test_auto_composes_for_each_unsent_published_meeting(self, mock_genai):
        # Bump the seed meeting forward so it falls into the auto window.
        # The setUp meeting ends 2026-03-20 which is before the
        # AUTO_COMPOSE_START_DATE cutoff and would otherwise be skipped.
        self.meeting.end_date = "2026-05-15"
        self.meeting.save(update_fields=["end_date"])
        # Add a second published meeting
        meeting2 = ParliamentaryMeeting.objects.create(
            name="Second Meeting of the Fourth Term 2026",
            short_name="2nd Meeting 2026",
            term=4, session=2, year=2026,
            start_date="2026-05-12", end_date="2026-06-05",
            report_html="<h2>R2</h2><p>x</p>",
            executive_summary="S2.", is_published=True,
        )
        # Add an unpublished meeting — must NOT be picked up
        ParliamentaryMeeting.objects.create(
            name="Future Meeting", short_name="Future",
            term=4, session=3, year=2026,
            start_date="2026-09-01", end_date="2026-09-30",
            report_html="<h2>R3</h2>",
            executive_summary="S3.", is_published=False,
        )
        # And a published one with empty report_html — also skipped
        ParliamentaryMeeting.objects.create(
            name="Empty Meeting", short_name="Empty",
            term=4, session=4, year=2026,
            start_date="2026-10-01", end_date="2026-10-30",
            report_html="", executive_summary="",
            is_published=True,
        )
        mock_response = Mock()
        mock_response.text = (
            '{"headlines": "Test.", "developments": [], '
            '"scorecard_summary": "Test.", "one_thing": "Test."}'
        )
        mock_genai.Client.return_value.models.generate_content.return_value = (
            mock_response
        )

        call_command("compose_parliament_watch", "--auto", stdout=StringIO())

        broadcasts = Broadcast.objects.filter(
            kind=Broadcast.Kind.PARLIAMENT_WATCH
        ).order_by("coverage_start_date")
        self.assertEqual(broadcasts.count(), 2)
        # Coverage dates copied from meeting
        self.assertEqual(str(broadcasts[0].coverage_start_date), "2026-02-24")
        self.assertEqual(str(broadcasts[1].coverage_start_date), "2026-05-12")
        self.assertEqual(broadcasts[0].subject, "Parliament Watch \u2014 1st Meeting 2026")
        self.assertEqual(broadcasts[1].subject, "Parliament Watch \u2014 2nd Meeting 2026")

    @patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"})
    @patch("broadcasts.services.parliament_digest.genai")
    def test_auto_skips_meetings_ending_before_cutoff(self, mock_genai):
        """The seed meeting in setUp ends 2026-03-20, which is before the
        AUTO_COMPOSE_START_DATE cutoff (2026-04-30). --auto must skip it
        so the launch run doesn't backfill 11 historical meetings."""
        mock_response = Mock()
        mock_response.text = (
            '{"headlines": "x", "developments": [], '
            '"scorecard_summary": "x", "one_thing": "x"}'
        )
        mock_genai.Client.return_value.models.generate_content.return_value = (
            mock_response
        )

        out = StringIO()
        call_command("compose_parliament_watch", "--auto", stdout=out)

        self.assertEqual(Broadcast.objects.count(), 0)
        self.assertIn("nothing to do", out.getvalue())

    @patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"})
    @patch("broadcasts.services.parliament_digest.genai")
    def test_auto_is_idempotent(self, mock_genai):
        """Re-running --auto for a meeting that already has a draft must skip it."""
        # Move the seed meeting into the auto window first.
        self.meeting.end_date = "2026-05-15"
        self.meeting.save(update_fields=["end_date"])
        mock_response = Mock()
        mock_response.text = (
            '{"headlines": "Test.", "developments": [], '
            '"scorecard_summary": "Test.", "one_thing": "Test."}'
        )
        mock_genai.Client.return_value.models.generate_content.return_value = (
            mock_response
        )

        call_command("compose_parliament_watch", "--auto", stdout=StringIO())
        self.assertEqual(Broadcast.objects.count(), 1)

        # Second run — should NOT create another broadcast
        out = StringIO()
        call_command("compose_parliament_watch", "--auto", stdout=out)
        self.assertEqual(Broadcast.objects.count(), 1)
        self.assertIn("nothing to do", out.getvalue())

    @patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"})
    @patch("broadcasts.services.parliament_digest.genai")
    def test_meeting_id_path_also_sets_coverage_dates(self, mock_genai):
        """The single-meeting path must also set coverage dates so --auto
        idempotency works after a manual compose run."""
        mock_response = Mock()
        mock_response.text = (
            '{"headlines": "Test.", "developments": [], '
            '"scorecard_summary": "Test.", "one_thing": "Test."}'
        )
        mock_genai.Client.return_value.models.generate_content.return_value = (
            mock_response
        )

        call_command(
            "compose_parliament_watch",
            "--meeting-id", str(self.meeting.pk),
            stdout=StringIO(),
        )
        b = Broadcast.objects.get()
        self.assertEqual(str(b.coverage_start_date), "2026-02-24")
        self.assertEqual(str(b.coverage_end_date), "2026-03-20")
