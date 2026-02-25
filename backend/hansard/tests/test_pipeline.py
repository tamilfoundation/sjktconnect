"""Integration tests for the full Hansard pipeline (process_hansard command).

Downloads are mocked — tests use a sample text fixture.
"""

import tempfile
from datetime import date
from pathlib import Path
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase

from hansard.management.commands import process_hansard as cmd_module
from hansard.models import HansardMention, HansardSitting

# Sample Hansard text that simulates a real parliamentary session
SAMPLE_HANSARD_TEXT = """
DEWAN RAKYAT
PARLIMEN KELIMA BELAS
PENGGAL KETIGA
MESYUARAT PERTAMA

Bil. 15 Rabu 20 Februari 2026

Tuan Ahmad bin Hassan [Segamat]: Tuan Yang di-Pertua, saya ingin
membangkitkan isu berkenaan SJK(T) Ladang Bikam di kawasan parlimen saya.
Sekolah ini memerlukan peruntukan sebanyak RM2 juta untuk membaiki
bangunan yang sudah uzur.

[Page break]

Timbalan Menteri Pendidikan [Dato' Sri Ramasamy]: Terima kasih Tuan Yang
di-Pertua. Kerajaan sedia maklum tentang masalah yang dihadapi oleh
sekolah Tamil di kawasan ladang. Kita telah memperuntukkan sebanyak
RM50 juta untuk membaiki 15 buah SJKT di seluruh negara termasuk
SJKT Ladang Bikam dan S.J.K.(T) Ladang Batu Arang.

[Page break]

Puan Kavitha a/p Subramaniam [Batu Gajah]: Tuan Yang di-Pertua,
saya ingin bertanya tentang peruntukan untuk Sekolah Jenis Kebangsaan
(Tamil) Gunung Cheroh di Batu Gajah. Sekolah ini mempunyai enrolmen
seramai 45 orang murid dan menghadapi masalah kekurangan guru.
"""


