"""Tests for send_broadcast management command."""

from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from broadcasts.models import Broadcast
from subscribers.models import Subscriber


@pytest.fixture
def subscriber(db):
    return Subscriber.objects.create(
        email="cmd@example.com", name="Cmd User", is_active=True
    )


@pytest.fixture
def draft_broadcast(db):
    return Broadcast.objects.create(
        subject="Command Test",
        html_content="<p>Via command</p>",
        audience_filter={},
        status=Broadcast.Status.DRAFT,
    )


@pytest.mark.django_db
class TestSendBroadcastCommand:
    """Tests for the send_broadcast management command."""

    def test_sends_draft_broadcast(self, draft_broadcast, subscriber):
        """Command sends a DRAFT broadcast and prints success."""
        with patch.dict("os.environ", {}, clear=False):
            import os
            os.environ.pop("BREVO_API_KEY", None)

            call_command("send_broadcast", id=draft_broadcast.pk)

        draft_broadcast.refresh_from_db()
        assert draft_broadcast.status == Broadcast.Status.SENT

    def test_rejects_nonexistent_broadcast(self):
        """Command raises error for non-existent broadcast ID."""
        with pytest.raises(CommandError, match="does not exist"):
            call_command("send_broadcast", id=99999)

    def test_rejects_non_draft_broadcast(self, db):
        """Command raises error for non-DRAFT broadcast."""
        broadcast = Broadcast.objects.create(
            subject="Already Sent",
            status=Broadcast.Status.SENT,
        )
        with pytest.raises(CommandError, match="not DRAFT"):
            call_command("send_broadcast", id=broadcast.pk)

    def test_rejects_sending_broadcast(self, db):
        """Command raises error for broadcast in SENDING status."""
        broadcast = Broadcast.objects.create(
            subject="In Progress",
            status=Broadcast.Status.SENDING,
        )
        with pytest.raises(CommandError, match="not DRAFT"):
            call_command("send_broadcast", id=broadcast.pk)
