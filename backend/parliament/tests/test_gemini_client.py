"""Tests for Gemini client service — all API calls mocked."""

import json
from unittest.mock import MagicMock, patch

from django.test import TestCase

from hansard.models import HansardMention, HansardSitting
from parliament.services.gemini_client import (
    _build_excerpt,
    _validate_response,
    analyse_mention,
    apply_analysis,
)


class BuildExcerptTests(TestCase):
    """Test excerpt construction and truncation."""

    def _make_mention(self, quote, before="", after=""):
        sitting = HansardSitting.objects.create(
            sitting_date="2026-01-26",
            pdf_url="https://example.com/test.pdf",
            pdf_filename="test.pdf",
        )
        return HansardMention.objects.create(
            sitting=sitting,
            verbatim_quote=quote,
            context_before=before,
            context_after=after,
            page_number=1,
        )

    def test_basic_excerpt(self):
        mention = self._make_mention(
            quote="SJK(T) Ladang Bikam needs repairs.",
            before="Tuan Pengerusi,",
            after="Terima kasih.",
        )
        excerpt = _build_excerpt(mention)
        self.assertIn("Tuan Pengerusi", excerpt)
        self.assertIn("SJK(T) Ladang Bikam", excerpt)
        self.assertIn("Terima kasih", excerpt)

    def test_no_context(self):
        mention = self._make_mention(quote="SJK(T) mentioned here.")
        excerpt = _build_excerpt(mention)
        self.assertEqual(excerpt, "SJK(T) mentioned here.")

    def test_truncation_at_1500_chars(self):
        long_text = "A" * 2000
        mention = self._make_mention(quote=long_text)
        excerpt = _build_excerpt(mention)
        self.assertLessEqual(len(excerpt), 1504)  # 1500 + "..."
        self.assertTrue(excerpt.endswith("..."))

    def test_excerpt_includes_speaker_hint(self):
        """When mention has mp_name from regex, excerpt should include it as a hint."""
        mention = self._make_mention(
            quote="SJK(T) Ladang Bikam needs repairs.",
            before="Tuan Ganabatirau a/l Veraman [Klang]:",
        )
        mention.mp_name = "Tuan Ganabatirau a/l Veraman"
        mention.mp_constituency = "Klang"
        mention.save()
        excerpt = _build_excerpt(mention)
        self.assertIn("[Speaker detected: Tuan Ganabatirau a/l Veraman", excerpt)


class ValidateResponseTests(TestCase):
    """Test validation and normalisation of Gemini output."""

    def test_valid_response(self):
        data = {
            "mp_name": "YB Dato' Sri Arul",
            "mp_constituency": "Tapah",
            "mp_party": "BN",
            "mention_type": "BUDGET",
            "significance": 4,
            "sentiment": "ADVOCATING",
            "change_indicator": "NEW",
            "summary": "MP requests budget for school repairs.",
        }
        result = _validate_response(data)
        self.assertEqual(result["mp_name"], "YB Dato' Sri Arul")
        self.assertEqual(result["mention_type"], "BUDGET")
        self.assertEqual(result["significance"], 4)
        self.assertEqual(result["sentiment"], "ADVOCATING")

    def test_invalid_enum_defaults(self):
        data = {
            "mention_type": "INVALID",
            "sentiment": "ANGRY",
            "change_indicator": "WHATEVER",
        }
        result = _validate_response(data)
        self.assertEqual(result["mention_type"], "OTHER")
        self.assertEqual(result["sentiment"], "NEUTRAL")
        self.assertEqual(result["change_indicator"], "NEW")

    def test_significance_clamped(self):
        self.assertEqual(_validate_response({"significance": 0})["significance"], 1)
        self.assertEqual(_validate_response({"significance": 10})["significance"], 5)
        self.assertEqual(_validate_response({"significance": "abc"})["significance"], 1)
        self.assertEqual(_validate_response({"significance": None})["significance"], 1)

    def test_missing_fields_get_defaults(self):
        result = _validate_response({})
        self.assertEqual(result["mp_name"], "")
        self.assertEqual(result["mention_type"], "OTHER")
        self.assertEqual(result["significance"], 1)
        self.assertEqual(result["sentiment"], "NEUTRAL")
        self.assertEqual(result["change_indicator"], "NEW")
        self.assertEqual(result["summary"], "")

    def test_case_normalisation(self):
        data = {"mention_type": "budget", "sentiment": "advocating"}
        result = _validate_response(data)
        self.assertEqual(result["mention_type"], "BUDGET")
        self.assertEqual(result["sentiment"], "ADVOCATING")


