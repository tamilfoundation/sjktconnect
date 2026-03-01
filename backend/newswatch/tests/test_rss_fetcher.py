from datetime import datetime, timezone
from time import mktime
from unittest.mock import MagicMock, patch

from django.test import TestCase

from newswatch.models import NewsArticle
from newswatch.services.rss_fetcher import (
    _clean_title,
    _parse_published_date,
    _resolve_url,
    fetch_news_from_rss,
)


class CleanTitleTest(TestCase):
    def test_removes_bold_tags(self):
        self.assertEqual(_clean_title("<b>Tamil</b> schools"), "Tamil schools")

    def test_removes_multiple_tags(self):
        self.assertEqual(
            _clean_title("<b>SJKT</b> in <i>Malaysia</i>"),
            "SJKT in Malaysia",
        )

    def test_plain_text_unchanged(self):
        self.assertEqual(_clean_title("No tags here"), "No tags here")

    def test_strips_whitespace(self):
        self.assertEqual(_clean_title("  spaced  "), "spaced")


class ResolveUrlTest(TestCase):
    def test_direct_url(self):
        entry = MagicMock()
        entry.link = "https://example.com/article"
        self.assertEqual(_resolve_url(entry), "https://example.com/article")

    def test_google_redirect_url(self):
        entry = MagicMock()
        entry.link = (
            "https://www.google.com/url?rct=j&sa=t"
            "&url=https%3A%2F%2Fexample.com%2Freal-article"
            "&ct=ga&cd=abc"
        )
        self.assertEqual(
            _resolve_url(entry), "https://example.com/real-article"
        )

    def test_empty_link(self):
        entry = MagicMock()
        entry.link = ""
        self.assertEqual(_resolve_url(entry), "")

    def test_no_link_attribute(self):
        entry = MagicMock(spec=[])  # No attributes
        self.assertEqual(_resolve_url(entry), "")


class ParsePublishedDateTest(TestCase):
    def test_published_parsed(self):
        entry = MagicMock()
        entry.published_parsed = datetime(2026, 3, 1, 12, 0, 0).timetuple()
        entry.updated_parsed = None
        result = _parse_published_date(entry)
        self.assertIsNotNone(result)
        self.assertEqual(result.year, 2026)
        self.assertEqual(result.tzinfo, timezone.utc)

    def test_falls_back_to_updated(self):
        entry = MagicMock()
        entry.published_parsed = None
        entry.updated_parsed = datetime(2026, 2, 15, 8, 0, 0).timetuple()
        result = _parse_published_date(entry)
        self.assertIsNotNone(result)
        self.assertEqual(result.month, 2)

    def test_no_date_returns_none(self):
        entry = MagicMock()
        entry.published_parsed = None
        entry.updated_parsed = None
        self.assertIsNone(_parse_published_date(entry))


class FetchNewsFromRssTest(TestCase):
    def test_empty_url_returns_error(self):
        result = fetch_news_from_rss("")
        self.assertEqual(result["errors"], ["No RSS URL provided."])
        self.assertEqual(result["created"], [])

    @patch("newswatch.services.rss_fetcher.feedparser.parse")
    def test_creates_new_articles(self, mock_parse):
        entry = MagicMock()
        entry.link = "https://example.com/news-1"
        entry.title = "<b>Tamil</b> school news"
        entry.published_parsed = datetime(2026, 3, 1).timetuple()

        mock_parse.return_value = MagicMock(
            bozo=False,
            entries=[entry],
            feed=MagicMock(title="Google Alerts - SJKT"),
        )

        result = fetch_news_from_rss("https://alerts.google.com/feed")
        self.assertEqual(len(result["created"]), 1)
        self.assertEqual(result["skipped"], 0)
        self.assertEqual(result["created"][0].title, "Tamil school news")
        self.assertEqual(result["created"][0].alert_title, "Google Alerts - SJKT")

    @patch("newswatch.services.rss_fetcher.feedparser.parse")
    def test_skips_existing_urls(self, mock_parse):
        NewsArticle.objects.create(
            url="https://example.com/existing",
            title="Existing Article",
        )

        entry = MagicMock()
        entry.link = "https://example.com/existing"
        entry.title = "Same article"
        entry.published_parsed = None
        entry.updated_parsed = None

        mock_parse.return_value = MagicMock(
            bozo=False,
            entries=[entry],
            feed=MagicMock(title="Alerts"),
        )

        result = fetch_news_from_rss("https://alerts.google.com/feed")
        self.assertEqual(len(result["created"]), 0)
        self.assertEqual(result["skipped"], 1)

    @patch("newswatch.services.rss_fetcher.feedparser.parse")
    def test_deduplicates_within_same_feed(self, mock_parse):
        entry1 = MagicMock()
        entry1.link = "https://example.com/dup"
        entry1.title = "Article"
        entry1.published_parsed = None
        entry1.updated_parsed = None

        entry2 = MagicMock()
        entry2.link = "https://example.com/dup"
        entry2.title = "Article again"
        entry2.published_parsed = None
        entry2.updated_parsed = None

        mock_parse.return_value = MagicMock(
            bozo=False,
            entries=[entry1, entry2],
            feed=MagicMock(title="Alerts"),
        )

        result = fetch_news_from_rss("https://alerts.google.com/feed")
        self.assertEqual(len(result["created"]), 1)
        self.assertEqual(result["skipped"], 1)

    @patch("newswatch.services.rss_fetcher.feedparser.parse")
    def test_bozo_feed_with_no_entries(self, mock_parse):
        mock_parse.return_value = MagicMock(
            bozo=True,
            entries=[],
            bozo_exception=Exception("XML error"),
        )

        result = fetch_news_from_rss("https://bad-feed.com")
        self.assertEqual(len(result["errors"]), 1)
        self.assertIn("Feed parse error", result["errors"][0])
