"""Tests for newswatch.services.news_analyser."""

import json
from unittest.mock import MagicMock, patch

from django.test import TestCase

from newswatch.models import NewsArticle
from newswatch.services.news_analyser import (
    _build_body,
    _validate_response,
    analyse_article,
    analyse_pending_articles,
    apply_analysis,
)


class BuildBodyTest(TestCase):
    def test_short_body_unchanged(self):
        article = NewsArticle(body_text="Short article text.")
        result = _build_body(article)
        self.assertEqual(result, "Short article text.")

    def test_long_body_truncated(self):
        article = NewsArticle(body_text="A" * 5000)
        result = _build_body(article)
        self.assertEqual(len(result), 3003)  # 3000 + "..."
        self.assertTrue(result.endswith("..."))

    def test_whitespace_stripped(self):
        article = NewsArticle(body_text="  leading and trailing  ")
        result = _build_body(article)
        self.assertEqual(result, "leading and trailing")


class ValidateResponseTest(TestCase):
    def test_valid_response(self):
        data = {
            "relevance_score": 4,
            "sentiment": "POSITIVE",
            "summary": "Good news for Tamil schools.",
            "mentioned_schools": [{"name": "SJK(T) Ladang Bikam", "moe_code": ""}],
            "is_urgent": False,
            "urgent_reason": "",
        }
        result = _validate_response(data)
        self.assertEqual(result["relevance_score"], 4)
        self.assertEqual(result["sentiment"], "POSITIVE")
        self.assertFalse(result["is_urgent"])

    def test_clamps_invalid_sentiment(self):
        data = {"sentiment": "HAPPY"}
        result = _validate_response(data)
        self.assertEqual(result["sentiment"], "NEUTRAL")

    def test_clamps_relevance_score(self):
        data = {"relevance_score": 10}
        result = _validate_response(data)
        self.assertEqual(result["relevance_score"], 5)

        data = {"relevance_score": -1}
        result = _validate_response(data)
        self.assertEqual(result["relevance_score"], 1)

    def test_invalid_relevance_defaults_to_1(self):
        data = {"relevance_score": "not a number"}
        result = _validate_response(data)
        self.assertEqual(result["relevance_score"], 1)

    def test_missing_fields_get_defaults(self):
        result = _validate_response({})
        self.assertEqual(result["relevance_score"], 1)
        self.assertEqual(result["sentiment"], "NEUTRAL")
        self.assertEqual(result["summary"], "")
        self.assertEqual(result["mentioned_schools"], [])
        self.assertFalse(result["is_urgent"])
        self.assertEqual(result["urgent_reason"], "")

    def test_urgent_reason_cleared_when_not_urgent(self):
        data = {"is_urgent": False, "urgent_reason": "Some leftover reason"}
        result = _validate_response(data)
        self.assertEqual(result["urgent_reason"], "")

    def test_mentioned_schools_not_list_defaults_to_empty(self):
        data = {"mentioned_schools": "not a list"}
        result = _validate_response(data)
        self.assertEqual(result["mentioned_schools"], [])


class AnalyseArticleTest(TestCase):
    def setUp(self):
        self.article = NewsArticle.objects.create(
            url="https://example.com/analyse-test",
            title="Tamil school funding boost",
            body_text="The government announced RM10 million for Tamil schools.",
            status=NewsArticle.EXTRACTED,
        )

    @patch("newswatch.services.news_analyser._get_client")
    def test_successful_analysis(self, mock_get_client):
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "relevance_score": 5,
            "sentiment": "POSITIVE",
            "summary": "RM10m funding for Tamil schools.",
            "mentioned_schools": [],
            "is_urgent": False,
            "urgent_reason": "",
        })
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mock_get_client.return_value = mock_client

        result = analyse_article(self.article)

        self.assertIsNotNone(result)
        self.assertEqual(result["relevance_score"], 5)
        self.assertEqual(result["sentiment"], "POSITIVE")
        self.assertIn("raw_response", result)

    @patch("newswatch.services.news_analyser._get_client")
    def test_api_failure_returns_none(self, mock_get_client):
        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = Exception("API error")
        mock_get_client.return_value = mock_client

        result = analyse_article(self.article)
        self.assertIsNone(result)

    @patch("newswatch.services.news_analyser._get_client")
    def test_invalid_json_returns_none(self, mock_get_client):
        mock_response = MagicMock()
        mock_response.text = "not valid json"
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mock_get_client.return_value = mock_client

        result = analyse_article(self.article)
        self.assertIsNone(result)


class ApplyAnalysisTest(TestCase):
    def test_apply_sets_fields_and_status(self):
        article = NewsArticle.objects.create(
            url="https://example.com/apply-test",
            title="Test",
            body_text="Some body text.",
            status=NewsArticle.EXTRACTED,
        )
        analysis = {
            "relevance_score": 3,
            "sentiment": "MIXED",
            "summary": "A mixed report.",
            "mentioned_schools": [{"name": "SJK(T) Test", "moe_code": "ABC1234"}],
            "is_urgent": True,
            "urgent_reason": "School closure mentioned.",
            "raw_response": {"relevance_score": 3},
        }

        apply_analysis(article, analysis)
        article.refresh_from_db()

        self.assertEqual(article.status, NewsArticle.ANALYSED)
        self.assertEqual(article.relevance_score, 3)
        self.assertEqual(article.sentiment, "MIXED")
        self.assertEqual(article.ai_summary, "A mixed report.")
        self.assertEqual(len(article.mentioned_schools), 1)
        self.assertTrue(article.is_urgent)
        self.assertEqual(article.urgent_reason, "School closure mentioned.")


