"""Tests for Gemini client service — all API calls mocked."""

import json
from unittest.mock import MagicMock, patch

from django.test import TestCase

from hansard.models import HansardMention, HansardSitting
from parliament.models import MP
from schools.models import Constituency
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

    @patch("parliament.services.context_builder.build_context")
    @patch("parliament.services.gemini_client._get_client")
    def test_successful_analysis(self, mock_get_client, mock_build_ctx):
        mock_build_ctx.return_value = {"cabinet": {}, "glossary": {}}
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

    @patch("parliament.services.context_builder.build_context")
    @patch("parliament.services.gemini_client._get_client")
    def test_prompt_includes_domain_context(self, mock_get_client, mock_build_ctx):
        mock_build_ctx.return_value = {
            "cabinet": {
                "education": {
                    "minister": "Dato' Sri Fadhlina binti Sidek",
                    "portfolio": "Minister of Education",
                }
            },
            "glossary": {"SJK(T)": "Tamil vernacular school"},
            "taxonomy": {},
        }
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "mp_name": "YB Test",
            "mp_constituency": "Test",
            "mp_party": "PH",
            "mention_type": "QUESTION",
            "significance": 3,
            "sentiment": "NEUTRAL",
            "change_indicator": "NEW",
            "summary": "Asked about funding.",
        })
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mock_get_client.return_value = mock_client

        analyse_mention(self.mention)

        # Verify the prompt sent to Gemini includes cabinet reference
        call_args = mock_client.models.generate_content.call_args
        prompt_sent = call_args.kwargs.get("contents") or call_args[1].get("contents", "")
        self.assertIn("CABINET REFERENCE", prompt_sent)
        self.assertIn("Fadhlina", prompt_sent)

    @patch("parliament.services.context_builder.build_context")
    @patch("parliament.services.gemini_client._get_client")
    def test_prompt_enforces_past_tense(self, mock_get_client, mock_build_ctx):
        mock_build_ctx.return_value = {"cabinet": {}, "glossary": {}}
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "mp_name": "", "mp_constituency": "", "mp_party": "",
            "mention_type": "OTHER", "significance": 1,
            "sentiment": "NEUTRAL", "change_indicator": "NEW",
            "summary": "Test.",
        })
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mock_get_client.return_value = mock_client

        analyse_mention(self.mention)

        call_args = mock_client.models.generate_content.call_args
        prompt_sent = call_args.kwargs.get("contents") or call_args[1].get("contents", "")
        self.assertIn("PAST TENSE", prompt_sent)

    @patch("parliament.services.context_builder.build_context")
    @patch("parliament.services.gemini_client._get_client")
    def test_api_error_returns_none(self, mock_get_client, mock_build_ctx):
        mock_build_ctx.return_value = {"cabinet": {}, "glossary": {}}
        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = Exception("API error")
        mock_get_client.return_value = mock_client
        result = analyse_mention(self.mention)
        self.assertIsNone(result)

    @patch("parliament.services.context_builder.build_context")
    @patch("parliament.services.gemini_client._get_client")
    def test_invalid_json_returns_none(self, mock_get_client, mock_build_ctx):
        mock_build_ctx.return_value = {"cabinet": {}, "glossary": {}}
        mock_response = MagicMock()
        mock_response.text = "This is not JSON"
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mock_get_client.return_value = mock_client

        result = analyse_mention(self.mention)
        self.assertIsNone(result)

    @patch("parliament.services.context_builder.build_context")
    @patch("parliament.services.gemini_client._get_client")
    def test_context_failure_graceful(self, mock_get_client, mock_build_ctx):
        """If context_builder fails, analysis should still proceed."""
        mock_build_ctx.side_effect = FileNotFoundError("No context JSON")
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "mp_name": "YB Test", "mp_constituency": "", "mp_party": "",
            "mention_type": "OTHER", "significance": 1,
            "sentiment": "NEUTRAL", "change_indicator": "NEW",
            "summary": "Test.",
        })
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mock_get_client.return_value = mock_client

        result = analyse_mention(self.mention)
        self.assertIsNotNone(result)
        self.assertEqual(result["mp_name"], "YB Test")


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


