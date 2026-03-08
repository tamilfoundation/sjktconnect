"""Tests for the evaluator service."""

import json
from unittest.mock import MagicMock, patch

from django.test import TestCase

from parliament.services.evaluator import (
    EvaluationResult,
    REPORT_TIER2_CRITERIA,
    evaluate_brief,
    evaluate_report,
    _compute_verdict,
)


class ComputeVerdictTests(TestCase):

    def test_tier1_failure_returns_reject(self):
        tier1 = {"fabricated_facts": {"pass": False, "details": "Made up school"}}
        tier2 = {"headline_specificity": {"score": 10}}
        self.assertEqual(_compute_verdict(tier1, tier2), "REJECT")

    def test_tier2_avg_below_6_returns_fix(self):
        tier1 = {"fabricated_facts": {"pass": True}}
        tier2 = {
            "headline_specificity": {"score": 4},
            "key_findings_specificity": {"score": 5},
            "actionability": {"score": 5},
        }
        self.assertEqual(_compute_verdict(tier1, tier2), "FIX")

    def test_tier2_single_below_5_returns_fix(self):
        tier1 = {"fabricated_facts": {"pass": True}}
        tier2 = {
            "headline_specificity": {"score": 4},
            "key_findings_specificity": {"score": 9},
            "actionability": {"score": 9},
        }
        self.assertEqual(_compute_verdict(tier1, tier2), "FIX")

    def test_all_passing_returns_pass(self):
        tier1 = {
            "fabricated_facts": {"pass": True},
            "wrong_attribution": {"pass": True},
        }
        tier2 = {
            "headline_specificity": {"score": 8},
            "key_findings_specificity": {"score": 7},
            "actionability": {"score": 9},
        }
        self.assertEqual(_compute_verdict(tier1, tier2), "PASS")

    def test_empty_tier2_returns_pass_if_tier1_ok(self):
        tier1 = {"fabricated_facts": {"pass": True}}
        self.assertEqual(_compute_verdict(tier1, {}), "PASS")


class EvaluationResultTests(TestCase):

    def test_fields(self):
        r = EvaluationResult(
            verdict="FIX",
            tier1_results={"fabricated_facts": {"pass": True}},
            tier2_scores={"headline_specificity": {"score": 4, "feedback": "Generic"}},
            tier3_flags={"illustration_similarity": "OK"},
            unlinked_schools=["SJK(T) Ladang, Mentakab"],
            repair_suggestions=["Remove comma: SJK(T) Ladang Mentakab"],
        )
        self.assertEqual(r.verdict, "FIX")
        self.assertEqual(len(r.unlinked_schools), 1)

    def test_report_tier2_has_executive_response_attribution(self):
        """REPORT_TIER2_CRITERIA includes executive_response_attribution."""
        self.assertIn("executive_response_attribution", REPORT_TIER2_CRITERIA)


