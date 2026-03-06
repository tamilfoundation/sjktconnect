from datetime import date, timedelta
from unittest.mock import patch, Mock
from django.test import TestCase
from newswatch.models import NewsArticle
from broadcasts.services.news_digest import generate_news_digest


class NewsDigestTest(TestCase):
    def setUp(self):
        today = date.today()
        for i in range(6):
            NewsArticle.objects.create(
                url=f"https://example.com/article-{i}",
                title=f"Article {i} about Tamil schools",
                source_name="The Star",
                published_date=today - timedelta(days=i),
                body_text=f"Body text for article {i}.",
                status=NewsArticle.ANALYSED,
                relevance_score=5 - i,
                sentiment="POSITIVE" if i % 2 == 0 else "NEGATIVE",
                ai_summary=f"Summary of article {i}.",
                review_status=NewsArticle.APPROVED,
            )

    @patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"})
    @patch("broadcasts.services.news_digest.genai")
    def test_generates_economist_style_content(self, mock_genai):
        mock_response = Mock()
        mock_response.text = '{"editors_note": "A busy fortnight.", "big_story": {"title": "Article 0", "url": "https://example.com/article-0", "source": "The Star", "summary": "Important.", "why_it_matters": "Because."}, "in_brief": [{"title": "Article 1", "url": "https://example.com/article-1", "source": "The Star", "sentiment": "negative", "one_liner": "Brief."}], "the_number": {"number": "5", "context": "schools mentioned."}, "worth_knowing": "Hidden gem."}'
        mock_genai.Client.return_value.models.generate_content.return_value = mock_response

        result = generate_news_digest()

        self.assertIn("editors_note", result)
        self.assertIn("big_story", result)
        self.assertIn("in_brief", result)
        self.assertIn("the_number", result)

    def test_returns_none_if_no_articles(self):
        NewsArticle.objects.all().delete()
        result = generate_news_digest()
        self.assertIsNone(result)

    @patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"})
    @patch("broadcasts.services.news_digest.genai")
    def test_returns_none_on_invalid_json(self, mock_genai):
        mock_response = Mock()
        mock_response.text = "not json"
        mock_genai.Client.return_value.models.generate_content.return_value = mock_response

        result = generate_news_digest()
        self.assertIsNone(result)

    @patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"})
    @patch("broadcasts.services.news_digest.genai")
    def test_returns_none_on_missing_keys(self, mock_genai):
        mock_response = Mock()
        mock_response.text = '{"editors_note": "test"}'
        mock_genai.Client.return_value.models.generate_content.return_value = mock_response

        result = generate_news_digest()
        self.assertIsNone(result)

    def test_custom_days_parameter(self):
        """Only recent articles should be included."""
        result = generate_news_digest(days=0)
        self.assertIsNone(result)