class AutoApproveTest(TestCase):
    """Test auto-approve logic in apply_analysis."""

    def test_high_relevance_auto_approved(self):
        article = NewsArticle.objects.create(
            url="https://example.com/auto-approve-high",
            title="Relevant article",
            body_text="Article about Tamil school.",
            status=NewsArticle.EXTRACTED,
        )
        analysis = {
            "relevance_score": 4,
            "sentiment": "POSITIVE",
            "summary": "Good news.",
            "mentioned_schools": [],
            "is_urgent": False,
            "urgent_reason": "",
            "raw_response": {},
        }
        apply_analysis(article, analysis)
        article.refresh_from_db()
        assert article.review_status == "APPROVED"

    def test_relevance_3_auto_approved(self):
        article = NewsArticle.objects.create(
            url="https://example.com/auto-approve-3",
            title="Moderately relevant",
            body_text="Some text.",
            status=NewsArticle.EXTRACTED,
        )
        analysis = {
            "relevance_score": 3,
            "sentiment": "NEUTRAL",
            "summary": "Moderate relevance.",
            "mentioned_schools": [],
            "is_urgent": False,
            "urgent_reason": "",
            "raw_response": {},
        }
        apply_analysis(article, analysis)
        article.refresh_from_db()
        assert article.review_status == "APPROVED"

    def test_low_relevance_stays_pending(self):
        article = NewsArticle.objects.create(
            url="https://example.com/auto-approve-low",
            title="Irrelevant article",
            body_text="Not about Tamil schools.",
            status=NewsArticle.EXTRACTED,
        )
        analysis = {
            "relevance_score": 2,
            "sentiment": "NEUTRAL",
            "summary": "Not relevant.",
            "mentioned_schools": [],
            "is_urgent": False,
            "urgent_reason": "",
            "raw_response": {},
        }
        apply_analysis(article, analysis)
        article.refresh_from_db()
        assert article.review_status == "PENDING"

    def test_relevance_1_stays_pending(self):
        article = NewsArticle.objects.create(
            url="https://example.com/auto-approve-1",
            title="Completely irrelevant",
            body_text="Unrelated content.",
            status=NewsArticle.EXTRACTED,
        )
        analysis = {
            "relevance_score": 1,
            "sentiment": "NEUTRAL",
            "summary": "Irrelevant.",
            "mentioned_schools": [],
            "is_urgent": False,
            "urgent_reason": "",
            "raw_response": {},
        }
        apply_analysis(article, analysis)
        article.refresh_from_db()
        assert article.review_status == "PENDING"


class AnalysePendingArticlesTest(TestCase):
    @patch("newswatch.services.news_analyser.analyse_article")
    def test_analyses_extracted_articles(self, mock_analyse):
        a1 = NewsArticle.objects.create(
            url="https://example.com/pending-1",
            title="Article 1",
            body_text="Body text 1.",
            status=NewsArticle.EXTRACTED,
        )
        # NEW article should NOT be picked up
        NewsArticle.objects.create(
            url="https://example.com/pending-2",
            title="Article 2",
            status=NewsArticle.NEW,
        )

        mock_analyse.return_value = {
            "relevance_score": 4,
            "sentiment": "POSITIVE",
            "summary": "Good news.",
            "mentioned_schools": [],
            "is_urgent": False,
            "urgent_reason": "",
            "raw_response": {},
        }

        counts = analyse_pending_articles(batch_size=10)

        self.assertEqual(counts["analysed"], 1)
        self.assertEqual(counts["failed"], 0)
        mock_analyse.assert_called_once()
        a1.refresh_from_db()
        self.assertEqual(a1.status, NewsArticle.ANALYSED)

    @patch("newswatch.services.news_analyser.analyse_article")
    def test_skips_empty_body(self, mock_analyse):
        NewsArticle.objects.create(
            url="https://example.com/empty-body",
            title="Empty body",
            body_text="",
            status=NewsArticle.EXTRACTED,
        )

        counts = analyse_pending_articles(batch_size=10)

        self.assertEqual(counts["skipped"], 1)
        self.assertEqual(counts["analysed"], 0)
        mock_analyse.assert_not_called()

    @patch("newswatch.services.news_analyser.analyse_article")
    def test_counts_failures(self, mock_analyse):
        NewsArticle.objects.create(
            url="https://example.com/fail",
            title="Fail",
            body_text="Some text.",
            status=NewsArticle.EXTRACTED,
        )
        mock_analyse.return_value = None

        counts = analyse_pending_articles(batch_size=10)

        self.assertEqual(counts["failed"], 1)
        self.assertEqual(counts["analysed"], 0)

    @patch("newswatch.services.news_analyser.analyse_article")
    def test_respects_batch_size(self, mock_analyse):
        for i in range(5):
            NewsArticle.objects.create(
                url=f"https://example.com/batch-{i}",
                title=f"Article {i}",
                body_text="Some text.",
                status=NewsArticle.EXTRACTED,
            )

        mock_analyse.return_value = {
            "relevance_score": 3,
            "sentiment": "NEUTRAL",
            "summary": "Summary.",
            "mentioned_schools": [],
            "is_urgent": False,
            "urgent_reason": "",
            "raw_response": {},
        }

        counts = analyse_pending_articles(batch_size=2)

        self.assertEqual(counts["analysed"], 2)
        self.assertEqual(mock_analyse.call_count, 2)
