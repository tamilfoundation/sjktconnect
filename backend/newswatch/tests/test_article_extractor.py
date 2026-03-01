from unittest.mock import MagicMock, patch

from django.test import TestCase

from newswatch.models import NewsArticle
from newswatch.services.article_extractor import (
    extract_article,
    extract_pending_articles,
)


class ExtractArticleTest(TestCase):
    def setUp(self):
        self.article = NewsArticle.objects.create(
            url="https://example.com/test-article",
            title="Test Article",
        )

    @patch("newswatch.services.article_extractor.trafilatura.extract_metadata")
    @patch("newswatch.services.article_extractor.trafilatura.extract")
    @patch("newswatch.services.article_extractor.trafilatura.fetch_url")
    def test_successful_extraction(self, mock_fetch, mock_extract, mock_meta):
        mock_fetch.return_value = "<html><body>Content</body></html>"
        mock_extract.return_value = "Article body text about Tamil schools."
        mock_meta.return_value = MagicMock(
            sitename="The Star", date="2026-03-01"
        )

        result = extract_article(self.article)
        result.refresh_from_db()

        self.assertEqual(result.status, NewsArticle.EXTRACTED)
        self.assertEqual(result.body_text, "Article body text about Tamil schools.")
        self.assertEqual(result.source_name, "The Star")
        self.assertIsNotNone(result.published_date)

    @patch("newswatch.services.article_extractor.trafilatura.fetch_url")
    def test_download_failure(self, mock_fetch):
        mock_fetch.return_value = None

        result = extract_article(self.article)
        result.refresh_from_db()

        self.assertEqual(result.status, NewsArticle.FAILED)
        self.assertIn("Failed to download", result.extraction_error)

    @patch("newswatch.services.article_extractor.trafilatura.extract_metadata")
    @patch("newswatch.services.article_extractor.trafilatura.extract")
    @patch("newswatch.services.article_extractor.trafilatura.fetch_url")
    def test_no_text_extracted(self, mock_fetch, mock_extract, mock_meta):
        mock_fetch.return_value = "<html></html>"
        mock_extract.return_value = None
        mock_meta.return_value = MagicMock(sitename=None, date=None)

        result = extract_article(self.article)
        result.refresh_from_db()

        self.assertEqual(result.status, NewsArticle.FAILED)
        self.assertIn("No text content", result.extraction_error)

    @patch("newswatch.services.article_extractor.trafilatura.fetch_url")
    def test_exception_handled(self, mock_fetch):
        mock_fetch.side_effect = ConnectionError("Network error")

        result = extract_article(self.article)
        result.refresh_from_db()

        self.assertEqual(result.status, NewsArticle.FAILED)
        self.assertIn("Network error", result.extraction_error)

    @patch("newswatch.services.article_extractor.trafilatura.extract_metadata")
    @patch("newswatch.services.article_extractor.trafilatura.extract")
    @patch("newswatch.services.article_extractor.trafilatura.fetch_url")
    def test_preserves_existing_published_date(
        self, mock_fetch, mock_extract, mock_meta
    ):
        """If article already has a published_date from RSS, don't overwrite."""
        from datetime import datetime, timezone

        self.article.published_date = datetime(2026, 2, 1, tzinfo=timezone.utc)
        self.article.save()

        mock_fetch.return_value = "<html><body>Text</body></html>"
        mock_extract.return_value = "Some text."
        mock_meta.return_value = MagicMock(
            sitename="Star", date="2026-03-15"
        )

        result = extract_article(self.article)
        result.refresh_from_db()

        self.assertEqual(result.published_date.month, 2)  # Kept original

    @patch("newswatch.services.article_extractor.trafilatura.extract_metadata")
    @patch("newswatch.services.article_extractor.trafilatura.extract")
    @patch("newswatch.services.article_extractor.trafilatura.fetch_url")
    def test_no_metadata_still_extracts(
        self, mock_fetch, mock_extract, mock_meta
    ):
        mock_fetch.return_value = "<html><body>Text</body></html>"
        mock_extract.return_value = "Article content here."
        mock_meta.return_value = None

        result = extract_article(self.article)
        result.refresh_from_db()

        self.assertEqual(result.status, NewsArticle.EXTRACTED)
        self.assertEqual(result.body_text, "Article content here.")
        self.assertEqual(result.source_name, "")


class ExtractPendingArticlesTest(TestCase):
    @patch("newswatch.services.article_extractor.trafilatura.extract_metadata")
    @patch("newswatch.services.article_extractor.trafilatura.extract")
    @patch("newswatch.services.article_extractor.trafilatura.fetch_url")
    def test_processes_new_articles_only(
        self, mock_fetch, mock_extract, mock_meta
    ):
        NewsArticle.objects.create(
            url="https://example.com/new-1", title="New 1"
        )
        NewsArticle.objects.create(
            url="https://example.com/new-2", title="New 2"
        )
        NewsArticle.objects.create(
            url="https://example.com/done",
            title="Already Done",
            status=NewsArticle.EXTRACTED,
        )

        mock_fetch.return_value = "<html>content</html>"
        mock_extract.return_value = "Extracted text."
        mock_meta.return_value = MagicMock(sitename=None, date=None)

        result = extract_pending_articles()

        self.assertEqual(result["total"], 2)
        self.assertEqual(result["extracted"], 2)
        self.assertEqual(result["failed"], 0)

    def test_empty_batch(self):
        result = extract_pending_articles()
        self.assertEqual(result["total"], 0)
        self.assertEqual(result["extracted"], 0)

    @patch("newswatch.services.article_extractor.trafilatura.extract_metadata")
    @patch("newswatch.services.article_extractor.trafilatura.extract")
    @patch("newswatch.services.article_extractor.trafilatura.fetch_url")
    def test_respects_batch_size(self, mock_fetch, mock_extract, mock_meta):
        for i in range(5):
            NewsArticle.objects.create(
                url=f"https://example.com/batch-{i}", title=f"Article {i}"
            )

        mock_fetch.return_value = "<html>content</html>"
        mock_extract.return_value = "Text."
        mock_meta.return_value = MagicMock(sitename=None, date=None)

        result = extract_pending_articles(batch_size=3)

        self.assertEqual(result["total"], 3)
