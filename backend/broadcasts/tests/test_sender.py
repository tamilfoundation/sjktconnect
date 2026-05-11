"""Tests for broadcast sender service."""

from unittest.mock import MagicMock, patch

import pytest
from django.utils import timezone

from broadcasts.models import Broadcast, BroadcastRecipient
from broadcasts.services.sender import (
    _wrap_broadcast_html,
    send_broadcast,
)
from subscribers.models import Subscriber


@pytest.fixture
def subscriber_a(db):
    return Subscriber.objects.create(
        email="alice@example.com", name="Alice", is_active=True
    )


@pytest.fixture
def subscriber_b(db):
    return Subscriber.objects.create(
        email="bob@example.com", name="Bob", is_active=True
    )


@pytest.fixture
def inactive_subscriber(db):
    return Subscriber.objects.create(
        email="gone@example.com", name="Gone", is_active=False
    )


@pytest.fixture
def draft_broadcast(db):
    return Broadcast.objects.create(
        subject="Test Blast",
        html_content="<p>Hello everyone</p>",
        text_content="Hello everyone",
        audience_filter={},
        status=Broadcast.Status.DRAFT,
    )


@pytest.fixture
def mock_brevo_quota():
    """Permissive Brevo quota for production-mode tests.

    The pre-flight quota check (added 2026-05-11 after the duplicate-
    blast incident) calls Brevo /v3/account. These tests don't want to
    hit the network, so we short-circuit get_quota with plenty of room.
    """
    permissive = {
        "daily_quota": 1000,
        "used_today": 0,
        "remaining": 1000,
        "dev_mode": False,
    }
    with patch("broadcasts.services.sender.get_quota", return_value=permissive):
        yield permissive


