"""Tests for Brevo webhook endpoint and event processing."""

import json

import pytest
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from broadcasts.models import Broadcast, BroadcastRecipient
from broadcasts.services.webhook import HARD_BOUNCE_THRESHOLD, process_brevo_event
from subscribers.models import Subscriber


@pytest.fixture
def subscriber(db):
    return Subscriber.objects.create(
        email="test@example.com", name="Test User", is_active=True
    )


@pytest.fixture
def broadcast(db):
    return Broadcast.objects.create(
        subject="Weekly Update",
        html_content="<p>Hello</p>",
        status=Broadcast.Status.SENT,
        sent_at=timezone.now(),
    )


@pytest.fixture
def recipient(db, broadcast, subscriber):
    return BroadcastRecipient.objects.create(
        broadcast=broadcast,
        subscriber=subscriber,
        email=subscriber.email,
        status=BroadcastRecipient.DeliveryStatus.SENT,
        brevo_message_id="abc-123-def",
        sent_at=timezone.now(),
    )


# --- Service-level tests ---


class TestProcessBrevoEvent:
    def test_delivered_event(self, recipient):
        result = process_brevo_event({
            "event": "delivered",
            "message-id": "abc-123-def",
        })
        assert result is True
        recipient.refresh_from_db()
        assert recipient.status == BroadcastRecipient.DeliveryStatus.DELIVERED
        assert recipient.delivered_at is not None

    def test_opened_event(self, recipient):
        result = process_brevo_event({
            "event": "opened",
            "message-id": "abc-123-def",
        })
        assert result is True
        recipient.refresh_from_db()
        assert recipient.opened_at is not None
        assert recipient.open_count == 1
        # Status upgraded from SENT to DELIVERED
        assert recipient.status == BroadcastRecipient.DeliveryStatus.DELIVERED

    def test_opened_event_increments_count(self, recipient):
        # First open
        process_brevo_event({"event": "opened", "message-id": "abc-123-def"})
        # Second open
        process_brevo_event({"event": "opened", "message-id": "abc-123-def"})
        recipient.refresh_from_db()
        assert recipient.open_count == 2

    def test_click_event(self, recipient):
        result = process_brevo_event({
            "event": "click",
            "message-id": "abc-123-def",
        })
        assert result is True
        recipient.refresh_from_db()
        assert recipient.clicked_at is not None
        assert recipient.click_count == 1

    def test_click_event_increments_count(self, recipient):
        process_brevo_event({"event": "click", "message-id": "abc-123-def"})
        process_brevo_event({"event": "click", "message-id": "abc-123-def"})
        recipient.refresh_from_db()
        assert recipient.click_count == 2

    def test_hard_bounce_event(self, recipient, subscriber):
        result = process_brevo_event({
            "event": "hard_bounce",
            "message-id": "abc-123-def",
        })
        assert result is True
        recipient.refresh_from_db()
        assert recipient.status == BroadcastRecipient.DeliveryStatus.BOUNCED
        assert recipient.bounce_type == BroadcastRecipient.BounceType.HARD
        subscriber.refresh_from_db()
        assert subscriber.bounce_count == 1
        assert subscriber.is_active is False  # Threshold is 1 — deactivated immediately

    def test_soft_bounce_event(self, recipient, subscriber):
        result = process_brevo_event({
            "event": "soft_bounce",
            "message-id": "abc-123-def",
        })
        assert result is True
        recipient.refresh_from_db()
        assert recipient.status == BroadcastRecipient.DeliveryStatus.BOUNCED
        assert recipient.bounce_type == BroadcastRecipient.BounceType.SOFT
        # Soft bounces do NOT increment subscriber bounce_count
        subscriber.refresh_from_db()
        assert subscriber.bounce_count == 0

    def test_spam_event(self, recipient):
        result = process_brevo_event({
            "event": "spam",
            "message-id": "abc-123-def",
        })
        assert result is True
        recipient.refresh_from_db()
        assert recipient.status == BroadcastRecipient.DeliveryStatus.SPAM

    def test_unsubscribed_event(self, recipient, subscriber):
        result = process_brevo_event({
            "event": "unsubscribed",
            "message-id": "abc-123-def",
        })
        assert result is True
        subscriber.refresh_from_db()
        assert subscriber.is_active is False
        assert subscriber.unsubscribed_at is not None

    def test_auto_deactivate_after_threshold_bounces(self, subscriber, db):
        """Subscriber is auto-deactivated after HARD_BOUNCE_THRESHOLD hard bounces."""
        for i in range(HARD_BOUNCE_THRESHOLD):
            bc = Broadcast.objects.create(
                subject=f"Bounce test {i}",
                status=Broadcast.Status.SENT,
                sent_at=timezone.now(),
            )
            BroadcastRecipient.objects.create(
                broadcast=bc,
                subscriber=subscriber,
                email=subscriber.email,
                status=BroadcastRecipient.DeliveryStatus.SENT,
                brevo_message_id=f"bounce-msg-{i}",
                sent_at=timezone.now(),
            )
            process_brevo_event({
                "event": "hard_bounce",
                "message-id": f"bounce-msg-{i}",
            })

        subscriber.refresh_from_db()
        assert subscriber.bounce_count == HARD_BOUNCE_THRESHOLD
        assert subscriber.is_active is False

    def test_unknown_message_id_returns_false(self, db):
        result = process_brevo_event({
            "event": "delivered",
            "message-id": "unknown-id-999",
        })
        assert result is False

    def test_missing_event_returns_false(self, db):
        result = process_brevo_event({"message-id": "abc-123-def"})
        assert result is False

    def test_missing_message_id_returns_false(self, db):
        result = process_brevo_event({"event": "delivered"})
        assert result is False

    def test_angle_brackets_stripped(self, recipient):
        """Brevo sometimes wraps message-id in angle brackets."""
        result = process_brevo_event({
            "event": "delivered",
            "message-id": "<abc-123-def>",
        })
        assert result is True
        recipient.refresh_from_db()
        assert recipient.status == BroadcastRecipient.DeliveryStatus.DELIVERED

    def test_opened_preserves_delivered_status(self, recipient):
        """If already DELIVERED, opening doesn't downgrade status."""
        recipient.status = BroadcastRecipient.DeliveryStatus.DELIVERED
        recipient.delivered_at = timezone.now()
        recipient.save()

        process_brevo_event({"event": "opened", "message-id": "abc-123-def"})
        recipient.refresh_from_db()
        assert recipient.status == BroadcastRecipient.DeliveryStatus.DELIVERED
        assert recipient.open_count == 1


