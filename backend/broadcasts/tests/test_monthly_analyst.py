"""Tests for the monthly analyst service (Gemini-powered trend analysis)."""

from unittest.mock import patch, Mock
from django.test import TestCase
from broadcasts.services.monthly_analyst import generate_monthly_analysis


def _aggregate_stub(**overrides):
    """Stub matching the Sprint 23 aggregate_month return shape."""
    base = {
        "parliament": [],
        "news": [],
        "scorecards": [],
        "briefs": [],
        "meeting_reports": [],
        "scorecards_are_lifetime_fallback": False,
        # Sprint 23 deterministic counts
        "parliament_total": 0,
        "news_total": 0,
        "news_all": [],
        "news_sentiment_breakdown": {"positive": 0, "negative": 0, "neutral": 0},
        "schools_mentioned": [],
        "schools_mentioned_total": 0,
        "parliament_was_in_session": False,
        "parliament_sitting_count": 0,
    }
    base.update(overrides)
    return base


# A valid Gemini response per the 2026-07-05 prompt schema — no
# emerging_signals / fading_from_view (both retired after a repetition
# audit found they restated the top story).
_VALID_RESPONSE = (
    '{"executive_summary": "Quiet month.", '
    '"trend_lines": [{"trend": "Mentions declining", "direction": "down", "detail": "Down 20%."}], '
    '"opportunity_watch": ["MP X opened door."], '
    '"school_spotlight": {"name": "SJK(T) Ladang Bikam", "reason": "Most mentioned."}, '
    '"headline": "Special ed coming to Tamil schools in 2027"}'
)


@patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"})
class MonthlyAnalystTest(TestCase):
    @patch("broadcasts.services.monthly_analyst.aggregate_month")
    @patch("broadcasts.services.monthly_analyst.genai")
    def test_generates_analytical_content(self, mock_genai, mock_agg):
        mock_agg.return_value = _aggregate_stub()

        mock_response = Mock()
        mock_response.text = _VALID_RESPONSE
        mock_genai.Client.return_value.models.generate_content.return_value = mock_response

        result = generate_monthly_analysis(2026, 2)

        self.assertIn("executive_summary", result)
        self.assertIn("trend_lines", result)
        self.assertIn("opportunity_watch", result)
        self.assertIn("school_spotlight", result)
        self.assertIn("by_the_numbers", result)
        self.assertIn("headline", result)
        # Retired 2026-07-05 — must not resurface.
        self.assertNotIn("emerging_signals", result)
        self.assertNotIn("fading_from_view", result)

    @patch("broadcasts.services.monthly_analyst.aggregate_month")
    @patch("broadcasts.services.monthly_analyst.genai")
    def test_by_the_numbers_uses_real_db_counts_not_llm(self, mock_genai, mock_agg):
        """Sprint 23: by_the_numbers must come from aggregator counts, not LLM."""
        mock_agg.return_value = _aggregate_stub(
            parliament_total=3,
            news_total=46,
            schools_mentioned_total=29,
            news_sentiment_breakdown={"positive": 11, "negative": 4, "neutral": 31},
        )
        mock_response = Mock()
        mock_response.text = _VALID_RESPONSE
        mock_genai.Client.return_value.models.generate_content.return_value = mock_response

        result = generate_monthly_analysis(2026, 4)

        self.assertEqual(result["by_the_numbers"]["parliament_mentions"], 3)
        self.assertEqual(result["by_the_numbers"]["news_articles"], 46)
        self.assertEqual(result["by_the_numbers"]["schools_affected"], 29)
        self.assertEqual(result["by_the_numbers"]["sentiment_positive"], 11)
        self.assertEqual(result["by_the_numbers"]["sentiment_negative"], 4)

    @patch("broadcasts.services.monthly_analyst.aggregate_month")
    @patch("broadcasts.services.monthly_analyst.genai")
    def test_overlay_strips_any_llm_returned_by_the_numbers(self, mock_genai, mock_agg):
        """If the LLM returns by_the_numbers (off-spec), Python's count wins."""
        mock_agg.return_value = _aggregate_stub(news_total=42)
        mock_response = Mock()
        # LLM returns by_the_numbers with 999 — should be overwritten by 42.
        mock_response.text = (
            '{"executive_summary": "t", "trend_lines": [], '
            '"opportunity_watch": [], "school_spotlight": null, '
            '"headline": "Test headline", '
            '"by_the_numbers": {"news_articles": 999, "parliament_mentions": 999, '
            '"schools_affected": 999, "sentiment_positive": 999, "sentiment_negative": 999}}'
        )
        mock_genai.Client.return_value.models.generate_content.return_value = mock_response

        result = generate_monthly_analysis(2026, 4)

        self.assertEqual(result["by_the_numbers"]["news_articles"], 42)

    @patch("broadcasts.services.monthly_analyst.aggregate_month")
    @patch("broadcasts.services.monthly_analyst.genai")
    def test_returns_none_on_invalid_json(self, mock_genai, mock_agg):
        mock_agg.return_value = _aggregate_stub()
        mock_response = Mock()
        mock_response.text = "not json"
        mock_genai.Client.return_value.models.generate_content.return_value = mock_response
        result = generate_monthly_analysis(2026, 2)
        self.assertIsNone(result)

    @patch("broadcasts.services.monthly_analyst.aggregate_month")
    @patch("broadcasts.services.monthly_analyst.genai")
    def test_returns_none_on_missing_keys(self, mock_genai, mock_agg):
        mock_agg.return_value = _aggregate_stub()
        mock_response = Mock()
        # Missing "trend_lines" — required.
        mock_response.text = '{"executive_summary": "test"}'
        mock_genai.Client.return_value.models.generate_content.return_value = mock_response
        result = generate_monthly_analysis(2026, 2)
        self.assertIsNone(result)

    @patch("broadcasts.services.monthly_analyst.aggregate_month")
    @patch("broadcasts.services.monthly_analyst.genai")
    def test_compares_with_previous_month(self, mock_genai, mock_agg):
        """Should call aggregate_month twice - current and previous."""
        mock_agg.return_value = _aggregate_stub()
        mock_response = Mock()
        mock_response.text = _VALID_RESPONSE
        mock_genai.Client.return_value.models.generate_content.return_value = mock_response

        generate_monthly_analysis(2026, 2)
        # Should be called for Feb 2026 AND Jan 2026
        self.assertEqual(mock_agg.call_count, 2)

    @patch("broadcasts.services.monthly_analyst.aggregate_month")
    @patch("broadcasts.services.monthly_analyst.genai")
    def test_recess_clauses_present_in_all_sections(self, mock_genai, mock_agg):
        """Sprint 24 #1: recess instruction must appear in every section
        that produced false signals in the April 2026 render audit.
        Adjusted 2026-07-05 after emerging_signals + fading_from_view were
        retired — only trend_lines + opportunity_watch remain.
        """
        mock_agg.return_value = _aggregate_stub(parliament_was_in_session=False)
        mock_response = Mock()
        mock_response.text = _VALID_RESPONSE
        mock_genai.Client.return_value.models.generate_content.return_value = mock_response

        generate_monthly_analysis(2026, 4)

        call_kwargs = mock_genai.Client.return_value.models.generate_content.call_args.kwargs
        prompt = call_kwargs["contents"]

        # Session state must be wired through accurately.
        self.assertIn("Parliament was not in session", prompt)

        # Each of the remaining two sections must carry its own RECESS
        # clause. (The executive_summary clause uses a different phrasing:
        # "say so explicitly".)
        recess_clause_count = prompt.count("RECESS:")
        self.assertEqual(
            recess_clause_count, 2,
            f"Expected 2 RECESS clauses (trend_lines, opportunity_watch); "
            f"got {recess_clause_count}"
        )

        # Per-section anchor phrases — proves each section got its
        # tailored guidance, not just a generic copy-paste. Adjusted
        # 2026-07-05 after emerging_signals + fading_from_view were retired
        # and the prompt was reflowed with hard line breaks.
        self.assertIn('direction="up" or "down" for parliamentary attention', prompt)
        self.assertIn("MP outreach in constituencies IS a", prompt)