class EvaluateReportTests(TestCase):

    @patch("parliament.services.evaluator.genai")
    @patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"})
    def test_evaluate_report_returns_result(self, mock_genai):
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "verdict": "PASS",
            "tier1_red_lines": {
                "fabricated_facts": {"pass": True, "details": None},
                "wrong_attribution": {"pass": True, "details": None},
                "hallucinated_schools": {"pass": True, "details": None},
                "empty_output": {"pass": True, "details": None},
                "internal_contradiction": {"pass": True, "details": None},
            },
            "tier2_quality": {
                "headline_specificity": {"score": 8, "feedback": None},
                "key_findings_specificity": {"score": 9, "feedback": None},
            },
            "tier3_drift": {"illustration_similarity": "OK"},
            "unlinked_schools": [],
            "repair_suggestions": [],
        })
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mock_genai.Client.return_value = mock_client

        result = evaluate_report(
            report_html="<h2>Headline</h2><p>Report text</p>",
            source_briefs="Brief 1 text. Brief 2 text.",
            school_names=["SJK(T) Ladang Bikam"],
            mp_names=["YB Arul"],
            previous_report="",
        )

        self.assertIsInstance(result, EvaluationResult)
        self.assertEqual(result.verdict, "PASS")
        mock_client.models.generate_content.assert_called_once()

    @patch("parliament.services.evaluator.genai")
    @patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"})
    def test_evaluate_report_reject_on_hallucination(self, mock_genai):
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "verdict": "REJECT",
            "tier1_red_lines": {
                "fabricated_facts": {"pass": True, "details": None},
                "wrong_attribution": {"pass": True, "details": None},
                "hallucinated_schools": {"pass": False, "details": "SJK(T) Ladang Bintang not found"},
                "empty_output": {"pass": True, "details": None},
                "internal_contradiction": {"pass": True, "details": None},
            },
            "tier2_quality": {},
            "tier3_drift": {},
            "unlinked_schools": [],
            "repair_suggestions": [],
        })
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mock_genai.Client.return_value = mock_client

        result = evaluate_report(
            report_html="<p>SJK(T) Ladang Bintang needs help</p>",
            source_briefs="No mention of Ladang Bintang.",
            school_names=["SJK(T) Ladang Bikam"],
            mp_names=[],
        )
        self.assertEqual(result.verdict, "REJECT")

    def test_evaluate_report_no_api_key_returns_pass(self):
        """Fail-open: no API key -> treat as PASS."""
        with patch.dict("os.environ", {}, clear=False):
            # Ensure GEMINI_API_KEY is not set
            import os
            old = os.environ.pop("GEMINI_API_KEY", None)
            try:
                result = evaluate_report(
                    report_html="<p>Report</p>",
                    source_briefs="Brief text",
                    school_names=[],
                    mp_names=[],
                )
                self.assertEqual(result.verdict, "PASS")
            finally:
                if old is not None:
                    os.environ["GEMINI_API_KEY"] = old

    @patch("parliament.services.evaluator.genai")
    @patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"})
    def test_evaluate_report_api_error_returns_amber(self, mock_genai):
        """Fail-safe: API error -> treat as AMBER."""
        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = Exception("API error")
        mock_genai.Client.return_value = mock_client

        result = evaluate_report(
            report_html="<p>Report</p>",
            source_briefs="Brief text",
            school_names=[],
            mp_names=[],
        )
        self.assertEqual(result.verdict, "AMBER")
        self.assertTrue(result.evaluator_error)


class EvaluateBriefTests(TestCase):

    @patch("parliament.services.evaluator.genai")
    @patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"})
    def test_evaluate_brief_returns_result(self, mock_genai):
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "tier1_red_lines": {"fabricated_facts": {"pass": True}},
            "tier2_quality": {"school_linkification": {"score": 9}},
            "tier3_drift": {},
            "unlinked_schools": [],
            "repair_suggestions": [],
        })
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mock_genai.Client.return_value = mock_client

        result = evaluate_brief(
            brief_html="<p>Brief text</p>",
            source_summaries="AI summary text",
            school_names=["SJK(T) Ladang Bikam"],
            mp_names=["YB Arul"],
        )
        self.assertEqual(result.verdict, "PASS")


class FailSafeTests(TestCase):
    """Test fail-safe behaviour: API errors return AMBER, not PASS."""

    @patch("parliament.services.evaluator.genai")
    @patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"})
    def test_api_error_returns_amber(self, mock_genai):
        """API call failure should return AMBER with evaluator_error flag."""
        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = Exception("Timeout")
        mock_genai.Client.return_value = mock_client

        result = evaluate_report(
            report_html="<p>Report</p>",
            source_briefs="Brief text",
            school_names=[],
            mp_names=[],
        )
        self.assertEqual(result.verdict, "AMBER")
        self.assertTrue(result.evaluator_error)

    @patch("parliament.services.evaluator.genai")
    @patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"})
    def test_json_parse_error_returns_amber(self, mock_genai):
        """Invalid JSON from API should return AMBER with evaluator_error flag."""
        mock_response = MagicMock()
        mock_response.text = "NOT VALID JSON {{"
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mock_genai.Client.return_value = mock_client

        result = evaluate_report(
            report_html="<p>Report</p>",
            source_briefs="Brief text",
            school_names=[],
            mp_names=[],
        )
        self.assertEqual(result.verdict, "AMBER")
        self.assertTrue(result.evaluator_error)

    def test_no_api_key_still_returns_pass(self):
        """No API key should still return PASS (fail-open for dev)."""
        import os
        old = os.environ.pop("GEMINI_API_KEY", None)
        try:
            result = evaluate_report(
                report_html="<p>Report</p>",
                source_briefs="Brief text",
                school_names=[],
                mp_names=[],
            )
            self.assertEqual(result.verdict, "PASS")
            self.assertFalse(result.evaluator_error)
        finally:
            if old is not None:
                os.environ["GEMINI_API_KEY"] = old

    @patch("parliament.services.evaluator.genai")
    @patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"})
    def test_brief_api_error_returns_amber(self, mock_genai):
        """Brief evaluator also returns AMBER on API failure."""
        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = Exception("Rate limit")
        mock_genai.Client.return_value = mock_client

        result = evaluate_brief(
            brief_html="<p>Brief</p>",
            source_summaries="Summary",
            school_names=[],
            mp_names=[],
        )
        self.assertEqual(result.verdict, "AMBER")
        self.assertTrue(result.evaluator_error)