# --- API endpoint tests ---


@pytest.mark.django_db
class TestBrevoWebhookEndpoint:
    def setup_method(self):
        self.client = APIClient()
        self.url = reverse("broadcasts-api:brevo-webhook")
        self.subscriber = Subscriber.objects.create(
            email="api@example.com", name="API User", is_active=True
        )
        self.broadcast = Broadcast.objects.create(
            subject="Test",
            status=Broadcast.Status.SENT,
            sent_at=timezone.now(),
        )
        self.recipient = BroadcastRecipient.objects.create(
            broadcast=self.broadcast,
            subscriber=self.subscriber,
            email=self.subscriber.email,
            status=BroadcastRecipient.DeliveryStatus.SENT,
            brevo_message_id="endpoint-msg-1",
            sent_at=timezone.now(),
        )

    def test_single_event(self):
        response = self.client.post(
            self.url,
            data={"event": "delivered", "message-id": "endpoint-msg-1"},
            format="json",
        )
        assert response.status_code == 200
        assert response.data["processed"] == 1

    def test_batch_events(self):
        sub2 = Subscriber.objects.create(
            email="api2@example.com", name="API User 2", is_active=True
        )
        r2 = BroadcastRecipient.objects.create(
            broadcast=self.broadcast,
            subscriber=sub2,
            email=sub2.email,
            status=BroadcastRecipient.DeliveryStatus.SENT,
            brevo_message_id="endpoint-msg-2",
            sent_at=timezone.now(),
        )
        response = self.client.post(
            self.url,
            data=[
                {"event": "delivered", "message-id": "endpoint-msg-1"},
                {"event": "opened", "message-id": "endpoint-msg-2"},
            ],
            format="json",
        )
        assert response.status_code == 200
        assert response.data["processed"] == 2

    def test_no_auth_required(self):
        """Webhook endpoint must be public (Brevo can't send tokens)."""
        response = self.client.post(
            self.url,
            data={"event": "delivered", "message-id": "unknown"},
            format="json",
        )
        assert response.status_code == 200

    @pytest.mark.parametrize("secret_env", ["test-secret-key"])
    def test_hmac_validation_rejects_bad_signature(self, secret_env, settings):
        import os
        with pytest.MonkeyPatch.context() as mp:
            mp.setenv("BREVO_WEBHOOK_SECRET", secret_env)
            response = self.client.post(
                self.url,
                data={"event": "delivered", "message-id": "endpoint-msg-1"},
                format="json",
                HTTP_X_SIB_SIGNATURE="invalid-signature",
            )
            assert response.status_code == 403
