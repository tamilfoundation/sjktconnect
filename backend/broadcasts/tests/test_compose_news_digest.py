from datetime import date, timedelta
from io import StringIO
from unittest.mock import Mock, patch

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from broadcasts.management.commands.compose_news_digest import (
    Command as ComposeNewsDigestCommand,
)
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
        self.assertEqual(broadcast.kind, Broadcast.Kind.NEWS_DIGEST)
        self.assertIsNotNone(broadcast.coverage_start_date)
        self.assertIsNotNone(broadcast.coverage_end_date)

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


class DigestCadenceTest(TestCase):
    """Cadence logic: _should_skip and _get_since_date filter on kind."""

    def setUp(self):
        self.cmd = ComposeNewsDigestCommand()
        self.now = timezone.now()

    def _make_digest(self, coverage_end, created_delta_days=0):
        b = Broadcast.objects.create(
            subject=f"News Watch coverage ending {coverage_end}",
            kind=Broadcast.Kind.NEWS_DIGEST,
            coverage_start_date=coverage_end - timedelta(days=14),
            coverage_end_date=coverage_end,
            status=Broadcast.Status.SENT,
        )
        if created_delta_days:
            Broadcast.objects.filter(pk=b.pk).update(
                created_at=self.now - timedelta(days=created_delta_days)
            )
        return b

    def _make_urgent(self, created_delta_days):
        b = Broadcast.objects.create(
            subject="URGENT: some crisis",
            kind=Broadcast.Kind.URGENT_ALERT,
            status=Broadcast.Status.SENT,
        )
        Broadcast.objects.filter(pk=b.pk).update(
            created_at=self.now - timedelta(days=created_delta_days)
        )
        return b

    def test_urgent_alert_in_window_does_not_trigger_skip(self):
        self._make_urgent(created_delta_days=3)
        self.assertFalse(self.cmd._should_skip())

    def test_digest_in_window_triggers_skip(self):
        self._make_digest(
            coverage_end=self.now.date() - timedelta(days=2),
            created_delta_days=3,
        )
        self.assertTrue(self.cmd._should_skip())

    def test_digest_outside_window_does_not_trigger_skip(self):
        self._make_digest(
            coverage_end=self.now.date() - timedelta(days=14),
            created_delta_days=14,
        )
        self.assertFalse(self.cmd._should_skip())

    def test_since_returns_coverage_end_plus_one_day(self):
        self._make_digest(
            coverage_end=date(2026, 3, 30),
            created_delta_days=22,
        )
        since = self.cmd._get_since_date()
        self.assertEqual(since.date(), date(2026, 3, 31))

    def test_since_ignores_urgent_alerts(self):
        self._make_digest(
            coverage_end=date(2026, 3, 30),
            created_delta_days=22,
        )
        self._make_urgent(created_delta_days=14)
        since = self.cmd._get_since_date()
        # Should be day after the digest's coverage end, not based on urgent alert
        self.assertEqual(since.date(), date(2026, 3, 31))

    def test_since_falls_back_to_14_days_when_no_digest_exists(self):
        self._make_urgent(created_delta_days=3)  # Noise
        since = self.cmd._get_since_date()
        expected = self.now - timedelta(days=14)
        self.assertAlmostEqual(
            since.timestamp(), expected.timestamp(), delta=5,
        )
