from datetime import date, timedelta
from io import StringIO
from unittest.mock import Mock, patch

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from django.core.management.base import CommandError

from broadcasts.management.commands.compose_news_digest import (
    FORTNIGHT_DAYS,
    WINDOW_ABORT_DAYS,
    Command as ComposeNewsDigestCommand,
    _digest_subject,
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
        # Owner decision 2026-06-11: the big story's headline is the subject
        self.assertEqual(broadcast.subject, "New building")
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

    def _make_digest(self, coverage_end, created_delta_days=0,
                     status=Broadcast.Status.SENT):
        b = Broadcast.objects.create(
            subject=f"News Watch coverage ending {coverage_end}",
            kind=Broadcast.Kind.NEWS_DIGEST,
            coverage_start_date=coverage_end - timedelta(days=14),
            coverage_end_date=coverage_end,
            status=status,
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

    # --- 2026-06-11 stuck-digest incident regressions ---

    def test_skips_at_eight_days_fortnightly_cadence(self):
        """The old 7-day guard let a weekly cron double-fire at day 8-13.

        Fortnightly cadence: coverage ended 8 days ago -> still skip.
        """
        self._make_digest(
            coverage_end=self.now.date() - timedelta(days=8),
            created_delta_days=8,
        )
        self.assertTrue(self.cmd._should_skip())

    def test_sends_at_exactly_fortnight(self):
        self._make_digest(
            coverage_end=self.now.date() - timedelta(days=FORTNIGHT_DAYS),
            created_delta_days=FORTNIGHT_DAYS,
        )
        self.assertFalse(self.cmd._should_skip())

    def test_failed_digest_does_not_suppress_recompose(self):
        """A FAILED digest must be re-attempted next Monday, not waited out."""
        self._make_digest(
            coverage_end=self.now.date() - timedelta(days=2),
            created_delta_days=2,
            status=Broadcast.Status.FAILED,
        )
        self.assertFalse(self.cmd._should_skip())

    def test_failed_digest_does_not_advance_anchor(self):
        """A failed send re-attempts the SAME window (owner decision).

        Incident shape: good digest ending 4 May, then a FAILED one ending
        19 May. The next compose must start 5 May, not 20 May — and not
        freeze either.
        """
        self._make_digest(coverage_end=date(2026, 5, 4), created_delta_days=40)
        self._make_digest(
            coverage_end=date(2026, 5, 19),
            created_delta_days=25,
            status=Broadcast.Status.FAILED,
        )
        since = self.cmd._get_since_date()
        self.assertEqual(since.date(), date(2026, 5, 5))

    def test_cancelled_digest_does_not_advance_anchor(self):
        """CANCELLED (operator-abandoned) digests are invisible to the anchor."""
        self._make_digest(coverage_end=date(2026, 5, 4), created_delta_days=40)
        self._make_digest(
            coverage_end=date(2026, 5, 25),
            created_delta_days=17,
            status=Broadcast.Status.CANCELLED,
        )
        since = self.cmd._get_since_date()
        self.assertEqual(since.date(), date(2026, 5, 5))

    def test_cancelled_digest_does_not_suppress_recompose(self):
        self._make_digest(
            coverage_end=self.now.date() - timedelta(days=2),
            created_delta_days=2,
            status=Broadcast.Status.CANCELLED,
        )
        self.assertFalse(self.cmd._should_skip())

    def test_sending_digest_suppresses_recompose(self):
        """A digest mid-drain (SENDING) must not be recomposed over."""
        self._make_digest(
            coverage_end=self.now.date() - timedelta(days=3),
            created_delta_days=3,
            status=Broadcast.Status.SENDING,
        )
        self.assertTrue(self.cmd._should_skip())


class DigestSubjectTest(TestCase):
    """The big story headline becomes the subject (owner decision 2026-06-11)."""

    def test_uses_big_story_title(self):
        subject = _digest_subject(
            {"title": "Decade-Long Wait Ends for SJK(T) Ladang Labu"},
            "5 May 2026 - 8 Jun 2026",
        )
        self.assertEqual(
            subject, "Decade-Long Wait Ends for SJK(T) Ladang Labu"
        )

    def test_sanitises_unicode_punctuation_to_ascii(self):
        """Subjects must be plain ASCII (lesson 21)."""
        subject = _digest_subject(
            {"title": "School’s ‘big’ win — RM2m"},
            "label",
        )
        self.assertEqual(subject, "School's 'big' win - RM2m")

    def test_falls_back_to_dated_pattern_without_big_story(self):
        subject = _digest_subject({}, "5 May 2026 – 8 Jun 2026")
        self.assertEqual(subject, "News Watch - 5 May 2026 - 8 Jun 2026")

    def test_falls_back_when_big_story_is_none(self):
        subject = _digest_subject(None, "label")
        self.assertEqual(subject, "News Watch - label")

    def test_truncates_very_long_titles(self):
        subject = _digest_subject({"title": "x" * 400}, "label")
        self.assertEqual(len(subject), 150)


class WindowGuardTest(TestCase):
    """Stuck-anchor tripwire: abort when the window is impossibly wide."""

    def test_aborts_when_window_exceeds_abort_threshold(self):
        wide = WINDOW_ABORT_DAYS + 5
        Broadcast.objects.create(
            subject="Old digest",
            kind=Broadcast.Kind.NEWS_DIGEST,
            coverage_start_date=timezone.now().date() - timedelta(days=wide + 14),
            coverage_end_date=timezone.now().date() - timedelta(days=wide),
            status=Broadcast.Status.SENT,
        )
        with self.assertRaises(CommandError):
            call_command("compose_news_digest")

    def test_force_window_bypasses_abort(self):
        """--force-window allows a deliberate catch-up; with no articles the
        command then exits cleanly without composing."""
        wide = WINDOW_ABORT_DAYS + 5
        Broadcast.objects.create(
            subject="Old digest",
            kind=Broadcast.Kind.NEWS_DIGEST,
            coverage_start_date=timezone.now().date() - timedelta(days=wide + 14),
            coverage_end_date=timezone.now().date() - timedelta(days=wide),
            status=Broadcast.Status.SENT,
        )
        out = StringIO()
        call_command("compose_news_digest", "--force-window", stdout=out)
        self.assertEqual(
            Broadcast.objects.exclude(subject="Old digest").count(), 0
        )
