from datetime import timedelta
from io import StringIO
from unittest.mock import Mock, patch

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from broadcasts.models import Broadcast
from newswatch.models import NewsArticle


@patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"})
class ComposeNewsDigestTest(TestCase):
    def setUp(self):
        now = timezone.now()
        NewsArticle.objects.create(
            url="https://example.com/story",
            title="Tamil school gets new building",
            source_name="The Star",
            published_date=now - timedelta(days=3),
            body_text="A Tamil school received funding.",
            status=NewsArticle.ANALYSED,
            relevance_score=5,
            sentiment="POSITIVE",
            ai_summary="A Tamil school received new infrastructure funding.",
            review_status=NewsArticle.APPROVED,
        )

    @patch("broadcasts.services.news_digest.genai")
    def test_creates_draft_broadcast(self, mock_genai):
        mock_response = Mock()
        mock_response.text = (
            '{"editors_note": "Good news.", "big_story": {"title": "New building",'
            ' "url": "https://example.com/story", "source": "The Star",'
            ' "summary": "Funding.", "why_it_matters": "Progress."},'
            ' "in_brief": [], "the_number": {"number": "1",'
            ' "context": "school funded."}, "worth_knowing": null}'
        )
        mock_genai.Client.return_value.models.generate_content.return_value = (
            mock_response
        )

        out = StringIO()
        call_command("compose_news_digest", stdout=out)

        broadcast = Broadcast.objects.first()
        self.assertIsNotNone(broadcast)
        self.assertEqual(broadcast.status, Broadcast.Status.DRAFT)
        self.assertIn("News Watch", broadcast.subject)
        self.assertEqual(broadcast.audience_filter, {"category": "NEWS_WATCH"})

    def test_skips_if_no_articles(self):
        NewsArticle.objects.all().delete()
        out = StringIO()
        call_command("compose_news_digest", stdout=out)
        self.assertEqual(Broadcast.objects.count(), 0)

    @patch("broadcasts.services.news_digest.genai")
    def test_dry_run(self, mock_genai):
        mock_response = Mock()
        mock_response.text = (
            '{"editors_note": "Test.", "big_story": {"title": "T", "url": "u",'
            ' "source": "s", "summary": "s", "why_it_matters": "w"},'
            ' "in_brief": [], "the_number": {"number": "1", "context": "c"},'
            ' "worth_knowing": null}'
        )
        mock_genai.Client.return_value.models.generate_content.return_value = (
            mock_response
        )

        out = StringIO()
        call_command("compose_news_digest", "--dry-run", stdout=out)
        self.assertEqual(Broadcast.objects.count(), 0)
        self.assertIn("DRY RUN", out.getvalue())
