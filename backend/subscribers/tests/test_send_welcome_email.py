"""Tests for the send_welcome_email management command.

Sprint-19 follow-up (2026-04-28): regression test for the exclusion
filter that was missing webhook-confirmed DELIVERED recipients.
Broadcasts 70 + 71 double-sent to 14 recipients on 2026-04-28 because
the filter only matched status="SENT" while the Brevo webhook had
moved them to status="DELIVERED" within seconds.
"""

from unittest.mock import patch
from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from broadcasts.models import Broadcast, BroadcastRecipient
from subscribers.models import Subscriber

WELCOME_SUBJECT = "Introducing SJK(T) Connect — Tamil School Intelligence for Our Community"


class SendWelcomeEmailExclusionTests(TestCase):
    """Anyone with a prior SENT *or* DELIVERED status should be excluded."""

    def setUp(self):
        self.alice = Subscriber.objects.create(
            email="alice@example.com", name="Alice",
            source="BULK_IMPORT", is_active=True,
        )
        self.bob = Subscriber.objects.create(
            email="bob@example.com", name="Bob",
            source="BULK_IMPORT", is_active=True,
        )
        self.carol = Subscriber.objects.create(
            email="carol@example.com", name="Carol",
            source="BULK_IMPORT", is_active=True,
        )

    def _prior_broadcast(self):
        return Broadcast.objects.create(
            subject=WELCOME_SUBJECT,
            html_content="<p>Welcome</p>",
            text_content="Welcome",
            audience_filter={"category": "", "source": "BULK_IMPORT"},
            status=Broadcast.Status.SENT,
        )

    def test_dry_run_excludes_prior_DELIVERED_recipients(self):
        """Webhook-updated DELIVERED status must count as 'already received'."""
        prior = self._prior_broadcast()
        # Alice's prior recipient has been webhook-confirmed → DELIVERED.
        BroadcastRecipient.objects.create(
            broadcast=prior, subscriber=self.alice,
            email=self.alice.email,
            status=BroadcastRecipient.DeliveryStatus.DELIVERED,
        )
        # Bob's prior recipient is still SENT (webhook hasn't fired yet).
        BroadcastRecipient.objects.create(
            broadcast=prior, subscriber=self.bob,
            email=self.bob.email,
            status=BroadcastRecipient.DeliveryStatus.SENT,
        )
        # Carol has NO prior recipient row — she should appear in remaining.

        out = StringIO()
        call_command("send_welcome_email", "--dry-run", stdout=out)
        output = out.getvalue()

        # Both Alice (DELIVERED) and Bob (SENT) excluded → only Carol left.
        assert "1 of 3 bulk-imported subscribers still need" in output

    def test_dry_run_includes_prior_FAILED_recipients(self):
        """FAILED recipients should still be retried."""
        prior = self._prior_broadcast()
        BroadcastRecipient.objects.create(
            broadcast=prior, subscriber=self.alice,
            email=self.alice.email,
            status=BroadcastRecipient.DeliveryStatus.FAILED,
        )
        BroadcastRecipient.objects.create(
            broadcast=prior, subscriber=self.bob,
            email=self.bob.email,
            status=BroadcastRecipient.DeliveryStatus.DELIVERED,
        )

        out = StringIO()
        call_command("send_welcome_email", "--dry-run", stdout=out)
        output = out.getvalue()

        # Bob (DELIVERED) excluded; Alice (FAILED) + Carol (no row) included.
        assert "2 of 3 bulk-imported subscribers still need" in output
