from unittest.mock import patch, MagicMock

from django.test import TestCase

from feedback.models import InboundEmail
from feedback.services.gmail_fetcher import (
    fetch_new_emails,
    _parse_email_address,
    _detect_broadcast_type,
)


class ParseEmailAddressTest(TestCase):
    def test_plain_email(self):
        name, email = _parse_email_address("reader@example.com")
        self.assertEqual(name, "")
        self.assertEqual(email, "reader@example.com")

    def test_name_and_email(self):
        name, email = _parse_email_address("A Reader <reader@example.com>")
        self.assertEqual(name, "A Reader")
        self.assertEqual(email, "reader@example.com")

    def test_quoted_name(self):
        name, email = _parse_email_address('"A Reader" <reader@example.com>')
        self.assertEqual(email, "reader@example.com")


class DetectBroadcastTypeTest(TestCase):
    def test_parliament_watch(self):
        self.assertEqual(
            _detect_broadcast_type("Re: Parliament Watch — 1st Meeting"),
            "PARLIAMENT_WATCH",
        )

    def test_news_watch(self):
        self.assertEqual(
            _detect_broadcast_type("Re: News Watch — 17 Feb"),
            "NEWS_WATCH",
        )

    def test_urgent(self):
        self.assertEqual(
            _detect_broadcast_type("Re: URGENT: School closure"),
            "NEWS_WATCH",
        )

    def test_monthly_blast(self):
        self.assertEqual(
            _detect_broadcast_type("Re: Monthly Intelligence Blast — Feb"),
            "MONTHLY_BLAST",
        )

    def test_unknown(self):
        self.assertEqual(_detect_broadcast_type("Random subject"), "")


class FetchNewEmailsTest(TestCase):
    @patch("feedback.services.gmail_fetcher._get_gmail_service")
    def test_skips_already_fetched(self, mock_get_service):
        InboundEmail.objects.create(
            gmail_message_id="msg_001",
            from_email="reader@example.com",
            subject="Old",
            body_text="Old",
        )
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service
        mock_service.users.return_value.messages.return_value.list.return_value.execute.return_value = {
            "messages": [{"id": "msg_001", "threadId": "thread_001"}]
        }

        result = fetch_new_emails()
        self.assertEqual(result["skipped"], 1)
        self.assertEqual(InboundEmail.objects.count(), 1)

    @patch("feedback.services.gmail_fetcher._get_gmail_service")
    def test_returns_zero_on_empty_inbox(self, mock_get_service):
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service
        mock_service.users.return_value.messages.return_value.list.return_value.execute.return_value = {}

        result = fetch_new_emails()
        self.assertEqual(result["fetched"], 0)
        self.assertEqual(result["skipped"], 0)
