"""Tests for broadcast sender service."""

from unittest.mock import MagicMock, patch

import pytest
from django.utils import timezone

from broadcasts.models import Broadcast, BroadcastRecipient
from broadcasts.services.brevo_quota import BrevoQuotaError
from broadcasts.services.sender import (
    _wrap_broadcast_html,
    resume_broadcast,
    send_broadcast,
    send_test,
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


@pytest.fixture
def sending_broadcast_with_pending(db, subscriber_a, subscriber_b):
    """A broadcast mid-drain: SENDING with two PENDING recipients."""
    broadcast = Broadcast.objects.create(
        subject="Mid-drain digest",
        html_content="<p>Hello</p>",
        kind=Broadcast.Kind.NEWS_DIGEST,
        status=Broadcast.Status.SENDING,
    )
    for sub in (subscriber_a, subscriber_b):
        BroadcastRecipient.objects.create(
            broadcast=broadcast,
            subscriber=sub,
            email=sub.email,
            status=BroadcastRecipient.DeliveryStatus.PENDING,
        )
    return broadcast


def _quota(remaining, daily=300):
    return {
        "daily_quota": daily,
        "used_today": daily - remaining,
        "remaining": remaining,
        "dev_mode": False,
    }


def _ok_post_response():
    response = MagicMock()
    response.json.return_value = {"messageId": "msg-1"}
    response.raise_for_status = MagicMock()
    return response


@pytest.mark.django_db
class TestQuotaResilience:
    """Quota exhaustion is transient — it must NEVER mark a broadcast FAILED.

    Regression tests for the 2026-06-11 stuck-digest incident: a
    QuotaExceeded on resume marked broadcasts 79-82 FAILED, the resume
    job ignores FAILED, and the same ~250 subscribers silently received
    nothing for five weeks. The same path made full-list urgent alerts
    (audience > daily quota) permanently unsendable.
    """

    def test_resume_with_quota_exhausted_stays_sending(
        self, sending_broadcast_with_pending
    ):
        """THE incident regression: zero quota left -> stay SENDING, not FAILED."""
        with patch.dict("os.environ", {"BREVO_API_KEY": "test-key"}):
            with patch(
                "broadcasts.services.sender.get_quota",
                return_value=_quota(0),
            ):
                result = resume_broadcast(sending_broadcast_with_pending.pk)

        assert result.status == Broadcast.Status.SENDING
        pending = result.recipients.filter(
            status=BroadcastRecipient.DeliveryStatus.PENDING
        ).count()
        assert pending == 2

    @patch("broadcasts.services.sender.requests.post")
    def test_resume_partial_quota_sends_what_fits(
        self, mock_post, sending_broadcast_with_pending
    ):
        """Quota for 1 of 2 pending -> 1 sent, 1 pending, still SENDING."""
        mock_post.return_value = _ok_post_response()
        with patch.dict("os.environ", {"BREVO_API_KEY": "test-key"}):
            with patch("broadcasts.services.sender.time.sleep"):
                with patch(
                    "broadcasts.services.sender.get_quota",
                    return_value=_quota(1),
                ):
                    result = resume_broadcast(sending_broadcast_with_pending.pk)

        assert result.status == Broadcast.Status.SENDING
        assert mock_post.call_count == 1
        statuses = list(
            result.recipients.values_list("status", flat=True)
        )
        assert sorted(statuses) == [
            BroadcastRecipient.DeliveryStatus.PENDING,
            BroadcastRecipient.DeliveryStatus.SENT,
        ]

    @patch("broadcasts.services.sender.requests.post")
    def test_resume_next_day_completes_to_sent(
        self, mock_post, sending_broadcast_with_pending
    ):
        """With quota available, the drain finishes and the broadcast is SENT."""
        mock_post.return_value = _ok_post_response()
        with patch.dict("os.environ", {"BREVO_API_KEY": "test-key"}):
            with patch("broadcasts.services.sender.time.sleep"):
                with patch(
                    "broadcasts.services.sender.get_quota",
                    return_value=_quota(300),
                ):
                    result = resume_broadcast(sending_broadcast_with_pending.pk)

        assert result.status == Broadcast.Status.SENT
        assert result.sent_at is not None
        assert mock_post.call_count == 2

    def test_resume_quota_probe_failure_stays_sending(
        self, sending_broadcast_with_pending
    ):
        """A failed quota PROBE is transient too — stay SENDING for retry."""
        with patch.dict("os.environ", {"BREVO_API_KEY": "test-key"}):
            with patch(
                "broadcasts.services.sender.get_quota",
                side_effect=BrevoQuotaError("probe failed"),
            ):
                result = resume_broadcast(sending_broadcast_with_pending.pk)

        assert result.status == Broadcast.Status.SENDING

    def test_send_broadcast_quota_exhausted_stays_sending(
        self, draft_broadcast, subscriber_a, subscriber_b
    ):
        """Initial send with zero quota queues everyone and stays SENDING.

        This is the urgent-alert scenario: an audience larger than the
        daily cap must drain over days, never refuse-and-FAIL.
        """
        with patch.dict("os.environ", {"BREVO_API_KEY": "test-key"}):
            with patch(
                "broadcasts.services.sender.get_quota",
                return_value=_quota(0),
            ):
                result = send_broadcast(draft_broadcast.pk)

        assert result.status == Broadcast.Status.SENDING
        pending = result.recipients.filter(
            status=BroadcastRecipient.DeliveryStatus.PENDING
        ).count()
        assert pending == 2

    @patch("broadcasts.services.sender.requests.post")
    def test_send_broadcast_partial_quota_sends_what_fits(
        self, mock_post, draft_broadcast, subscriber_a, subscriber_b
    ):
        mock_post.return_value = _ok_post_response()
        with patch.dict("os.environ", {"BREVO_API_KEY": "test-key"}):
            with patch("broadcasts.services.sender.time.sleep"):
                with patch(
                    "broadcasts.services.sender.get_quota",
                    return_value=_quota(1),
                ):
                    result = send_broadcast(draft_broadcast.pk)

        assert result.status == Broadcast.Status.SENDING
        assert mock_post.call_count == 1

    def test_send_broadcast_quota_probe_failure_stays_sending(
        self, draft_broadcast, subscriber_a
    ):
        with patch.dict("os.environ", {"BREVO_API_KEY": "test-key"}):
            with patch(
                "broadcasts.services.sender.get_quota",
                side_effect=BrevoQuotaError("probe failed"),
            ):
                result = send_broadcast(draft_broadcast.pk)

        assert result.status == Broadcast.Status.SENDING


@pytest.mark.django_db
class TestSenderName:
    """News-type emails arrive from "SJK(T) News" (owner decision 2026-06-11)."""

    def _payload_for_kind(self, kind, subscriber):
        broadcast = Broadcast.objects.create(
            subject="Sender name test",
            html_content="<p>Hi</p>",
            kind=kind,
            status=Broadcast.Status.DRAFT,
        )
        mock_post_response = _ok_post_response()
        with patch.dict("os.environ", {"BREVO_API_KEY": "test-key"}):
            with patch("broadcasts.services.sender.time.sleep"):
                with patch(
                    "broadcasts.services.sender.get_quota",
                    return_value=_quota(300),
                ):
                    with patch(
                        "broadcasts.services.sender.requests.post",
                        return_value=mock_post_response,
                    ) as mock_post:
                        send_broadcast(broadcast.pk)
        return mock_post.call_args[1]["json"]

    def test_news_digest_sends_as_sjkt_news(self, subscriber_a):
        payload = self._payload_for_kind(
            Broadcast.Kind.NEWS_DIGEST, subscriber_a
        )
        assert payload["sender"]["name"] == "SJK(T) News"
        assert payload["sender"]["email"] == "noreply@tamilschool.org"

    def test_urgent_alert_sends_as_sjkt_news(self, subscriber_a):
        payload = self._payload_for_kind(
            Broadcast.Kind.URGENT_ALERT, subscriber_a
        )
        assert payload["sender"]["name"] == "SJK(T) News"

    def test_monthly_blast_keeps_platform_name(self, subscriber_a):
        payload = self._payload_for_kind(
            Broadcast.Kind.MONTHLY_BLAST, subscriber_a
        )
        assert payload["sender"]["name"] == "SJK(T) Connect"


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


@pytest.mark.django_db
class TestSendTest:
    """Sprint 25 — send_test() must not mutate broadcast state."""

    def test_dev_mode_no_state_change(self, draft_broadcast):
        """Without BREVO_API_KEY the function logs and counts as sent."""
        with patch.dict("os.environ", {}, clear=False):
            import os as _os
            _os.environ.pop("BREVO_API_KEY", None)
            sent, failed = send_test(
                draft_broadcast.pk,
                ["a@example.com", "b@example.com"],
            )
        assert sent == 2
        assert failed == 0
        draft_broadcast.refresh_from_db()
        assert draft_broadcast.status == Broadcast.Status.DRAFT
        assert draft_broadcast.recipient_count == 0
        # CRITICAL: no BroadcastRecipient rows created.
        assert draft_broadcast.recipients.count() == 0

    def test_empty_strings_in_list_are_skipped(self, draft_broadcast):
        with patch.dict("os.environ", {}, clear=False):
            import os as _os
            _os.environ.pop("BREVO_API_KEY", None)
            sent, failed = send_test(
                draft_broadcast.pk,
                ["", "a@example.com", "  "],
            )
        assert sent == 1
        assert failed == 0

    def test_test_subject_is_prefixed(self, draft_broadcast):
        """The Brevo payload subject is [TEST]-prefixed."""
        captured = {}

        def fake_post(url, json, headers, timeout):  # noqa: ARG001
            captured["subject"] = json["subject"]
            resp = MagicMock()
            resp.status_code = 200
            return resp

        with patch.dict("os.environ", {"BREVO_API_KEY": "fake"}):
            with patch("broadcasts.services.sender.requests.post", side_effect=fake_post):
                with patch("broadcasts.services.sender.time.sleep"):
                    send_test(draft_broadcast.pk, ["a@example.com"])

        assert captured["subject"] == f"[TEST] {draft_broadcast.subject}"

    def test_request_failure_counted_not_raised(self, draft_broadcast):
        """A Brevo error does NOT bubble — failed count increments."""
        import requests as real_requests

        with patch.dict("os.environ", {"BREVO_API_KEY": "fake"}):
            with patch(
                "broadcasts.services.sender.requests.post",
                side_effect=real_requests.RequestException("boom"),
            ):
                with patch("broadcasts.services.sender.time.sleep"):
                    sent, failed = send_test(
                        draft_broadcast.pk,
                        ["a@example.com", "b@example.com"],
                    )
        assert sent == 0
        assert failed == 2
        draft_broadcast.refresh_from_db()
        assert draft_broadcast.status == Broadcast.Status.DRAFT
