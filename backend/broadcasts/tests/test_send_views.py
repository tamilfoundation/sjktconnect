"""Tests for broadcast send and detail views."""

from unittest.mock import patch

import pytest
from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse

from broadcasts.models import Broadcast, BroadcastRecipient
from subscribers.models import Subscriber


@pytest.fixture
def user(db):
    return User.objects.create_user(username="admin", password="testpass123")


@pytest.fixture
def auth_client(user):
    client = Client()
    client.login(username="admin", password="testpass123")
    return client


@pytest.fixture
def subscriber(db):
    return Subscriber.objects.create(
        email="reader@example.com", name="Reader", is_active=True
    )


@pytest.fixture
def draft_broadcast(db):
    return Broadcast.objects.create(
        subject="Test Broadcast",
        html_content="<p>Hello</p>",
        text_content="Hello",
        audience_filter={},
        status=Broadcast.Status.DRAFT,
    )


@pytest.fixture
def sent_broadcast(db):
    return Broadcast.objects.create(
        subject="Already Sent",
        html_content="<p>Old</p>",
        status=Broadcast.Status.SENT,
        recipient_count=3,
    )


@pytest.mark.django_db
class TestBroadcastSendView:
    """Tests for BroadcastSendView (POST broadcast/send/<pk>/)."""

    def test_requires_login(self, draft_broadcast):
        """Unauthenticated users are redirected to login."""
        client = Client()
        url = reverse("broadcasts:broadcast-send", kwargs={"pk": draft_broadcast.pk})
        response = client.post(url)
        assert response.status_code == 302
        assert "/accounts/login/" in response.url

    def test_send_draft_broadcast(self, auth_client, draft_broadcast, subscriber):
        """Sending a DRAFT broadcast transitions to SENT and redirects to detail."""
        url = reverse("broadcasts:broadcast-send", kwargs={"pk": draft_broadcast.pk})

        with patch.dict("os.environ", {}, clear=False):
            import os
            os.environ.pop("BREVO_API_KEY", None)

            response = auth_client.post(url)

        assert response.status_code == 302
        assert reverse(
            "broadcasts:broadcast-detail", kwargs={"pk": draft_broadcast.pk}
        ) in response.url

        draft_broadcast.refresh_from_db()
        assert draft_broadcast.status == Broadcast.Status.SENT

    def test_cannot_send_non_draft(self, auth_client, sent_broadcast):
        """Sending an already-sent broadcast shows error and redirects."""
        url = reverse("broadcasts:broadcast-send", kwargs={"pk": sent_broadcast.pk})
        response = auth_client.post(url)
        assert response.status_code == 302

        sent_broadcast.refresh_from_db()
        assert sent_broadcast.status == Broadcast.Status.SENT

    def test_send_nonexistent_broadcast_returns_404(self, auth_client):
        """Sending a non-existent broadcast returns 404."""
        url = reverse("broadcasts:broadcast-send", kwargs={"pk": 99999})
        response = auth_client.post(url)
        assert response.status_code == 404

    def test_get_not_allowed(self, auth_client, draft_broadcast):
        """GET is not allowed on the send view — only POST."""
        url = reverse("broadcasts:broadcast-send", kwargs={"pk": draft_broadcast.pk})
        response = auth_client.get(url)
        assert response.status_code == 405


@pytest.mark.django_db
class TestBroadcastDetailView:
    """Tests for BroadcastDetailView (GET broadcast/<pk>/)."""

    def test_requires_login(self, sent_broadcast):
        """Unauthenticated users are redirected to login."""
        client = Client()
        url = reverse("broadcasts:broadcast-detail", kwargs={"pk": sent_broadcast.pk})
        response = client.get(url)
        assert response.status_code == 302
        assert "/accounts/login/" in response.url

    def test_shows_broadcast_details(self, auth_client, sent_broadcast):
        """Detail view renders broadcast information."""
        url = reverse("broadcasts:broadcast-detail", kwargs={"pk": sent_broadcast.pk})
        response = auth_client.get(url)
        assert response.status_code == 200
        assert b"Already Sent" in response.content

    def test_shows_recipient_table(self, auth_client, draft_broadcast, subscriber):
        """After sending, detail view shows per-recipient status."""
        # Send the broadcast first
        with patch.dict("os.environ", {}, clear=False):
            import os
            os.environ.pop("BREVO_API_KEY", None)

            from broadcasts.services.sender import send_broadcast
            send_broadcast(draft_broadcast.pk)

        url = reverse("broadcasts:broadcast-detail", kwargs={"pk": draft_broadcast.pk})
        response = auth_client.get(url)
        assert response.status_code == 200
        assert b"reader@example.com" in response.content

    def test_nonexistent_broadcast_returns_404(self, auth_client):
        """Viewing a non-existent broadcast returns 404."""
        url = reverse("broadcasts:broadcast-detail", kwargs={"pk": 99999})
        response = auth_client.get(url)
        assert response.status_code == 404