class ProcessHansardCommandTests(TestCase):
    """Test process_hansard management command with mocked download."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.url = (
            "https://www.parlimen.gov.my/files/hindex/pdf/DR-20022026.pdf"
        )

    @patch.object(cmd_module, "extract_text")
    @patch.object(cmd_module, "download_hansard")
    def test_full_pipeline(self, mock_download, mock_extract):
        """Pipeline should create sitting + mentions from sample text."""
        fake_pdf = Path(self.temp_dir) / "DR-20022026.pdf"
        fake_pdf.write_text("fake pdf content")
        mock_download.return_value = fake_pdf

        pages = SAMPLE_HANSARD_TEXT.split("[Page break]")
        mock_extract.return_value = [
            (i + 1, page) for i, page in enumerate(pages)
        ]

        call_command(
            "process_hansard",
            self.url,
            "--sitting-date", "2026-02-20",
            "--dest-dir", self.temp_dir,
        )

        sitting = HansardSitting.objects.get(
            sitting_date=date(2026, 2, 20)
        )
        self.assertEqual(sitting.status, HansardSitting.Status.COMPLETED)
        self.assertEqual(sitting.total_pages, 3)
        self.assertEqual(sitting.pdf_url, self.url)

        mentions = HansardMention.objects.filter(sitting=sitting)
        self.assertGreater(mentions.count(), 0)
        self.assertEqual(sitting.mention_count, mentions.count())

        matched_keywords = set(
            mentions.values_list("keyword_matched", flat=True)
        )
        self.assertTrue(
            matched_keywords,
            "Should have matched at least one keyword"
        )

    @patch.object(cmd_module, "extract_text")
    @patch.object(cmd_module, "download_hansard")
    def test_mention_has_context(self, mock_download, mock_extract):
        """Each mention should have verbatim quote and context."""
        fake_pdf = Path(self.temp_dir) / "DR-20022026.pdf"
        fake_pdf.write_text("fake")
        mock_download.return_value = fake_pdf
        mock_extract.return_value = [(1, SAMPLE_HANSARD_TEXT)]

        call_command(
            "process_hansard",
            self.url,
            "--sitting-date", "2026-02-20",
            "--dest-dir", self.temp_dir,
        )

        mention = HansardMention.objects.first()
        self.assertIsNotNone(mention)
        self.assertTrue(len(mention.verbatim_quote) > 0)
        self.assertIsNotNone(mention.page_number)

    @patch.object(cmd_module, "extract_text")
    @patch.object(cmd_module, "download_hansard")
    def test_reprocess_replaces_mentions(
        self, mock_download, mock_extract
    ):
        """Reprocessing the same sitting should replace old mentions."""
        fake_pdf = Path(self.temp_dir) / "DR-20022026.pdf"
        fake_pdf.write_text("fake")
        mock_download.return_value = fake_pdf
        mock_extract.return_value = [(1, SAMPLE_HANSARD_TEXT)]

        sitting = HansardSitting.objects.create(
            sitting_date=date(2026, 2, 20),
            pdf_url=self.url,
            pdf_filename="DR-20022026.pdf",
            status=HansardSitting.Status.FAILED,
        )

        call_command(
            "process_hansard",
            self.url,
            "--sitting-date", "2026-02-20",
            "--dest-dir", self.temp_dir,
        )

        sitting.refresh_from_db()
        self.assertEqual(sitting.status, HansardSitting.Status.COMPLETED)
        self.assertGreater(sitting.mention_count, 0)

    @patch.object(cmd_module, "extract_text")
    @patch.object(cmd_module, "download_hansard")
    def test_no_mentions_found(self, mock_download, mock_extract):
        """Pipeline should complete even with zero mentions."""
        fake_pdf = Path(self.temp_dir) / "test.pdf"
        fake_pdf.write_text("fake")
        mock_download.return_value = fake_pdf
        mock_extract.return_value = [
            (1, "This page discusses infrastructure development."),
        ]

        call_command(
            "process_hansard",
            self.url,
            "--sitting-date", "2026-02-20",
            "--dest-dir", self.temp_dir,
        )

        sitting = HansardSitting.objects.get(
            sitting_date=date(2026, 2, 20)
        )
        self.assertEqual(sitting.status, HansardSitting.Status.COMPLETED)
        self.assertEqual(sitting.mention_count, 0)

    def test_date_extraction_from_url(self):
        """Date should be extractable from DR-DDMMYYYY.pdf pattern."""
        cmd = cmd_module.Command()
        result = cmd._resolve_sitting_date(
            None,
            "https://www.parlimen.gov.my/files/hindex/pdf/DR-20022026.pdf"
        )
        self.assertEqual(result, date(2026, 2, 20))

    def test_date_extraction_iso_format(self):
        """Explicit --sitting-date should work."""
        cmd = cmd_module.Command()
        result = cmd._resolve_sitting_date("2026-02-20", "any-url")
        self.assertEqual(result, date(2026, 2, 20))


class HansardModelTests(TestCase):
    """Test model creation and string representations."""

    def test_sitting_str(self):
        sitting = HansardSitting.objects.create(
            sitting_date=date(2026, 2, 20),
            pdf_url="https://example.com/test.pdf",
            pdf_filename="test.pdf",
        )
        self.assertIn("2026-02-20", str(sitting))
        self.assertIn("Pending", str(sitting))

    def test_mention_str(self):
        sitting = HansardSitting.objects.create(
            sitting_date=date(2026, 2, 20),
            pdf_url="https://example.com/test.pdf",
            pdf_filename="test.pdf",
        )
        mention = HansardMention.objects.create(
            sitting=sitting,
            page_number=5,
            verbatim_quote="SJK(T) Ladang Bikam",
            keyword_matched="sjk(t)",
        )
        self.assertIn("sjk(t)", str(mention))
        self.assertIn("5", str(mention))

    def test_sitting_status_choices(self):
        sitting = HansardSitting.objects.create(
            sitting_date=date(2026, 2, 20),
            pdf_url="https://example.com/test.pdf",
            pdf_filename="test.pdf",
            status=HansardSitting.Status.COMPLETED,
        )
        self.assertEqual(sitting.get_status_display(), "Completed")
