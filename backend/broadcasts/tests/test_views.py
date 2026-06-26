"""Tests for broadcast views."""

import pytest
from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse

from broadcasts.models import Broadcast
from subscribers.models import Subscriber


@pytest.fixture
def user(db):
    # TD-20 (2026-06-26): broadcast views are now SUPERUSER-only via
    # SuperuserRequiredMixin. The shared `user` fixture creates a
    # superuser so the bulk of the test suite (which asserts 200 OK on
    # admin actions) continues to pass. `regular_user` below is for
    # the new role-gating tests that expect 403.
    return User.objects.create_superuser(
        username="admin", email="admin@example.com", password="testpass123"
    )


@pytest.fixture
def auth_client(user):
    client = Client()
    client.login(username="admin", password="testpass123")
    return client


@pytest.fixture
def regular_user(db):
    return User.objects.create_user(username="regular", password="testpass123")


@pytest.fixture
def regular_client(regular_user):
    client = Client()
    client.login(username="regular", password="testpass123")
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
class TestBroadcastViewsRoleGating:
    """TD-20 (2026-06-26): regular users are 403'd from broadcast admin endpoints.

    Anonymous users redirect to login (LoginRequiredMixin); authenticated
    non-superusers get 403 (SuperuserRequiredMixin.raise_exception=True).
    Only superusers reach the view body.
    """

    def test_list_regular_user_403(self, regular_client):
        response = regular_client.get(reverse("broadcasts:broadcast-list"))
        assert response.status_code == 403

    def test_compose_regular_user_403(self, regular_client):
        response = regular_client.get(reverse("broadcasts:broadcast-compose"))
        assert response.status_code == 403

    def test_preview_regular_user_403(self, regular_client, broadcast):
        response = regular_client.get(
            reverse("broadcasts:broadcast-preview", kwargs={"pk": broadcast.pk})
        )
        assert response.status_code == 403

    def test_send_regular_user_403(self, regular_client, broadcast):
        response = regular_client.post(
            reverse("broadcasts:broadcast-send", kwargs={"pk": broadcast.pk})
        )
        assert response.status_code == 403

    def test_send_test_regular_user_403(self, regular_client, broadcast):
        response = regular_client.post(
            reverse("broadcasts:broadcast-send-test", kwargs={"pk": broadcast.pk}),
            {"recipients": "spam@example.com"},
        )
        assert response.status_code == 403

    def test_detail_regular_user_403(self, regular_client, broadcast):
        response = regular_client.get(
            reverse("broadcasts:broadcast-detail", kwargs={"pk": broadcast.pk})
        )
        assert response.status_code == 403


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

    def test_kind_filter_dropdown_present(self, auth_client):
        """Sprint 25: kind filter dropdown is rendered with all choices."""
        response = auth_client.get(reverse("broadcasts:broadcast-list"))
        assert b"Filter by kind" in response.content
        assert b"URGENT_ALERT" in response.content
        assert b"PARLIAMENT_WATCH" in response.content

    def test_kind_filter_narrows_queryset(self, auth_client, db):
        """Sprint 25: ?kind=URGENT_ALERT shows only urgent alerts."""
        Broadcast.objects.create(
            subject="Monthly Blast Jan",
            kind=Broadcast.Kind.MONTHLY_BLAST,
        )
        Broadcast.objects.create(
            subject="URGENT: school closure",
            kind=Broadcast.Kind.URGENT_ALERT,
        )
        response = auth_client.get(
            reverse("broadcasts:broadcast-list") + "?kind=URGENT_ALERT"
        )
        assert b"URGENT: school closure" in response.content
        assert b"Monthly Blast Jan" not in response.content

    def test_kind_filter_invalid_value_ignored(self, auth_client, broadcast):
        """Sprint 25: garbage ?kind=... falls back to showing everything."""
        response = auth_client.get(
            reverse("broadcasts:broadcast-list") + "?kind=NOT_A_KIND"
        )
        assert response.status_code == 200
        assert b"Test Broadcast" in response.content


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

    def test_send_button_enabled_for_draft(self, auth_client, broadcast):
        """Send button is enabled for DRAFT broadcasts."""
        response = auth_client.get(
            reverse("broadcasts:broadcast-preview", kwargs={"pk": broadcast.pk})
        )
        assert b"Send Broadcast" in response.content
        assert b"broadcast/send/" in response.content

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

    def test_send_test_form_visible_for_draft(self, auth_client, broadcast):
        """Sprint 25: Send Test form is rendered on DRAFT preview pages."""
        response = auth_client.get(
            reverse("broadcasts:broadcast-preview", kwargs={"pk": broadcast.pk})
        )
        assert b"Send Test" in response.content
        assert b"broadcast/send-test/" in response.content

    def test_send_test_form_hidden_for_sent(self, auth_client):
        """Sprint 25: Send Test form is hidden once the broadcast leaves DRAFT."""
        sent = Broadcast.objects.create(
            subject="Already sent",
            audience_filter={},
            status=Broadcast.Status.SENT,
        )
        response = auth_client.get(
            reverse("broadcasts:broadcast-preview", kwargs={"pk": sent.pk})
        )
        assert b"broadcast/send-test/" not in response.content


@pytest.mark.django_db
class TestBroadcastSendTestView:
    """Sprint 25: test-send endpoint that does NOT touch broadcast state."""

    def test_requires_login(self, broadcast):
        client = Client()
        response = client.post(
            reverse("broadcasts:broadcast-send-test", kwargs={"pk": broadcast.pk}),
            {"recipients": "x@example.com"},
        )
        assert response.status_code == 302
        assert "/accounts/login/" in response.url

    def test_empty_recipients_flashes_error(self, auth_client, broadcast):
        response = auth_client.post(
            reverse("broadcasts:broadcast-send-test", kwargs={"pk": broadcast.pk}),
            {"recipients": "   "},
        )
        assert response.status_code == 302
        # Broadcast unchanged
        broadcast.refresh_from_db()
        assert broadcast.status == Broadcast.Status.DRAFT
        assert broadcast.recipient_count == 5  # from fixture

    def test_cap_of_5_recipients(self, auth_client, broadcast):
        """More than 5 recipients is rejected — test sends are not bulk sends."""
        recipients = ",".join(f"u{i}@example.com" for i in range(6))
        response = auth_client.post(
            reverse("broadcasts:broadcast-send-test", kwargs={"pk": broadcast.pk}),
            {"recipients": recipients},
        )
        assert response.status_code == 302
        broadcast.refresh_from_db()
        assert broadcast.status == Broadcast.Status.DRAFT

    @pytest.mark.django_db
    def test_calls_send_test_and_keeps_draft(self, auth_client, broadcast):
        """send_test() is invoked; broadcast stays DRAFT; no recipients created."""
        from unittest.mock import patch
        with patch("broadcasts.views.send_test", return_value=(2, 0)) as mock:
            response = auth_client.post(
                reverse(
                    "broadcasts:broadcast-send-test",
                    kwargs={"pk": broadcast.pk},
                ),
                {"recipients": "a@example.com, b@example.com"},
            )
        assert response.status_code == 302
        mock.assert_called_once()
        args, _ = mock.call_args
        assert args[0] == broadcast.pk
        assert args[1] == ["a@example.com", "b@example.com"]
        broadcast.refresh_from_db()
        assert broadcast.status == Broadcast.Status.DRAFT
        assert broadcast.recipients.count() == 0
