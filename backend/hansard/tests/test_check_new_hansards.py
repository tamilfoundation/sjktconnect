"""Tests for the check_new_hansards management command."""

from datetime import date
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase

from hansard.models import HansardSitting


class CheckNewHansardsTests(TestCase):
    """Test the check_new_hansards discovery command."""

    def _call(self, *args, **kwargs):
        out = StringIO()
        err = StringIO()
        call_command("check_new_hansards", *args, stdout=out, stderr=err, **kwargs)
        return out.getvalue(), err.getvalue()

    @patch("hansard.management.commands.check_new_hansards.discover_new_pdfs")
    def test_no_new_hansards(self, mock_discover):
        mock_discover.return_value = []
        out, _ = self._call("--days=7")
        self.assertIn("No new Hansards", out)

    @patch("hansard.management.commands.check_new_hansards.discover_new_pdfs")
    def test_discovers_new_pdfs(self, mock_discover):
        mock_discover.return_value = [
            {
                "sitting_date": date(2026, 2, 10),
                "pdf_url": "https://example.com/DR-10022026.pdf",
                "pdf_filename": "DR-10022026.pdf",
            },
            {
                "sitting_date": date(2026, 2, 11),
                "pdf_url": "https://example.com/DR-11022026.pdf",
                "pdf_filename": "DR-11022026.pdf",
            },
        ]
        out, _ = self._call("--days=7")
        self.assertIn("2 new Hansard(s) found", out)
        self.assertIn("2026-02-10", out)
        self.assertIn("2026-02-11", out)

    @patch("hansard.management.commands.check_new_hansards.discover_new_pdfs")
    def test_skips_already_processed(self, mock_discover):
        # Create an already-processed sitting
        HansardSitting.objects.create(
            sitting_date="2026-02-10",
            pdf_url="https://example.com/DR-10022026.pdf",
            pdf_filename="DR-10022026.pdf",
            status=HansardSitting.Status.COMPLETED,
        )

        mock_discover.return_value = [
            {
                "sitting_date": date(2026, 2, 10),
                "pdf_url": "https://example.com/DR-10022026.pdf",
                "pdf_filename": "DR-10022026.pdf",
            },
            {
                "sitting_date": date(2026, 2, 11),
                "pdf_url": "https://example.com/DR-11022026.pdf",
                "pdf_filename": "DR-11022026.pdf",
            },
        ]
        out, _ = self._call("--days=7")
        self.assertIn("1 new Hansard(s) found", out)
        self.assertIn("2026-02-11", out)
        self.assertNotIn("2026-02-10 —", out)

    @patch("hansard.management.commands.check_new_hansards.discover_new_pdfs")
    def test_failed_sitting_not_skipped(self, mock_discover):
        """A FAILED sitting should be retried — not counted as processed."""
        HansardSitting.objects.create(
            sitting_date="2026-02-10",
            pdf_url="https://example.com/DR-10022026.pdf",
            pdf_filename="DR-10022026.pdf",
            status=HansardSitting.Status.FAILED,
        )

        mock_discover.return_value = [
            {
                "sitting_date": date(2026, 2, 10),
                "pdf_url": "https://example.com/DR-10022026.pdf",
                "pdf_filename": "DR-10022026.pdf",
            },
        ]
        out, _ = self._call("--days=7")
        self.assertIn("1 new Hansard(s) found", out)

    @patch("hansard.management.commands.check_new_hansards.discover_new_pdfs")
    def test_date_range_options(self, mock_discover):
        mock_discover.return_value = []
        self._call("--start=2026-01-01", "--end=2026-01-31")
        mock_discover.assert_called_once_with(date(2026, 1, 1), date(2026, 1, 31))

    @patch("hansard.management.commands.check_new_hansards.discover_new_pdfs")
    def test_without_auto_process_shows_hint(self, mock_discover):
        mock_discover.return_value = [
            {
                "sitting_date": date(2026, 2, 10),
                "pdf_url": "https://example.com/DR-10022026.pdf",
                "pdf_filename": "DR-10022026.pdf",
            },
        ]
        out, _ = self._call("--days=7")
        self.assertIn("--auto-process", out)

    @patch("hansard.management.commands.check_new_hansards.call_command")
    @patch("hansard.management.commands.check_new_hansards.discover_new_pdfs")
    def test_auto_process_calls_pipeline(self, mock_discover, mock_call):
        mock_discover.return_value = [
            {
                "sitting_date": date(2026, 2, 10),
                "pdf_url": "https://example.com/DR-10022026.pdf",
                "pdf_filename": "DR-10022026.pdf",
            },
        ]
        self._call("--days=7", "--auto-process")
        mock_call.assert_called_once()
        args, kwargs = mock_call.call_args
        self.assertEqual(args[0], "process_hansard")
        self.assertEqual(args[1], "https://example.com/DR-10022026.pdf")

    @patch("hansard.management.commands.check_new_hansards.call_command")
    @patch("hansard.management.commands.check_new_hansards.discover_new_pdfs")
    def test_auto_process_continues_on_failure(self, mock_discover, mock_call):
        """If one PDF fails to process, continue with the rest."""
        mock_discover.return_value = [
            {
                "sitting_date": date(2026, 2, 10),
                "pdf_url": "https://example.com/DR-10022026.pdf",
                "pdf_filename": "DR-10022026.pdf",
            },
            {
                "sitting_date": date(2026, 2, 11),
                "pdf_url": "https://example.com/DR-11022026.pdf",
                "pdf_filename": "DR-11022026.pdf",
            },
        ]
        mock_call.side_effect = [Exception("download failed"), None]
        out, err = self._call("--days=7", "--auto-process")
        self.assertEqual(mock_call.call_count, 2)
        self.assertIn("Failed to process 2026-02-10", err)


class HealthCheckTests(TestCase):
    """Test the /health/ endpoint."""

    def test_health_check_returns_200(self):
        response = self.client.get("/health/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})