@pytest.mark.django_db
class TestSendBroadcast:
    """Test send_broadcast service function."""

    def test_dev_mode_sends_all_recipients(
        self, draft_broadcast, subscriber_a, subscriber_b
    ):
        """Without BREVO_API_KEY, logs to console and marks all as SENT."""
        with patch.dict("os.environ", {}, clear=False):
            # Ensure BREVO_API_KEY is not set
            import os
            os.environ.pop("BREVO_API_KEY", None)

            result = send_broadcast(draft_broadcast.pk)

        assert result.status == Broadcast.Status.SENT
        assert result.sent_at is not None
        assert result.recipient_count == 2

        recipients = BroadcastRecipient.objects.filter(broadcast=draft_broadcast)
        assert recipients.count() == 2
        for r in recipients:
            assert r.status == BroadcastRecipient.DeliveryStatus.SENT
            assert r.sent_at is not None

    def test_excludes_inactive_subscribers(
        self, draft_broadcast, subscriber_a, inactive_subscriber
    ):
        """Inactive subscribers are not included as recipients."""
        with patch.dict("os.environ", {}, clear=False):
            import os
            os.environ.pop("BREVO_API_KEY", None)

            result = send_broadcast(draft_broadcast.pk)

        assert result.recipient_count == 1
        emails = list(
            BroadcastRecipient.objects.filter(broadcast=draft_broadcast)
            .values_list("email", flat=True)
        )
        assert "alice@example.com" in emails
        assert "gone@example.com" not in emails

    def test_status_transitions(self, draft_broadcast, subscriber_a):
        """Status goes DRAFT -> SENDING -> SENT."""
        with patch.dict("os.environ", {}, clear=False):
            import os
            os.environ.pop("BREVO_API_KEY", None)

            result = send_broadcast(draft_broadcast.pk)

        assert result.status == Broadcast.Status.SENT

    def test_rejects_non_draft(self, db, subscriber_a):
        """Cannot send a broadcast that is not in DRAFT status."""
        broadcast = Broadcast.objects.create(
            subject="Already Sent",
            status=Broadcast.Status.SENT,
        )
        with pytest.raises(ValueError, match="not DRAFT"):
            send_broadcast(broadcast.pk)

    def test_rejects_sending_status(self, db, subscriber_a):
        """Cannot send a broadcast that is currently SENDING."""
        broadcast = Broadcast.objects.create(
            subject="In Progress",
            status=Broadcast.Status.SENDING,
        )
        with pytest.raises(ValueError, match="not DRAFT"):
            send_broadcast(broadcast.pk)

    @patch("broadcasts.services.sender.requests.post")
    def test_production_mode_calls_brevo(
        self, mock_post, draft_broadcast, subscriber_a, mock_brevo_quota
    ):
        """With BREVO_API_KEY, calls Brevo API for each recipient."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"messageId": "msg-123"}
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        with patch.dict("os.environ", {"BREVO_API_KEY": "test-key"}):
            with patch("broadcasts.services.sender.time.sleep"):
                result = send_broadcast(draft_broadcast.pk)

        assert result.status == Broadcast.Status.SENT
        assert mock_post.call_count == 1

        recipient = BroadcastRecipient.objects.get(broadcast=draft_broadcast)
        assert recipient.status == BroadcastRecipient.DeliveryStatus.SENT
        assert recipient.brevo_message_id == "msg-123"

    @patch("broadcasts.services.sender.requests.post")
    def test_reply_to_header_included_in_brevo_payload(
        self, mock_post, draft_broadcast, subscriber_a, mock_brevo_quota
    ):
        """Brevo API payload includes replyTo with feedback address."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"messageId": "msg-456"}
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        with patch.dict("os.environ", {"BREVO_API_KEY": "test-key"}):
            with patch("broadcasts.services.sender.time.sleep"):
                send_broadcast(draft_broadcast.pk)

        payload = mock_post.call_args[1]["json"]
        assert "replyTo" in payload
        assert payload["replyTo"]["email"] == "feedback@tamilschool.org"
        assert payload["replyTo"]["name"] == "SJK(T) Connect"

    @patch("broadcasts.services.sender.requests.post")
    def test_to_payload_includes_name_when_subscriber_has_name(
        self, mock_post, draft_broadcast, subscriber_a, mock_brevo_quota
    ):
        """When subscriber.name is set, Brevo `to` entry includes it."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"messageId": "msg-789"}
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        with patch.dict("os.environ", {"BREVO_API_KEY": "test-key"}):
            with patch("broadcasts.services.sender.time.sleep"):
                send_broadcast(draft_broadcast.pk)

        payload = mock_post.call_args[1]["json"]
        assert payload["to"] == [{"email": "alice@example.com", "name": "Alice"}]

    @patch("broadcasts.services.sender.requests.post")
    def test_to_payload_omits_name_when_subscriber_name_empty(
        self, mock_post, draft_broadcast, db, mock_brevo_quota
    ):
        """Bulk-imported subscribers default to name='' — Brevo returns
        400 if `to.name` is present but empty, so we omit the key
        entirely. Regression test for the 259-failed welcome-email
        send on 2026-04-28."""
        from broadcasts.models import BroadcastRecipient
        nameless = Subscriber.objects.create(
            email="noname@example.com", name="", is_active=True
        )
        BroadcastRecipient.objects.create(
            broadcast=draft_broadcast,
            subscriber=nameless,
            email=nameless.email,
            status=BroadcastRecipient.DeliveryStatus.PENDING,
        )

        mock_response = MagicMock()
        mock_response.json.return_value = {"messageId": "msg-999"}
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        with patch.dict("os.environ", {"BREVO_API_KEY": "test-key"}):
            with patch("broadcasts.services.sender.time.sleep"):
                send_broadcast(draft_broadcast.pk)

        # Find the call for the nameless recipient (may not be the only call)
        calls = mock_post.call_args_list
        nameless_calls = [
            c for c in calls
            if c[1]["json"]["to"][0]["email"] == "noname@example.com"
        ]
        assert len(nameless_calls) == 1
        to_entry = nameless_calls[0][1]["json"]["to"][0]
        assert to_entry == {"email": "noname@example.com"}
        assert "name" not in to_entry

    @patch("broadcasts.services.sender.requests.post")
    def test_production_mode_handles_api_failure(
        self, mock_post, draft_broadcast, subscriber_a, mock_brevo_quota
    ):
        """API failure marks recipient as FAILED but broadcast still completes."""
        import requests as req
        mock_post.side_effect = req.RequestException("API error")

        with patch.dict("os.environ", {"BREVO_API_KEY": "test-key"}):
            with patch("broadcasts.services.sender.time.sleep"):
                result = send_broadcast(draft_broadcast.pk)

        # Broadcast still marked as SENT (overall)
        assert result.status == Broadcast.Status.SENT

        recipient = BroadcastRecipient.objects.get(broadcast=draft_broadcast)
        assert recipient.status == BroadcastRecipient.DeliveryStatus.FAILED

    def test_broadcast_fails_on_unhandled_exception(
        self, draft_broadcast, subscriber_a
    ):
        """C2: Unhandled exception during send sets status to FAILED, not stuck on SENDING."""
        with patch(
            "broadcasts.services.sender.get_filtered_subscribers",
            side_effect=RuntimeError("unexpected failure"),
        ):
            result = send_broadcast(draft_broadcast.pk)

        assert result.status == Broadcast.Status.FAILED
        assert result.sent_at is not None

    def test_recipient_email_denormalised(
        self, draft_broadcast, subscriber_a
    ):
        """BroadcastRecipient.email matches subscriber.email at send time."""
        with patch.dict("os.environ", {}, clear=False):
            import os
            os.environ.pop("BREVO_API_KEY", None)

            send_broadcast(draft_broadcast.pk)

        recipient = BroadcastRecipient.objects.get(
            broadcast=draft_broadcast, subscriber=subscriber_a
        )
        assert recipient.email == "alice@example.com"


@pytest.mark.django_db
class TestWrapBroadcastHtml:
    """Test the HTML wrapper helper."""

    def test_wraps_content_with_footer(self):
        """Content is wrapped with unsubscribe and preferences links."""
        html = _wrap_broadcast_html(
            "<p>Hello</p>",
            "https://example.com/unsubscribe/abc/",
            "https://example.com/preferences/abc/",
        )
        assert "<p>Hello</p>" in html
        assert "https://example.com/unsubscribe/abc/" in html
        assert "https://example.com/preferences/abc/" in html
        assert "&mdash;" in html  # HTML entities, not Unicode
        assert "&amp;" in html

    def test_uses_html_entities(self):
        """Footer uses HTML entities instead of Unicode characters."""
        html = _wrap_broadcast_html("<p>Test</p>", "http://u", "http://p")
        assert "&mdash;" in html
        assert "&middot;" in html
        assert "&amp;" in html
