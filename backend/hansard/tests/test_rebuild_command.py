"""Tests for rebuild_all_hansards management command."""

from io import StringIO
from unittest.mock import patch, MagicMock

from django.core.management import call_command
from django.test import TestCase

from hansard.models import HansardSitting, HansardMention


class RebuildCommandTests(TestCase):

    def setUp(self):
        self.sitting = HansardSitting.objects.create(
            sitting_date="2026-01-26",
            pdf_url="https://www.parlimen.gov.my/files/hindex/pdf/DR-26012026.pdf",
            pdf_filename="DR-26012026.pdf",
            status=HansardSitting.Status.COMPLETED,
            mention_count=3,
            total_pages=50,
        )
        HansardMention.objects.create(
            sitting=self.sitting,
            verbatim_quote="Old mention",
            page_number=1,
        )

    def test_dry_run_does_not_modify(self):
        """--dry-run should print plan without changing data."""
        out = StringIO()
        call_command("rebuild_all_hansards", "--dry-run", stdout=out)
        output = out.getvalue()
        self.assertIn("DRY RUN", output)
        self.assertIn("1 sitting(s)", output)
        self.sitting.refresh_from_db()
        self.assertEqual(self.sitting.status, HansardSitting.Status.COMPLETED)

    def test_dry_run_shows_multiple_sittings(self):
        HansardSitting.objects.create(
            sitting_date="2026-01-27",
            pdf_url="https://example.com/test2.pdf",
            pdf_filename="test2.pdf",
            status=HansardSitting.Status.COMPLETED,
        )
        out = StringIO()
        call_command("rebuild_all_hansards", "--dry-run", stdout=out)
        output = out.getvalue()
        self.assertIn("2 sitting(s)", output)

    @patch("hansard.management.commands.rebuild_all_hansards.connection")
    @patch("hansard.management.commands.rebuild_all_hansards.process_single_sitting")
    def test_rebuild_calls_process_and_deletes_old_mentions(self, mock_process, mock_conn):
        mock_process.return_value = {"mentions": 5, "matched": 2, "pages": 50, "status": "ok"}
        out = StringIO()
        call_command("rebuild_all_hansards", "--skip-analysis", stdout=out)
        mock_process.assert_called_once()

    def test_failed_sittings_skipped_by_default(self):
        self.sitting.status = HansardSitting.Status.FAILED
        self.sitting.save()
        out = StringIO()
        call_command("rebuild_all_hansards", "--dry-run", stdout=out)
        output = out.getvalue()
        self.assertIn("0 sitting(s)", output)

    def test_include_failed_flag(self):
        self.sitting.status = HansardSitting.Status.FAILED
        self.sitting.save()
        out = StringIO()
        call_command("rebuild_all_hansards", "--dry-run", "--include-failed", stdout=out)
        output = out.getvalue()
        self.assertIn("1 sitting(s)", output)
