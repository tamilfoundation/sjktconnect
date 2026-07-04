"""Tests for the send_urgent_alerts management command.

Urgent alerts ALWAYS go to admin review — the auto-send branch was
retired 2026-07-01 (audit follow-up). Prior tests exercised both
`URGENT_ALERT_REQUIRE_REVIEW` on/off states; only the DRAFT path
remains.
"""

from datetime import timedelta
from io import StringIO
from unittest.mock import Mock, patch

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from broadcasts.models import Broadcast
from newswatch.models import NewsArticle


@patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"})
class SendUrgentAlertsTest(TestCase):
    def setUp(self):
        self.article = NewsArticle.objects.create(
            url="https://example.com/closure",
            title="SJK(T) X to close on 1 June",
            source_name="Test Source",
            published_date=timezone.now() - timedelta(hours=2),
            body_text="SJK(T) X officially closing 1 June. Appeal by 15 May.",
            status=NewsArticle.ANALYSED,
            relevance_score=5,
            sentiment="NEGATIVE",
            ai_summary="SJK(T) X closing 1 June, appeal deadline 15 May.",
            is_urgent=True,
            urgent_reason="Imminent closure with appeal window.",
            review_status=NewsArticle.APPROVED,
        )

    def _mock_gemini(self, mock_genai):
        mock_resp = Mock()
        mock_resp.text = (
            '{"what_happened": "Closure announced.",'
            ' "who_affected": "80 students.",'
            ' "what_you_can_do": "Write to state director.",'
            ' "deadline": "15 May 2026"}'
        )
        mock_genai.Client.return_value.models.generate_content.return_value = (
            mock_resp
        )

    @patch("broadcasts.services.urgent_alert.genai")
    def test_creates_draft_and_skips_send(self, mock_genai):
        self._mock_gemini(mock_genai)
        out = StringIO()

        call_command("send_urgent_alerts", stdout=out)

        broadcast = Broadcast.objects.get(kind=Broadcast.Kind.URGENT_ALERT)
        self.assertEqual(broadcast.status, Broadcast.Status.DRAFT)
        self.assertTrue(broadcast.subject.startswith("URGENT:"))
        self.assertIn("DRAFT for review", out.getvalue())

    @patch("broadcasts.services.urgent_alert.genai")
    def test_broadcast_has_urgent_alert_kind(self, mock_genai):
        self._mock_gemini(mock_genai)

        call_command("send_urgent_alerts", stdout=StringIO())

        broadcast = Broadcast.objects.latest("pk")
        self.assertEqual(broadcast.kind, Broadcast.Kind.URGENT_ALERT)
