"""Tests for the urgent alert service and compose command."""

from datetime import timedelta
from io import StringIO
from unittest.mock import Mock, patch

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from broadcasts.models import Broadcast
from broadcasts.services.urgent_alert import generate_urgent_alert
from newswatch.models import NewsArticle


@patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"})
class UrgentAlertServiceTest(TestCase):
    def setUp(self):
        self.article = NewsArticle.objects.create(
            url="https://example.com/closure",
            title="Tamil school in Perak faces closure",
            source_name="Malay Mail",
            published_date=timezone.now() - timedelta(hours=2),
            body_text="SJK(T) Ladang Bikam faces closure due to low enrolment.",
            status=NewsArticle.ANALYSED,
            relevance_score=5,
            sentiment="NEGATIVE",
            ai_summary="SJK(T) Ladang Bikam in Perak faces closure threat.",
            is_urgent=True,
            urgent_reason="School closure threat",
            review_status=NewsArticle.APPROVED,
        )

    @patch("broadcasts.services.urgent_alert.genai")
    def test_generates_alert_content(self, mock_genai):
        mock_response = Mock()
        mock_response.text = (
            '{"what_happened": "SJK(T) Ladang Bikam faces closure.", '
            '"who_affected": "28 students and 6 teachers.", '
            '"what_you_can_do": "Write to Pengarah Pendidikan Negeri Perak.", '
            '"deadline": "20 March 2026"}'
        )
        mock_genai.Client.return_value.models.generate_content.return_value = (
            mock_response
        )

        result = generate_urgent_alert(self.article)
        self.assertIn("what_happened", result)
        self.assertIn("what_you_can_do", result)
        self.assertIn("deadline", result)

    def test_returns_none_if_not_urgent(self):
        self.article.is_urgent = False
        self.article.save()
        result = generate_urgent_alert(self.article)
        self.assertIsNone(result)

    @patch("broadcasts.services.urgent_alert.genai")
    def test_returns_none_on_invalid_json(self, mock_genai):
        mock_response = Mock()
        mock_response.text = "not json"
        mock_genai.Client.return_value.models.generate_content.return_value = (
            mock_response
        )
        result = generate_urgent_alert(self.article)
        self.assertIsNone(result)

    @patch("broadcasts.services.urgent_alert.genai")
    def test_returns_none_on_missing_keys(self, mock_genai):
        mock_response = Mock()
        mock_response.text = '{"what_happened": "Something."}'
        mock_genai.Client.return_value.models.generate_content.return_value = (
            mock_response
        )
        result = generate_urgent_alert(self.article)
        self.assertIsNone(result)

    @patch("broadcasts.services.urgent_alert.genai")
    def test_returns_none_on_api_error(self, mock_genai):
        mock_genai.Client.return_value.models.generate_content.side_effect = (
            RuntimeError("API down")
        )
        result = generate_urgent_alert(self.article)
        self.assertIsNone(result)

    def test_returns_none_if_not_approved(self):
        self.article.review_status = NewsArticle.PENDING
        self.article.save()
        result = generate_urgent_alert(self.article)
        self.assertIsNone(result)


@patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"})
class ComposeUrgentAlertTest(TestCase):
    def setUp(self):
        self.article = NewsArticle.objects.create(
            url="https://example.com/closure",
            title="School closure threat",
            source_name="The Star",
            published_date=timezone.now() - timedelta(hours=1),
            body_text="Body.",
            status=NewsArticle.ANALYSED,
            relevance_score=5,
            sentiment="NEGATIVE",
            ai_summary="Closure threat.",
            is_urgent=True,
            urgent_reason="Closure",
            review_status=NewsArticle.APPROVED,
        )

    @patch("broadcasts.services.urgent_alert.genai")
    def test_creates_draft_broadcast(self, mock_genai):
        mock_response = Mock()
        mock_response.text = (
            '{"what_happened": "Closure.", '
            '"who_affected": "Students.", '
            '"what_you_can_do": "Act now.", '
            '"deadline": null}'
        )
        mock_genai.Client.return_value.models.generate_content.return_value = (
            mock_response
        )

        out = StringIO()
        call_command(
            "compose_urgent_alert",
            "--article-id",
            str(self.article.pk),
            stdout=out,
        )

        broadcast = Broadcast.objects.first()
        self.assertIsNotNone(broadcast)
        self.assertIn("URGENT", broadcast.subject)
        self.assertEqual(broadcast.audience_filter, {"category": "NEWS_WATCH"})
        self.assertEqual(broadcast.status, Broadcast.Status.DRAFT)

    def test_fails_if_not_urgent(self):
        self.article.is_urgent = False
        self.article.save()
        err = StringIO()
        call_command(
            "compose_urgent_alert",
            "--article-id",
            str(self.article.pk),
            stderr=err,
        )
        self.assertEqual(Broadcast.objects.count(), 0)

    def test_fails_if_article_not_found(self):
        err = StringIO()
        call_command(
            "compose_urgent_alert",
            "--article-id",
            "99999",
            stderr=err,
        )
        self.assertEqual(Broadcast.objects.count(), 0)

    @patch("broadcasts.services.urgent_alert.genai")
    def test_dry_run(self, mock_genai):
        mock_response = Mock()
        mock_response.text = (
            '{"what_happened": "Test.", '
            '"who_affected": "Test.", '
            '"what_you_can_do": "Test.", '
            '"deadline": null}'
        )
        mock_genai.Client.return_value.models.generate_content.return_value = (
            mock_response
        )

        out = StringIO()
        call_command(
            "compose_urgent_alert",
            "--article-id",
            str(self.article.pk),
            "--dry-run",
            stdout=out,
        )
        self.assertEqual(Broadcast.objects.count(), 0)
        self.assertIn("DRY RUN", out.getvalue())

    @patch("broadcasts.services.urgent_alert.genai")
    def test_broadcast_subject_contains_title(self, mock_genai):
        mock_response = Mock()
        mock_response.text = (
            '{"what_happened": "X.", '
            '"who_affected": "Y.", '
            '"what_you_can_do": "Z.", '
            '"deadline": "1 April 2026"}'
        )
        mock_genai.Client.return_value.models.generate_content.return_value = (
            mock_response
        )

        call_command(
            "compose_urgent_alert",
            "--article-id",
            str(self.article.pk),
        )
        broadcast = Broadcast.objects.first()
        self.assertIn(self.article.title, broadcast.subject)
