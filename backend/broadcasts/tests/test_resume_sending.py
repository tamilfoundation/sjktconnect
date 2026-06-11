"""Tests for the resume_sending management command.

Covers the daily drain loop and the FAILED-broadcast sweep added after
the 2026-06-11 stuck-digest incident (four digests sat FAILED for five
weeks while every job involved kept exiting 0 — the sweep makes this
daily job exit non-zero so the Cloud Run console and the job-failure
alert both see it).
"""

from datetime import timedelta
from io import StringIO
from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.utils import timezone

from broadcasts.models import Broadcast, BroadcastRecipient
from subscribers.models import Subscriber


@pytest.fixture
def subscriber(db):
    return Subscriber.objects.create(
        email="reader@example.com", name="Reader", is_active=True
    )


def _sending_broadcast(subscriber, subject="Mid-drain"):
    broadcast = Broadcast.objects.create(
        subject=subject,
        html_content="<p>Hi</p>",
        kind=Broadcast.Kind.NEWS_DIGEST,
        status=Broadcast.Status.SENDING,
    )
    BroadcastRecipient.objects.create(
        broadcast=broadcast,
        subscriber=subscriber,
        email=subscriber.email,
        status=BroadcastRecipient.DeliveryStatus.PENDING,
    )
    return broadcast


def _failed_broadcast(updated_days_ago=0):
    broadcast = Broadcast.objects.create(
        subject="Broken broadcast",
        kind=Broadcast.Kind.NEWS_DIGEST,
        status=Broadcast.Status.FAILED,
    )
    if updated_days_ago:
        Broadcast.objects.filter(pk=broadcast.pk).update(
            updated_at=timezone.now() - timedelta(days=updated_days_ago)
        )
    return broadcast


def _run(*args):
    out = StringIO()
    # Dev mode (no BREVO_API_KEY) — sends log to console and mark SENT.
    with patch.dict("os.environ", {}, clear=False):
        import os
        os.environ.pop("BREVO_API_KEY", None)
        call_command("resume_sending", *args, stdout=out)
    return out.getvalue()


@pytest.mark.django_db
class TestResumeSendingDrain:
    def test_drains_all_sending_broadcasts(self, subscriber, db):
        """Every SENDING broadcast is resumed, not just the latest."""
        second_subscriber = Subscriber.objects.create(
            email="other@example.com", name="Other", is_active=True
        )
        first = _sending_broadcast(subscriber, subject="First digest")
        second = _sending_broadcast(second_subscriber, subject="Urgent thing")

        _run()

        first.refresh_from_db()
        second.refresh_from_db()
        assert first.status == Broadcast.Status.SENT
        assert second.status == Broadcast.Status.SENT

    def test_no_sending_broadcasts_is_clean(self, db):
        output = _run()
        assert "No broadcasts in SENDING status." in output


@pytest.mark.django_db
class TestFailedBroadcastSweep:
    def test_recent_failed_broadcast_fails_the_run(self, db):
        broadcast = _failed_broadcast()
        with pytest.raises(CommandError, match="BROADCAST_FAILED_ALERT"):
            _run()
        # The sweep is detection-only — it must not mutate the broadcast.
        broadcast.refresh_from_db()
        assert broadcast.status == Broadcast.Status.FAILED

    def test_sweep_runs_even_when_nothing_is_sending(self, db):
        """The early-return path must still surface FAILED broadcasts."""
        _failed_broadcast()
        with pytest.raises(CommandError, match="BROADCAST_FAILED_ALERT"):
            _run()

    def test_drain_completes_before_the_sweep_raises(self, subscriber, db):
        """A FAILED broadcast must not block draining a healthy one."""
        healthy = _sending_broadcast(subscriber)
        _failed_broadcast()
        with pytest.raises(CommandError, match="BROADCAST_FAILED_ALERT"):
            _run()
        healthy.refresh_from_db()
        assert healthy.status == Broadcast.Status.SENT

    def test_old_failed_broadcast_does_not_fail_the_run(self, db):
        _failed_broadcast(updated_days_ago=10)
        output = _run()
        assert "No broadcasts in SENDING status." in output

    def test_cancelled_broadcast_does_not_fail_the_run(self, db):
        Broadcast.objects.create(
            subject="Abandoned",
            kind=Broadcast.Kind.NEWS_DIGEST,
            status=Broadcast.Status.CANCELLED,
        )
        output = _run()
        assert "No broadcasts in SENDING status." in output

    def test_dry_run_warns_instead_of_failing(self, db):
        _failed_broadcast()
        output = _run("--dry-run")
        assert "BROADCAST_FAILED_ALERT" in output
