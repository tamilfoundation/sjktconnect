"""Tests for broadcasts models."""

import pytest
from django.db import IntegrityError
from django.utils import timezone

from broadcasts.models import Broadcast, BroadcastRecipient
from subscribers.models import Subscriber


@pytest.fixture
def subscriber(db):
    return Subscriber.objects.create(email="test@example.com", name="Test User")


@pytest.fixture
def broadcast(db):
    return Broadcast.objects.create(
        subject="Test Broadcast",
        html_content="<p>Hello</p>",
        text_content="Hello",
    )


@pytest.mark.django_db
class TestBroadcast:
    def test_create_with_defaults(self):
        """Broadcast is created with sensible defaults."""
        b = Broadcast.objects.create(subject="Weekly Update")
        assert b.subject == "Weekly Update"
        assert b.status == Broadcast.Status.DRAFT
        assert b.recipient_count == 0
        assert b.html_content == ""
        assert b.text_content == ""
        assert b.audience_filter == {}
        assert b.sent_at is None

    def test_status_choices(self):
        """All status choices are valid."""
        for status_value, _label in Broadcast.Status.choices:
            b = Broadcast.objects.create(
                subject=f"Test {status_value}", status=status_value
            )
            assert b.status == status_value

    def test_str_representation(self, broadcast):
        """String representation includes subject and status."""
        assert str(broadcast) == "Test Broadcast (Draft)"

    def test_str_representation_sent(self):
        """String representation reflects sent status."""
        b = Broadcast.objects.create(
            subject="Sent One", status=Broadcast.Status.SENT
        )
        assert str(b) == "Sent One (Sent)"

    def test_ordering_newest_first(self):
        """Broadcasts are ordered by newest first via Meta.ordering."""
        assert Broadcast._meta.ordering == ["-created_at"]

    def test_audience_filter_stores_json(self):
        """audience_filter stores arbitrary JSON."""
        filters = {"state": "JOHOR", "min_enrolment": 50}
        b = Broadcast.objects.create(subject="Filtered", audience_filter=filters)
        b.refresh_from_db()
        assert b.audience_filter == filters

    def test_sent_at_nullable(self):
        """sent_at is null by default and can be set."""
        b = Broadcast.objects.create(subject="Test")
        assert b.sent_at is None
        now = timezone.now()
        b.sent_at = now
        b.save()
        b.refresh_from_db()
        assert b.sent_at is not None

    def test_timestamps_auto_set(self):
        """created_at and updated_at are set automatically."""
        b = Broadcast.objects.create(subject="Timestamps")
        assert b.created_at is not None
        assert b.updated_at is not None


@pytest.mark.django_db
class TestBroadcastRecipient:
    def test_create_recipient(self, broadcast, subscriber):
        """BroadcastRecipient is created with defaults."""
        r = BroadcastRecipient.objects.create(
            broadcast=broadcast,
            subscriber=subscriber,
            email=subscriber.email,
        )
        assert r.status == BroadcastRecipient.DeliveryStatus.PENDING
        assert r.brevo_message_id == ""
        assert r.sent_at is None

    def test_str_representation(self, broadcast, subscriber):
        """String representation includes email and status."""
        r = BroadcastRecipient.objects.create(
            broadcast=broadcast,
            subscriber=subscriber,
            email="test@example.com",
        )
        assert str(r) == "test@example.com — Pending"

    def test_unique_together_constraint(self, broadcast, subscriber):
        """Cannot create duplicate recipient for same broadcast+subscriber."""
        BroadcastRecipient.objects.create(
            broadcast=broadcast,
            subscriber=subscriber,
            email=subscriber.email,
        )
        with pytest.raises(IntegrityError):
            BroadcastRecipient.objects.create(
                broadcast=broadcast,
                subscriber=subscriber,
                email=subscriber.email,
            )

    def test_ordering_by_email(self, broadcast):
        """Recipients are ordered by email."""
        s1 = Subscriber.objects.create(email="alice@example.com")
        s2 = Subscriber.objects.create(email="bob@example.com")
        BroadcastRecipient.objects.create(
            broadcast=broadcast, subscriber=s2, email=s2.email
        )
        BroadcastRecipient.objects.create(
            broadcast=broadcast, subscriber=s1, email=s1.email
        )
        recipients = list(broadcast.recipients.all())
        assert recipients[0].email == "alice@example.com"
        assert recipients[1].email == "bob@example.com"

    def test_delivery_status_choices(self, broadcast, subscriber):
        """All delivery status choices are valid."""
        for status_value, _label in BroadcastRecipient.DeliveryStatus.choices:
            r = BroadcastRecipient.objects.create(
                broadcast=Broadcast.objects.create(subject=f"B-{status_value}"),
                subscriber=subscriber,
                email=subscriber.email,
                status=status_value,
            )
            assert r.status == status_value
