"""Tests for confirmation email on subscribe."""

from unittest.mock import MagicMock, patch

import pytest

from subscribers.models import Subscriber, SubscriptionPreference
from subscribers.services.email_service import send_confirmation_email
from subscribers.services.subscriber_service import subscribe


@pytest.mark.django_db
class TestSendConfirmationEmail:
    """Tests for the send_confirmation_email function."""

    def test_dev_mode_logs_to_console(self, db):
        """Without BREVO_API_KEY, logs to console and returns True."""
        subscriber = Subscriber.objects.create(
            email="dev@example.com", name="Dev User"
        )
        with patch.dict("os.environ", {}, clear=False):
            import os
            os.environ.pop("BREVO_API_KEY", None)

            result = send_confirmation_email(subscriber)

        assert result is True

    @patch("subscribers.services.email_service.requests.post")
    def test_production_mode_calls_brevo(self, mock_post, db):
        """With BREVO_API_KEY, sends via Brevo API."""
        subscriber = Subscriber.objects.create(
            email="prod@example.com", name="Prod User"
        )
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        with patch.dict("os.environ", {"BREVO_API_KEY": "test-key"}):
            result = send_confirmation_email(subscriber)

        assert result is True
        assert mock_post.call_count == 1

        # Verify payload
        call_kwargs = mock_post.call_args
        payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        assert payload["subject"] == "Welcome to SJK(T) Connect"
        assert payload["sender"]["email"] == "noreply@tamilschool.org"
        assert payload["to"][0]["email"] == "prod@example.com"

    @patch("subscribers.services.email_service.requests.post")
    def test_api_failure_returns_false(self, mock_post, db):
        """API failure returns False."""
        import requests as req
        subscriber = Subscriber.objects.create(
            email="fail@example.com", name="Fail"
        )
        mock_post.side_effect = req.RequestException("timeout")

        with patch.dict("os.environ", {"BREVO_API_KEY": "test-key"}):
            result = send_confirmation_email(subscriber)

        assert result is False

    def test_html_includes_preferences_link(self, db):
        """Confirmation email HTML includes preferences URL."""
        subscriber = Subscriber.objects.create(
            email="html@example.com", name="HTML"
        )
        with patch.dict(
            "os.environ",
            {"FRONTEND_URL": "https://tamilschool.org"},
            clear=False,
        ):
            import os
            os.environ.pop("BREVO_API_KEY", None)

            # We can test the HTML builder directly
            from subscribers.services.email_service import _build_confirmation_html

            html = _build_confirmation_html(
                "HTML",
                "https://tamilschool.org/preferences/%s/" % subscriber.unsubscribe_token,
                "https://tamilschool.org/unsubscribe/%s/" % subscriber.unsubscribe_token,
            )

        assert "Manage Your Preferences" in html
        assert "Unsubscribe" in html
        assert str(subscriber.unsubscribe_token) in html

    def test_html_uses_html_entities(self, db):
        """Confirmation email uses HTML entities, not Unicode."""
        from subscribers.services.email_service import _build_confirmation_html
        html = _build_confirmation_html("Test", "http://p", "http://u")
        assert "&mdash;" in html
        assert "&rsquo;" in html


@pytest.mark.django_db
class TestSubscribeTriggersConfirmationEmail:
    """Tests that subscribing triggers a confirmation email."""

    @patch("subscribers.services.subscriber_service.send_confirmation_email")
    def test_new_subscriber_receives_confirmation(self, mock_send):
        """New subscriber triggers confirmation email."""
        subscriber, created = subscribe("new@example.com", name="New User")
        assert created is True
        mock_send.assert_called_once_with(subscriber)

    @patch("subscribers.services.subscriber_service.send_confirmation_email")
    def test_duplicate_subscriber_no_confirmation(self, mock_send):
        """Existing active subscriber does NOT trigger confirmation email."""
        # Create first
        subscribe("dup@example.com", name="Dup")
        mock_send.reset_mock()

        # Subscribe again
        subscriber, created = subscribe("dup@example.com")
        assert created is False
        mock_send.assert_not_called()

    @patch("subscribers.services.subscriber_service.send_confirmation_email")
    def test_reactivated_subscriber_no_confirmation(self, mock_send):
        """Reactivated subscriber does NOT trigger confirmation email."""
        # Create and unsubscribe
        sub = Subscriber.objects.create(
            email="react@example.com", name="React", is_active=False
        )
        mock_send.reset_mock()

        # Reactivate via subscribe
        subscriber, created = subscribe("react@example.com")
        assert created is True  # reactivation returns True
        # But no confirmation email — it was not a NEW creation
        # Actually, looking at the code, reactivation also calls subscribe
        # which goes through a different branch. Let me check...
        # The reactivation branch does NOT call send_confirmation_email
        # because we only added it in the `if created:` block (get_or_create)
        mock_send.assert_not_called()