class ApplyAnalysisWithResolverTests(TestCase):
    """Test that analysis pipeline enriches MP data from database."""

    @classmethod
    def setUpTestData(cls):
        cls.constituency = Constituency.objects.create(
            code="P078", name="Klang", state="Selangor",
        )
        cls.mp = MP.objects.create(
            constituency=cls.constituency,
            name="Tuan Ganabatirau a/l Veraman",
            party="PH(DAP)",
        )

    def test_resolver_enriches_party_after_analysis(self):
        from parliament.services.mp_resolver import resolve_mp

        analysis = {
            "mp_name": "Ganabatirau",
            "mp_constituency": "Klang",
            "mp_party": "",
            "mention_type": "QUESTION",
            "significance": 3,
            "sentiment": "ADVOCATING",
            "change_indicator": "NEW",
            "summary": "Asked about SJK(T) funding.",
        }
        resolved = resolve_mp(
            analysis["mp_name"], analysis["mp_constituency"], analysis["mp_party"]
        )
        analysis.update(resolved)
        self.assertEqual(analysis["mp_party"], "PH(DAP)")
        self.assertEqual(analysis["mp_name"], "Tuan Ganabatirau a/l Veraman")


class SpeakerValidationTests(TestCase):
    """Test speaker verification during apply_analysis."""

    def _make_mention(self, quote, context_before=""):
        sitting = HansardSitting.objects.create(
            sitting_date="2026-02-15",
            pdf_url="https://example.com/test.pdf",
            pdf_filename="test.pdf",
        )
        return HansardMention.objects.create(
            sitting=sitting,
            verbatim_quote=quote,
            context_before=context_before,
            page_number=1,
        )

    def _base_analysis(self, mp_name="YB Dato' Sri Arul"):
        return {
            "mp_name": mp_name,
            "mp_constituency": "",
            "mp_party": "",
            "mention_type": "QUESTION",
            "significance": 3,
            "sentiment": "NEUTRAL",
            "change_indicator": "NEW",
            "summary": "Test summary.",
            "raw_response": {},
        }

    def test_speaker_verified_when_name_in_quote(self):
        """Full name found in verbatim_quote → speaker_verified=True."""
        mention = self._make_mention(
            quote="YB Dato' Sri Arul asked about SJK(T) funding.",
        )
        apply_analysis(mention, self._base_analysis("YB Dato' Sri Arul"))
        mention.refresh_from_db()
        self.assertTrue(mention.speaker_verified)

    def test_speaker_unverified_when_name_not_in_excerpt(self):
        """Name not in quote or context → speaker_verified=False."""
        mention = self._make_mention(
            quote="SJK(T) Ladang Bikam needs repairs.",
            context_before="Tuan Pengerusi,",
        )
        apply_analysis(mention, self._base_analysis("YB Someone Else"))
        mention.refresh_from_db()
        self.assertFalse(mention.speaker_verified)

    def test_speaker_verified_by_surname_fragment(self):
        """Surname fragment found in excerpt → speaker_verified=True."""
        mention = self._make_mention(
            quote="Ganabatirau raised the issue of SJK(T) closures.",
        )
        apply_analysis(mention, self._base_analysis("Tuan Ganabatirau a/l Veraman"))
        mention.refresh_from_db()
        self.assertTrue(mention.speaker_verified)

    def test_speaker_verified_when_name_in_context_before(self):
        """Name found in context_before → speaker_verified=True."""
        mention = self._make_mention(
            quote="SJK(T) Ladang Bikam needs repairs.",
            context_before="YB Dato' Sri Arul [Tapah]:",
        )
        apply_analysis(mention, self._base_analysis("YB Dato' Sri Arul"))
        mention.refresh_from_db()
        self.assertTrue(mention.speaker_verified)

    def test_speaker_verified_true_when_no_mp_name(self):
        """Empty mp_name → nothing to verify → speaker_verified=True."""
        mention = self._make_mention(
            quote="SJK(T) mentioned in passing.",
        )
        apply_analysis(mention, self._base_analysis(""))
        mention.refresh_from_db()
        self.assertTrue(mention.speaker_verified)
