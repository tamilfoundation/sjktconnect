"""Tests for the monthly analyst service (Gemini-powered trend analysis)."""

from unittest.mock import patch, Mock
from django.test import TestCase, override_settings
from broadcasts.services.monthly_analyst import generate_monthly_analysis


@patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"})
class MonthlyAnalystTest(TestCase):
    @patch("broadcasts.services.monthly_analyst.aggregate_month")
    @patch("broadcasts.services.monthly_analyst.genai")
    def test_generates_analytical_content(self, mock_genai, mock_agg):
        mock_agg.return_value = {"parliament": [], "news": [], "scorecards": []}

        mock_response = Mock()
        mock_response.text = '{"executive_summary": "Quiet month.", "trend_lines": [{"trend": "Mentions declining", "direction": "down", "detail": "Down 20%."}], "emerging_signals": ["Teacher shortage mentioned."], "fading_from_view": ["Transport fading."], "opportunity_watch": ["MP X opened door."], "school_spotlight": {"name": "SJK(T) Ladang Bikam", "reason": "Most mentioned."}, "by_the_numbers": {"parliament_mentions": 5, "news_articles": 12, "schools_affected": 8, "sentiment_positive": 7, "sentiment_negative": 3}}'
        mock_genai.Client.return_value.models.generate_content.return_value = mock_response

        result = generate_monthly_analysis(2026, 2)

        self.assertIn("executive_summary", result)
        self.assertIn("trend_lines", result)
        self.assertIn("emerging_signals", result)
        self.assertIn("fading_from_view", result)
        self.assertIn("opportunity_watch", result)
        self.assertIn("by_the_numbers", result)

    @patch("broadcasts.services.monthly_analyst.aggregate_month")
    @patch("broadcasts.services.monthly_analyst.genai")
    def test_returns_none_on_invalid_json(self, mock_genai, mock_agg):
        mock_agg.return_value = {"parliament": [], "news": [], "scorecards": []}
        mock_response = Mock()
        mock_response.text = "not json"
        mock_genai.Client.return_value.models.generate_content.return_value = mock_response
        result = generate_monthly_analysis(2026, 2)
        self.assertIsNone(result)

    @patch("broadcasts.services.monthly_analyst.aggregate_month")
    @patch("broadcasts.services.monthly_analyst.genai")
    def test_returns_none_on_missing_keys(self, mock_genai, mock_agg):
        mock_agg.return_value = {"parliament": [], "news": [], "scorecards": []}
        mock_response = Mock()
        mock_response.text = '{"executive_summary": "test"}'
        mock_genai.Client.return_value.models.generate_content.return_value = mock_response
        result = generate_monthly_analysis(2026, 2)
        self.assertIsNone(result)

    @patch("broadcasts.services.monthly_analyst.aggregate_month")
    @patch("broadcasts.services.monthly_analyst.genai")
    def test_compares_with_previous_month(self, mock_genai, mock_agg):
        """Should call aggregate_month twice - current and previous."""
        mock_agg.return_value = {"parliament": [], "news": [], "scorecards": []}
        mock_response = Mock()
        mock_response.text = '{"executive_summary": "t", "trend_lines": [], "emerging_signals": [], "fading_from_view": [], "opportunity_watch": [], "school_spotlight": null, "by_the_numbers": {"parliament_mentions": 0, "news_articles": 0, "schools_affected": 0, "sentiment_positive": 0, "sentiment_negative": 0}}'
        mock_genai.Client.return_value.models.generate_content.return_value = mock_response

        generate_monthly_analysis(2026, 2)
        # Should be called for Feb 2026 AND Jan 2026
        self.assertEqual(mock_agg.call_count, 2)
