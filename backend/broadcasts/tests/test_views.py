"""Tests for broadcast views."""

import pytest
from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse

from broadcasts.models import Broadcast
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
def broadcast(db):
    return Broadcast.objects.create(
        subject="Test Broadcast",
        html_content="<p>Hello world</p>",
        text_content="Hello world",
        audience_filter={"state": "JOHOR"},
        recipient_count=5,
    )


@pytest.fixture
def subscriber(db):
    return Subscriber.objects.create(
        email="reader@example.com", name="Reader", is_active=True
    )


@pytest.mark.django_db
class TestBroadcastListView:
    def test_requires_login(self):
        """Unauthenticated users are redirected to login."""
        client = Client()
        response = client.get(reverse("broadcasts:broadcast-list"))
        assert response.status_code == 302
        assert "/accounts/login/" in response.url

    def test_shows_broadcasts(self, auth_client, broadcast):
        """Authenticated user sees broadcasts in the list."""
        response = auth_client.get(reverse("broadcasts:broadcast-list"))
        assert response.status_code == 200
        assert b"Test Broadcast" in response.content

    def test_empty_state(self, auth_client):
        """Empty list shows helpful message."""
        response = auth_client.get(reverse("broadcasts:broadcast-list"))
        assert response.status_code == 200
        assert b"No broadcasts yet" in response.content

    def test_compose_link_present(self, auth_client):
        """List page has a link to compose."""
        response = auth_client.get(reverse("broadcasts:broadcast-list"))
        assert b"Compose New Broadcast" in response.content


@pytest.mark.django_db
class TestBroadcastComposeView:
    def test_requires_login(self):
        """Unauthenticated users are redirected to login."""
        client = Client()
        response = client.get(reverse("broadcasts:broadcast-compose"))
        assert response.status_code == 302
        assert "/accounts/login/" in response.url

    def test_get_renders_form(self, auth_client):
        """GET renders the compose form with all fields."""
        response = auth_client.get(reverse("broadcasts:broadcast-compose"))
        assert response.status_code == 200
        assert b"Compose Broadcast" in response.content
        assert b"subject" in response.content
        assert b"html_content" in response.content
        assert b"state" in response.content

    def test_post_creates_draft(self, auth_client, subscriber):
        """POST creates a DRAFT broadcast and redirects to preview."""
        response = auth_client.post(
            reverse("broadcasts:broadcast-compose"),
            {
                "subject": "New Broadcast",
                "html_content": "<p>Content</p>",
                "text_content": "Content",
            },
        )
        assert response.status_code == 302
        broadcast = Broadcast.objects.get(subject="New Broadcast")
        assert broadcast.status == Broadcast.Status.DRAFT
        assert f"/broadcast/preview/{broadcast.pk}/" in response.url

    def test_post_with_audience_filters(self, auth_client, subscriber):
        """POST with audience filters saves them in audience_filter JSON."""
        response = auth_client.post(
            reverse("broadcasts:broadcast-compose"),
            {
                "subject": "Filtered Broadcast",
                "html_content": "<p>Hello</p>",
                "text_content": "Hello",
                "state": "JOHOR",
                "constituency": "P140",
                "min_enrolment": "50",
                "skm": "true",
                "category": "PARLIAMENT_WATCH",
            },
        )
        assert response.status_code == 302
        broadcast = Broadcast.objects.get(subject="Filtered Broadcast")
        assert broadcast.audience_filter["state"] == "JOHOR"
        assert broadcast.audience_filter["constituency"] == "P140"
        assert broadcast.audience_filter["min_enrolment"] == 50
        assert broadcast.audience_filter["skm"] is True
        assert broadcast.audience_filter["category"] == "PARLIAMENT_WATCH"

    def test_post_calculates_recipient_count(self, auth_client, subscriber):
        """POST calculates and stores recipient_count from audience filter."""
        response = auth_client.post(
            reverse("broadcasts:broadcast-compose"),
            {
                "subject": "Count Test",
                "html_content": "<p>Hi</p>",
                "text_content": "Hi",
            },
        )
        broadcast = Broadcast.objects.get(subject="Count Test")
        # subscriber is active, no filters → should match
        assert broadcast.recipient_count == 1

    def test_post_invalid_enrolment_does_not_crash(self, auth_client, subscriber):
        """POST with non-numeric enrolment ignores the value without crashing."""
        response = auth_client.post(
            reverse("broadcasts:broadcast-compose"),
            {
                "subject": "Enrolment Test",
                "html_content": "<p>Hi</p>",
                "text_content": "Hi",
                "min_enrolment": "abc",
                "max_enrolment": "xyz",
            },
        )
        assert response.status_code == 302
        broadcast = Broadcast.objects.get(subject="Enrolment Test")
        assert "min_enrolment" not in broadcast.audience_filter
        assert "max_enrolment" not in broadcast.audience_filter

    def test_post_empty_subject_rejected(self, auth_client, subscriber):
        """POST with empty subject re-renders form with error, does not create broadcast."""
        response = auth_client.post(
            reverse("broadcasts:broadcast-compose"),
            {
                "subject": "",
                "html_content": "<p>Content</p>",
                "text_content": "Content",
            },
        )
        assert response.status_code == 200  # Re-rendered form, not redirect
        assert b"Subject is required" in response.content
        assert Broadcast.objects.filter(html_content="<p>Content</p>").count() == 0

    def test_post_sets_created_by(self, auth_client, user, subscriber):
        """POST sets created_by to the current user."""
        response = auth_client.post(
            reverse("broadcasts:broadcast-compose"),
            {
                "subject": "Created By Test",
                "html_content": "<p>Hi</p>",
                "text_content": "Hi",
            },
        )
        broadcast = Broadcast.objects.get(subject="Created By Test")
        assert broadcast.created_by == user


