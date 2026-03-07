"""Tests for the evaluator service."""

import json
from unittest.mock import MagicMock, patch

from django.test import TestCase

from parliament.services.evaluator import (
    EvaluationResult,
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
    def test_evaluate_report_api_error_returns_pass(self, mock_genai):
        """Fail-open: API error -> treat as PASS."""
        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = Exception("API error")
        mock_genai.Client.return_value = mock_client

        result = evaluate_report(
            report_html="<p>Report</p>",
            source_briefs="Brief text",
            school_names=[],
            mp_names=[],
        )
        self.assertEqual(result.verdict, "PASS")


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
