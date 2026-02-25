"""Tests for Hansard PDF downloader."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from django.test import TestCase

from hansard.pipeline.downloader import (
    _extract_filename,
    _filename_from_content_disposition,
    download_hansard,
)


class ExtractFilenameTests(TestCase):
    """Test filename extraction from URLs."""

    def test_simple_pdf_url(self):
        result = _extract_filename(
            "https://www.parlimen.gov.my/files/hindex/pdf/DR-20022026.pdf"
        )
        self.assertEqual(result, "DR-20022026.pdf")

    def test_encoded_url(self):
        result = _extract_filename(
            "https://example.com/files/DR%2020022026.pdf"
        )
        self.assertEqual(result, "DR 20022026.pdf")

    def test_no_filename_in_url(self):
        result = _extract_filename("https://example.com/download/")
        self.assertEqual(result, "hansard.pdf")


class ContentDispositionTests(TestCase):
    """Test filename extraction from Content-Disposition headers."""

    def test_with_filename(self):
        result = _filename_from_content_disposition(
            'attachment; filename="DR-20022026.pdf"'
        )
        self.assertEqual(result, "DR-20022026.pdf")

    def test_without_quotes(self):
        result = _filename_from_content_disposition(
            "attachment; filename=DR-20022026.pdf"
        )
        self.assertEqual(result, "DR-20022026.pdf")

    def test_empty_header(self):
        result = _filename_from_content_disposition("")
        self.assertEqual(result, "")

    def test_no_filename_part(self):
        result = _filename_from_content_disposition("attachment")
        self.assertEqual(result, "")


class DownloadHansardTests(TestCase):
    """Test download_hansard with mocked HTTP."""

    @patch("hansard.pipeline.downloader.requests.get")
    def test_successful_download(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.iter_content.return_value = [b"fake pdf content"]
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        with tempfile.TemporaryDirectory() as tmpdir:
            result = download_hansard(
                "https://example.com/DR-20022026.pdf", tmpdir
            )
            self.assertTrue(result.exists())
            self.assertEqual(result.name, "DR-20022026.pdf")
            self.assertEqual(result.read_bytes(), b"fake pdf content")

    @patch("hansard.pipeline.downloader.requests.get")
    def test_skips_existing_file(self, mock_get):
        """Should not re-download if file already exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            existing = Path(tmpdir) / "DR-20022026.pdf"
            existing.write_text("already here")

            result = download_hansard(
                "https://example.com/DR-20022026.pdf", tmpdir
            )
            self.assertEqual(result, existing)
            mock_get.assert_not_called()

    @patch("hansard.pipeline.downloader.requests.get")
    @patch("hansard.pipeline.downloader.RETRY_DELAY_SECONDS", 0)
    def test_retries_on_failure(self, mock_get):
        """Should retry up to MAX_RETRIES times."""
        import requests as req

        mock_get.side_effect = req.ConnectionError("Network error")

        with tempfile.TemporaryDirectory() as tmpdir:
            with self.assertRaises(req.HTTPError):
                download_hansard(
                    "https://example.com/test.pdf", tmpdir
                )
            self.assertEqual(mock_get.call_count, 3)
