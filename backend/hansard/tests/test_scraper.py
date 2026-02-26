"""Tests for the Hansard PDF scraper (discovery via HEAD requests)."""

from datetime import date
from unittest.mock import MagicMock, patch

from django.test import TestCase

from hansard.pipeline.scraper import (
    _build_filename,
    _build_url,
    _pdf_exists,
    discover_new_pdfs,
)


class BuildUrlTests(TestCase):
    """Test URL and filename generation."""

    def test_build_filename(self):
        self.assertEqual(_build_filename(date(2026, 1, 26)), "DR-26012026.pdf")

    def test_build_filename_zero_padded(self):
        self.assertEqual(_build_filename(date(2026, 2, 3)), "DR-03022026.pdf")

    def test_build_url(self):
        url = _build_url(date(2026, 1, 26))
        self.assertEqual(
            url,
            "https://www.parlimen.gov.my/files/hindex/pdf/DR-26012026.pdf",
        )


class PdfExistsTests(TestCase):
    """Test HEAD request probing."""

    @patch("hansard.pipeline.scraper.requests.head")
    def test_returns_true_on_200(self, mock_head):
        mock_head.return_value = MagicMock(status_code=200)
        self.assertTrue(_pdf_exists("https://example.com/test.pdf"))

    @patch("hansard.pipeline.scraper.requests.head")
    def test_returns_false_on_404(self, mock_head):
        mock_head.return_value = MagicMock(status_code=404)
        self.assertFalse(_pdf_exists("https://example.com/test.pdf"))

    @patch("hansard.pipeline.scraper.requests.head")
    def test_returns_false_on_network_error(self, mock_head):
        import requests
        mock_head.side_effect = requests.ConnectionError("timeout")
        self.assertFalse(_pdf_exists("https://example.com/test.pdf"))

    @patch("hansard.pipeline.scraper.requests.head")
    def test_ssl_verify_disabled(self, mock_head):
        mock_head.return_value = MagicMock(status_code=200)
        _pdf_exists("https://www.parlimen.gov.my/files/hindex/pdf/DR-26012026.pdf")
        mock_head.assert_called_once()
        _, kwargs = mock_head.call_args
        self.assertFalse(kwargs["verify"])


class DiscoverNewPdfsTests(TestCase):
    """Test date range scanning."""

    @patch("hansard.pipeline.scraper._pdf_exists")
    def test_finds_pdfs_in_range(self, mock_exists):
        # Only Mon 27 Jan exists
        mock_exists.side_effect = lambda url: "27012026" in url
        results = discover_new_pdfs(date(2026, 1, 26), date(2026, 1, 30))
        # 26 Jan = Mon, 27 = Tue, 28 = Wed, 29 = Thu, 30 = Fri
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["sitting_date"], date(2026, 1, 27))

    @patch("hansard.pipeline.scraper._pdf_exists")
    def test_skips_weekends(self, mock_exists):
        mock_exists.return_value = True
        # Sat 31 Jan + Sun 1 Feb 2026 — actually let me use a real weekend
        # 31 Jan 2026 = Saturday, 1 Feb 2026 = Sunday
        results = discover_new_pdfs(date(2026, 1, 31), date(2026, 2, 1))
        self.assertEqual(len(results), 0)
        mock_exists.assert_not_called()

    @patch("hansard.pipeline.scraper._pdf_exists")
    def test_includes_weekends_when_flag_off(self, mock_exists):
        mock_exists.return_value = True
        results = discover_new_pdfs(
            date(2026, 1, 31), date(2026, 2, 1), skip_weekends=False
        )
        self.assertEqual(len(results), 2)

    @patch("hansard.pipeline.scraper._pdf_exists")
    def test_empty_range(self, mock_exists):
        results = discover_new_pdfs(date(2026, 2, 1), date(2026, 1, 1))
        self.assertEqual(len(results), 0)
        mock_exists.assert_not_called()

    @patch("hansard.pipeline.scraper._pdf_exists")
    def test_single_day(self, mock_exists):
        mock_exists.return_value = True
        results = discover_new_pdfs(date(2026, 2, 2), date(2026, 2, 2))
        # 2 Feb 2026 = Monday
        self.assertEqual(len(results), 1)

    @patch("hansard.pipeline.scraper._pdf_exists")
    def test_result_structure(self, mock_exists):
        mock_exists.return_value = True
        results = discover_new_pdfs(date(2026, 2, 2), date(2026, 2, 2))
        pdf = results[0]
        self.assertIn("sitting_date", pdf)
        self.assertIn("pdf_url", pdf)
        self.assertIn("pdf_filename", pdf)
        self.assertEqual(pdf["pdf_filename"], "DR-02022026.pdf")
