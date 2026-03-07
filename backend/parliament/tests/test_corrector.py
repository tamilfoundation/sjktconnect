"""Tests for the corrector service."""

from unittest.mock import MagicMock, patch

from django.test import TestCase

from parliament.services.corrector import (
    apply_code_fixes,
    correct_report,
    MAX_ATTEMPTS,
)
from parliament.services.evaluator import EvaluationResult


class ApplyCodeFixesTests(TestCase):

    def test_fixes_sjkt_brackets(self):
        html = "<p>The (SJK(T)) school needs repair</p>"
        result = apply_code_fixes(html)
        self.assertNotIn("(SJK(T))", result)
        self.assertIn("SJK(T)", result)

    def test_no_change_if_clean(self):
        html = "<p>SJK(T) Ladang Bikam is a school</p>"
        result = apply_code_fixes(html)
        self.assertEqual(html, result)


class CorrectReportTests(TestCase):

    def test_max_attempts_constant(self):
        self.assertEqual(MAX_ATTEMPTS, 3)

    @patch("parliament.services.corrector.genai")
    @patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"})
    def test_reprompt_with_feedback(self, mock_genai):
        mock_response = MagicMock()
        mock_response.text = "## Better Headline\n\nImproved report."
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mock_genai.Client.return_value = mock_client

        eval_result = EvaluationResult(
            verdict="FIX",
            tier2_scores={
                "headline_specificity": {"score": 3, "feedback": "Too generic"},
            },
        )

        corrected = correct_report(
            current_draft="## Tamil School Report\n\nGeneric text.",
            eval_result=eval_result,
            source_briefs="Brief 1. Brief 2.",
        )

        self.assertIsNotNone(corrected)
        mock_client.models.generate_content.assert_called_once()

    def test_no_api_key_returns_none(self):
        import os
        old = os.environ.pop("GEMINI_API_KEY", None)
        try:
            result = correct_report(
                current_draft="Draft",
                eval_result=EvaluationResult(
                    verdict="FIX",
                    tier2_scores={"headline": {"score": 3, "feedback": "Bad"}},
                ),
                source_briefs="Briefs",
            )
            self.assertIsNone(result)
        finally:
            if old is not None:
                os.environ["GEMINI_API_KEY"] = old

    def test_no_feedback_returns_none(self):
        """If all scores are fine, no correction needed."""
        with patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}):
            result = correct_report(
                current_draft="Draft",
                eval_result=EvaluationResult(
                    verdict="FIX",
                    tier2_scores={"headline": {"score": 8}},
                ),
                source_briefs="Briefs",
            )
            self.assertIsNone(result)

    @patch("parliament.services.corrector.genai")
    @patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"})
    def test_api_error_returns_none(self, mock_genai):
        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = Exception("API down")
        mock_genai.Client.return_value = mock_client

        result = correct_report(
            current_draft="Draft",
            eval_result=EvaluationResult(
                verdict="REJECT",
                tier1_results={"fabricated_facts": {"pass": False, "details": "Made up"}},
            ),
            source_briefs="Briefs",
        )
        self.assertIsNone(result)
