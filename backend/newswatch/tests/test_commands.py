from unittest.mock import patch

from django.test import TestCase
from django.core.management import call_command
from io import StringIO

from newswatch.models import NewsArticle


class FetchNewsAlertsCommandTest(TestCase):
    @patch("newswatch.management.commands.fetch_news_alerts.fetch_news_from_rss")
    def test_with_url_flag(self, mock_fetch):
        mock_fetch.return_value = {
            "created": [NewsArticle(title="Test")],
            "skipped": 0,
            "errors": [],
        }

        out = StringIO()
        call_command("fetch_news_alerts", "--url", "https://feed.example.com", stdout=out)

        mock_fetch.assert_called_once_with("https://feed.example.com")
        self.assertIn("Created: 1", out.getvalue())

    def test_no_urls_configured(self):
        out = StringIO()
        err = StringIO()
        call_command("fetch_news_alerts", stdout=out, stderr=err)
        self.assertIn("No RSS feed URLs configured", err.getvalue())

    @patch("newswatch.management.commands.fetch_news_alerts.fetch_news_from_rss")
    @patch(
        "newswatch.management.commands.fetch_news_alerts.settings",
    )
    def test_uses_settings_feeds(self, mock_settings, mock_fetch):
        mock_settings.NEWS_WATCH_RSS_FEEDS = [
            "https://feed1.example.com",
            "https://feed2.example.com",
        ]
        mock_fetch.return_value = {
            "created": [],
            "skipped": 2,
            "errors": [],
        }

        out = StringIO()
        call_command("fetch_news_alerts", stdout=out)

        self.assertEqual(mock_fetch.call_count, 2)


class ExtractArticlesCommandTest(TestCase):
    @patch(
        "newswatch.management.commands.extract_articles.extract_pending_articles"
    )
    def test_default_batch_size(self, mock_extract):
        mock_extract.return_value = {
            "extracted": 3,
            "failed": 1,
            "total": 4,
        }

        out = StringIO()
        call_command("extract_articles", stdout=out)

        mock_extract.assert_called_once_with(batch_size=20)
        self.assertIn("Extracted: 3", out.getvalue())

    @patch(
        "newswatch.management.commands.extract_articles.extract_pending_articles"
    )
    def test_custom_batch_size(self, mock_extract):
        mock_extract.return_value = {
            "extracted": 5,
            "failed": 0,
            "total": 5,
        }

        out = StringIO()
        call_command("extract_articles", "--batch-size", "50", stdout=out)

        mock_extract.assert_called_once_with(batch_size=50)


class AnalyseNewsArticlesCommandTest(TestCase):
    @patch(
        "newswatch.management.commands.analyse_news_articles.analyse_pending_articles"
    )
    def test_default_batch_size(self, mock_analyse):
        mock_analyse.return_value = {
            "analysed": 3,
            "failed": 0,
            "skipped": 1,
        }

        out = StringIO()
        call_command("analyse_news_articles", stdout=out)

        mock_analyse.assert_called_once_with(batch_size=10)
        self.assertIn("Analysed: 3", out.getvalue())

    @patch(
        "newswatch.management.commands.analyse_news_articles.analyse_pending_articles"
    )
    def test_custom_batch_size(self, mock_analyse):
        mock_analyse.return_value = {
            "analysed": 5,
            "failed": 0,
            "skipped": 0,
        }

        out = StringIO()
        call_command("analyse_news_articles", "--batch-size", "25", stdout=out)

        mock_analyse.assert_called_once_with(batch_size=25)

    @patch(
        "newswatch.management.commands.analyse_news_articles.analyse_pending_articles"
    )
    def test_warns_about_urgent(self, mock_analyse):
        # Create an urgent pending article
        NewsArticle.objects.create(
            url="https://example.com/urgent-cmd",
            title="Urgent",
            status=NewsArticle.ANALYSED,
            is_urgent=True,
            review_status=NewsArticle.PENDING,
        )

        mock_analyse.return_value = {
            "analysed": 1,
            "failed": 0,
            "skipped": 0,
        }

        out = StringIO()
        call_command("analyse_news_articles", stdout=out)

        self.assertIn("URGENT", out.getvalue())