class MentionEvaluationTests(TestCase):
    """Test deterministic mention-level evaluation (no API call)."""

    def test_high_confidence_when_all_checks_pass(self):
        from parliament.services.evaluator import evaluate_mention
        from hansard.models import HansardMention, HansardSitting
        sitting = HansardSitting.objects.create(
            sitting_date="2099-06-01",
            pdf_url="https://example.com/t.pdf",
            pdf_filename="t.pdf",
        )
        mention = HansardMention.objects.create(
            sitting=sitting,
            verbatim_quote="YB Arul [Segamat] asked about SJK(T) Ladang Bikam funding of RM2 million for infrastructure repairs and classroom upgrades in the coming financial year.",
            context_before="",
            page_number=1,
            mp_name="YB Arul",
            mp_constituency="Segamat",
            mention_type="BUDGET",
            significance=4,
            ai_summary="MP requests RM2M.",
        )
        result = evaluate_mention(mention)
        self.assertGreaterEqual(result.confidence, 0.8)
        self.assertEqual(len(result.warnings), 0)

    def test_low_confidence_when_speaker_not_in_excerpt(self):
        from parliament.services.evaluator import evaluate_mention
        from hansard.models import HansardMention, HansardSitting
        sitting = HansardSitting.objects.create(
            sitting_date="2099-06-02",
            pdf_url="https://example.com/t.pdf",
            pdf_filename="t.pdf",
        )
        mention = HansardMention.objects.create(
            sitting=sitting,
            verbatim_quote="SJK(T) mentioned in passing.",
            context_before="",
            page_number=1,
            mp_name="YB Phantom",
            mp_constituency="Nowhere",
            mention_type="OTHER",
            significance=2,
            ai_summary="Passing mention.",
        )
        result = evaluate_mention(mention)
        self.assertLess(result.confidence, 0.8)
        self.assertTrue(any("speaker" in w.lower() for w in result.warnings))

    def test_warning_when_high_significance_short_excerpt(self):
        from parliament.services.evaluator import evaluate_mention
        from hansard.models import HansardMention, HansardSitting
        sitting = HansardSitting.objects.create(
            sitting_date="2099-06-03",
            pdf_url="https://example.com/t.pdf",
            pdf_filename="t.pdf",
        )
        mention = HansardMention.objects.create(
            sitting=sitting,
            verbatim_quote="SJK(T) ok.",
            context_before="",
            page_number=1,
            mp_name="",
            mention_type="OTHER",
            significance=4,
            ai_summary="Short.",
        )
        result = evaluate_mention(mention)
        self.assertTrue(any("significance" in w.lower() for w in result.warnings))

    def test_warning_when_budget_type_no_financial_terms(self):
        from parliament.services.evaluator import evaluate_mention
        from hansard.models import HansardMention, HansardSitting
        sitting = HansardSitting.objects.create(
            sitting_date="2099-06-04",
            pdf_url="https://example.com/t.pdf",
            pdf_filename="t.pdf",
        )
        mention = HansardMention.objects.create(
            sitting=sitting,
            verbatim_quote="The MP discussed SJK(T) school conditions and student welfare.",
            context_before="",
            page_number=1,
            mp_name="YB Test",
            mention_type="BUDGET",
            significance=3,
            ai_summary="Discussed conditions.",
        )
        result = evaluate_mention(mention)
        self.assertTrue(any("budget" in w.lower() for w in result.warnings))

    def test_no_mp_name_skips_speaker_check(self):
        """Empty mp_name should not trigger speaker warning."""
        from parliament.services.evaluator import evaluate_mention
        from hansard.models import HansardMention, HansardSitting
        sitting = HansardSitting.objects.create(
            sitting_date="2099-06-05",
            pdf_url="https://example.com/t.pdf",
            pdf_filename="t.pdf",
        )
        mention = HansardMention.objects.create(
            sitting=sitting,
            verbatim_quote="SJK(T) mentioned in a long discussion about school funding and RM allocations.",
            context_before="",
            page_number=1,
            mp_name="",
            mention_type="OTHER",
            significance=2,
            ai_summary="General mention.",
        )
        result = evaluate_mention(mention)
        self.assertFalse(any("speaker" in w.lower() for w in result.warnings))