class AnalyseMentionTests(TestCase):
    """Test the full analyse_mention flow with mocked Gemini."""

    def setUp(self):
        self.sitting = HansardSitting.objects.create(
            sitting_date="2026-01-26",
            pdf_url="https://example.com/test.pdf",
            pdf_filename="test.pdf",
        )
        self.mention = HansardMention.objects.create(
            sitting=self.sitting,
            verbatim_quote="SJK(T) Ladang Bikam memerlukan peruntukan.",
            context_before="Tuan Pengerusi, saya ingin bertanya tentang",
            context_after="Terima kasih.",
            page_number=42,
            keyword_matched="SJK(T)",
        )

    @patch("parliament.services.gemini_client._get_client")
    def test_successful_analysis(self, mock_get_client):
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "mp_name": "YB Dato' Sri Arul",
            "mp_constituency": "Tapah",
            "mp_party": "BN",
            "mention_type": "BUDGET",
            "significance": 4,
            "sentiment": "ADVOCATING",
            "change_indicator": "NEW",
            "summary": "MP requests budget for SJK(T) Ladang Bikam repairs.",
        })
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mock_get_client.return_value = mock_client

        result = analyse_mention(self.mention)

        self.assertIsNotNone(result)
        self.assertEqual(result["mp_name"], "YB Dato' Sri Arul")
        self.assertEqual(result["mention_type"], "BUDGET")
        self.assertEqual(result["significance"], 4)
        self.assertIn("raw_response", result)

    @patch("parliament.services.gemini_client._get_client")
    def test_api_error_returns_none(self, mock_get_client):
        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = Exception("API error")
        mock_get_client.return_value = mock_client
        result = analyse_mention(self.mention)
        self.assertIsNone(result)

    @patch("parliament.services.gemini_client._get_client")
    def test_invalid_json_returns_none(self, mock_get_client):
        mock_response = MagicMock()
        mock_response.text = "This is not JSON"
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mock_get_client.return_value = mock_client

        result = analyse_mention(self.mention)
        self.assertIsNone(result)


class ApplyAnalysisTests(TestCase):
    """Test applying analysis results to a mention."""

    def test_apply_updates_fields(self):
        sitting = HansardSitting.objects.create(
            sitting_date="2026-01-26",
            pdf_url="https://example.com/test.pdf",
            pdf_filename="test.pdf",
        )
        mention = HansardMention.objects.create(
            sitting=sitting,
            verbatim_quote="Test quote",
            page_number=1,
        )

        analysis = {
            "mp_name": "YB Test",
            "mp_constituency": "Segamat",
            "mp_party": "PH",
            "mention_type": "QUESTION",
            "significance": 3,
            "sentiment": "NEUTRAL",
            "change_indicator": "NEW",
            "summary": "Test summary.",
            "raw_response": {"mp_name": "YB Test"},
        }

        apply_analysis(mention, analysis)

        mention.refresh_from_db()
        self.assertEqual(mention.mp_name, "YB Test")
        self.assertEqual(mention.mp_constituency, "Segamat")
        self.assertEqual(mention.mention_type, "QUESTION")
        self.assertEqual(mention.significance, 3)
        self.assertEqual(mention.ai_summary, "Test summary.")
        self.assertEqual(mention.ai_raw_response, {"mp_name": "YB Test"})