@pytest.mark.django_db
class TestBroadcastPreviewView:
    def test_requires_login(self, broadcast):
        """Unauthenticated users are redirected to login."""
        client = Client()
        response = client.get(
            reverse("broadcasts:broadcast-preview", kwargs={"pk": broadcast.pk})
        )
        assert response.status_code == 302
        assert "/accounts/login/" in response.url

    def test_shows_broadcast_details(self, auth_client, broadcast):
        """Preview shows subject, status, and filter summary."""
        response = auth_client.get(
            reverse("broadcasts:broadcast-preview", kwargs={"pk": broadcast.pk})
        )
        assert response.status_code == 200
        assert b"Test Broadcast" in response.content
        assert b"Draft" in response.content
        assert b"JOHOR" in response.content

    def test_shows_recipient_count(self, auth_client, broadcast, subscriber):
        """Preview shows current recipient count."""
        response = auth_client.get(
            reverse("broadcasts:broadcast-preview", kwargs={"pk": broadcast.pk})
        )
        assert response.status_code == 200
        # recipient_count is recalculated from the filter
        assert b"subscriber" in response.content

    def test_shows_html_preview(self, auth_client, broadcast):
        """Preview renders the HTML content."""
        response = auth_client.get(
            reverse("broadcasts:broadcast-preview", kwargs={"pk": broadcast.pk})
        )
        assert b"Hello world" in response.content

    def test_send_button_disabled(self, auth_client, broadcast):
        """Send button is present but disabled (Sprint 2.3)."""
        response = auth_client.get(
            reverse("broadcasts:broadcast-preview", kwargs={"pk": broadcast.pk})
        )
        assert b"disabled" in response.content
        assert b"Send Broadcast" in response.content

    def test_404_for_nonexistent(self, auth_client):
        """Returns 404 for nonexistent broadcast."""
        response = auth_client.get(
            reverse("broadcasts:broadcast-preview", kwargs={"pk": 99999})
        )
        assert response.status_code == 404

    def test_filter_summary_all_subscribers(self, auth_client):
        """Empty filter shows 'All active subscribers'."""
        b = Broadcast.objects.create(
            subject="No Filter", audience_filter={}
        )
        response = auth_client.get(
            reverse("broadcasts:broadcast-preview", kwargs={"pk": b.pk})
        )
        assert b"All active subscribers" in response.content
