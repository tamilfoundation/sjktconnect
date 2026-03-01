from django.db import IntegrityError
from django.test import TestCase

from newswatch.models import NewsArticle


class NewsArticleModelTest(TestCase):
    def test_create_article(self):
        article = NewsArticle.objects.create(
            url="https://example.com/article-1",
            title="Test Article",
        )
        self.assertEqual(article.status, NewsArticle.NEW)
        self.assertEqual(article.body_text, "")
        self.assertEqual(article.source_name, "")
        self.assertIsNotNone(article.created_at)

    def test_url_unique(self):
        NewsArticle.objects.create(
            url="https://example.com/unique",
            title="First",
        )
        with self.assertRaises(IntegrityError):
            NewsArticle.objects.create(
                url="https://example.com/unique",
                title="Duplicate",
            )

    def test_str_representation(self):
        article = NewsArticle.objects.create(
            url="https://example.com/str-test",
            title="A very long title that should be truncated in the string representation of this model",
        )
        text = str(article)
        self.assertIn("(NEW)", text)
        self.assertTrue(len(text.split(" (")[0]) <= 80)

    def test_default_ordering_is_newest_first(self):
        """Meta ordering is -created_at (newest first)."""
        self.assertEqual(
            NewsArticle._meta.ordering, ["-created_at"]
        )

    def test_status_choices(self):
        article = NewsArticle.objects.create(
            url="https://example.com/status",
            title="Status Test",
        )
        article.status = NewsArticle.EXTRACTED
        article.save()
        article.refresh_from_db()
        self.assertEqual(article.status, "EXTRACTED")

    def test_optional_fields_default_blank(self):
        article = NewsArticle.objects.create(
            url="https://example.com/defaults",
            title="Defaults",
        )
        self.assertEqual(article.source_name, "")
        self.assertEqual(article.alert_title, "")
        self.assertEqual(article.body_text, "")
        self.assertEqual(article.extraction_error, "")
        self.assertIsNone(article.published_date)
