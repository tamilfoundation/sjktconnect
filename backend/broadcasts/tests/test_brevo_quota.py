"""Tests for the Brevo daily-quota helper."""

from unittest.mock import MagicMock, patch

import pytest
import requests
from django.utils import timezone

from broadcasts.models import Broadcast, BroadcastRecipient
from broadcasts.services.brevo_quota import (
    DEFAULT_DAILY_QUOTA,
    BrevoQuotaError,
    get_quota,
)
from subscribers.models import Subscriber


@pytest.fixture
def _ok_account_response():
    response = MagicMock()
    response.json.return_value = {"email": "admin@tamilfoundation.org"}
    response.raise_for_status = MagicMock()
    return response


@pytest.mark.django_db
class TestGetQuota:
    def test_dev_mode_returns_full_quota_without_api_key(self):
        with patch.dict("os.environ", {}, clear=False):
            import os
            os.environ.pop("BREVO_API_KEY", None)
            quota = get_quota()

        assert quota["dev_mode"] is True
        assert quota["daily_quota"] == DEFAULT_DAILY_QUOTA
        assert quota["used_today"] == 0
        assert quota["remaining"] == DEFAULT_DAILY_QUOTA

    @patch("broadcasts.services.brevo_quota.requests.get")
    def test_production_mode_returns_remaining_300_when_unused(
        self, mock_get, _ok_account_response
    ):
        mock_get.return_value = _ok_account_response
        with patch.dict("os.environ", {"BREVO_API_KEY": "test-key"}):
            quota = get_quota()

        assert quota["dev_mode"] is False
        assert quota["daily_quota"] == DEFAULT_DAILY_QUOTA
        assert quota["used_today"] == 0
        assert quota["remaining"] == DEFAULT_DAILY_QUOTA

    @patch("broadcasts.services.brevo_quota.requests.get")
    def test_counts_today_sent_recipients(
        self, mock_get, _ok_account_response
    ):
        mock_get.return_value = _ok_account_response
        broadcast = Broadcast.objects.create(
            subject="Test", status=Broadcast.Status.SENT,
        )
        subscriber = Subscriber.objects.create(email="a@x.com", is_active=True)
        BroadcastRecipient.objects.create(
            broadcast=broadcast,
            subscriber=subscriber,
            email=subscriber.email,
            status=BroadcastRecipient.DeliveryStatus.SENT,
            sent_at=timezone.now(),
        )

        with patch.dict("os.environ", {"BREVO_API_KEY": "test-key"}):
            quota = get_quota()

        assert quota["used_today"] == 1
        assert quota["remaining"] == DEFAULT_DAILY_QUOTA - 1

    @patch("broadcasts.services.brevo_quota.requests.get")
    def test_excludes_pending_and_failed_from_used_count(
        self, mock_get, _ok_account_response
    ):
        mock_get.return_value = _ok_account_response
        broadcast = Broadcast.objects.create(
            subject="Test", status=Broadcast.Status.SENDING,
        )
        for status_value, email in [
            (BroadcastRecipient.DeliveryStatus.PENDING, "p@x.com"),
            (BroadcastRecipient.DeliveryStatus.FAILED, "f@x.com"),
        ]:
            sub = Subscriber.objects.create(email=email, is_active=True)
            BroadcastRecipient.objects.create(
                broadcast=broadcast,
                subscriber=sub,
                email=email,
                status=status_value,
                sent_at=timezone.now(),
            )

        with patch.dict("os.environ", {"BREVO_API_KEY": "test-key"}):
            quota = get_quota()

        assert quota["used_today"] == 0

    @patch("broadcasts.services.brevo_quota.requests.get")
    def test_remaining_clamped_to_zero(
        self, mock_get, _ok_account_response
    ):
        mock_get.return_value = _ok_account_response
        broadcast = Broadcast.objects.create(
            subject="Test", status=Broadcast.Status.SENT,
        )
        # Exceed the default quota
        for i in range(DEFAULT_DAILY_QUOTA + 5):
            sub = Subscriber.objects.create(
                email=f"u{i}@x.com", is_active=True
            )
            BroadcastRecipient.objects.create(
                broadcast=broadcast,
                subscriber=sub,
                email=sub.email,
                status=BroadcastRecipient.DeliveryStatus.DELIVERED,
                sent_at=timezone.now(),
            )

        with patch.dict("os.environ", {"BREVO_API_KEY": "test-key"}):
            quota = get_quota()

        assert quota["remaining"] == 0

    @patch("broadcasts.services.brevo_quota.requests.get")
    def test_network_error_raises_brevo_quota_error(self, mock_get):
        mock_get.side_effect = requests.RequestException("boom")
        with patch.dict("os.environ", {"BREVO_API_KEY": "test-key"}):
            with pytest.raises(BrevoQuotaError, match="probe failed"):
                get_quota()

    def test_env_override_for_daily_quota(self):
        with patch.dict(
            "os.environ", {"BREVO_DAILY_QUOTA": "500"}, clear=False
        ):
            import os
            os.environ.pop("BREVO_API_KEY", None)
            quota = get_quota()

        assert quota["daily_quota"] == 500
        assert quota["remaining"] == 500
