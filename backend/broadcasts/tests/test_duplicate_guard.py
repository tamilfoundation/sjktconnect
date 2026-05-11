"""Tests for the duplicate-broadcast guard."""

from datetime import date, timedelta

import pytest
from django.utils import timezone

from broadcasts.models import Broadcast
from broadcasts.services.duplicate_guard import (
    check_duplicate,
    format_block_message,
)


@pytest.mark.django_db
class TestCheckDuplicate:
    def test_returns_none_when_no_match(self):
        result = check_duplicate(
            kind=Broadcast.Kind.MONTHLY_BLAST,
            coverage_start=date(2026, 4, 1),
            coverage_end=date(2026, 4, 30),
        )
        assert result is None

    def test_blocks_when_sent_broadcast_exists_in_window(self):
        existing = Broadcast.objects.create(
            subject="April digest",
            kind=Broadcast.Kind.MONTHLY_BLAST,
            coverage_start_date=date(2026, 4, 1),
            coverage_end_date=date(2026, 4, 30),
            status=Broadcast.Status.SENT,
        )

        result = check_duplicate(
            kind=Broadcast.Kind.MONTHLY_BLAST,
            coverage_start=date(2026, 4, 1),
            coverage_end=date(2026, 4, 30),
        )
        assert result is not None
        assert result.pk == existing.pk

    def test_blocks_when_sending_broadcast_exists(self):
        Broadcast.objects.create(
            subject="In flight",
            kind=Broadcast.Kind.MONTHLY_BLAST,
            coverage_start_date=date(2026, 4, 1),
            coverage_end_date=date(2026, 4, 30),
            status=Broadcast.Status.SENDING,
        )

        result = check_duplicate(
            kind=Broadcast.Kind.MONTHLY_BLAST,
            coverage_start=date(2026, 4, 1),
            coverage_end=date(2026, 4, 30),
        )
        assert result is not None

    def test_ignores_draft_broadcast(self):
        Broadcast.objects.create(
            subject="Draft",
            kind=Broadcast.Kind.MONTHLY_BLAST,
            coverage_start_date=date(2026, 4, 1),
            coverage_end_date=date(2026, 4, 30),
            status=Broadcast.Status.DRAFT,
        )

        result = check_duplicate(
            kind=Broadcast.Kind.MONTHLY_BLAST,
            coverage_start=date(2026, 4, 1),
            coverage_end=date(2026, 4, 30),
        )
        assert result is None

    def test_ignores_failed_broadcast(self):
        Broadcast.objects.create(
            subject="Failed",
            kind=Broadcast.Kind.MONTHLY_BLAST,
            coverage_start_date=date(2026, 4, 1),
            coverage_end_date=date(2026, 4, 30),
            status=Broadcast.Status.FAILED,
        )

        result = check_duplicate(
            kind=Broadcast.Kind.MONTHLY_BLAST,
            coverage_start=date(2026, 4, 1),
            coverage_end=date(2026, 4, 30),
        )
        assert result is None

    def test_different_kind_does_not_match(self):
        Broadcast.objects.create(
            subject="April news",
            kind=Broadcast.Kind.NEWS_DIGEST,
            coverage_start_date=date(2026, 4, 1),
            coverage_end_date=date(2026, 4, 30),
            status=Broadcast.Status.SENT,
        )

        result = check_duplicate(
            kind=Broadcast.Kind.MONTHLY_BLAST,
            coverage_start=date(2026, 4, 1),
            coverage_end=date(2026, 4, 30),
        )
        assert result is None

    def test_different_coverage_dates_do_not_match(self):
        Broadcast.objects.create(
            subject="April digest",
            kind=Broadcast.Kind.MONTHLY_BLAST,
            coverage_start_date=date(2026, 4, 1),
            coverage_end_date=date(2026, 4, 30),
            status=Broadcast.Status.SENT,
        )

        result = check_duplicate(
            kind=Broadcast.Kind.MONTHLY_BLAST,
            coverage_start=date(2026, 5, 1),
            coverage_end=date(2026, 5, 31),
        )
        assert result is None

    def test_window_expiry_allows_resend(self):
        old = Broadcast.objects.create(
            subject="Old",
            kind=Broadcast.Kind.MONTHLY_BLAST,
            coverage_start_date=date(2026, 4, 1),
            coverage_end_date=date(2026, 4, 30),
            status=Broadcast.Status.SENT,
        )
        Broadcast.objects.filter(pk=old.pk).update(
            created_at=timezone.now() - timedelta(days=30)
        )

        result = check_duplicate(
            kind=Broadcast.Kind.MONTHLY_BLAST,
            coverage_start=date(2026, 4, 1),
            coverage_end=date(2026, 4, 30),
            window_days=7,
        )
        assert result is None

    def test_subject_match_for_urgent_alerts(self):
        existing = Broadcast.objects.create(
            subject="URGENT: Tamil school closure announcement",
            kind=Broadcast.Kind.URGENT_ALERT,
            status=Broadcast.Status.SENT,
        )

        result = check_duplicate(
            kind=Broadcast.Kind.URGENT_ALERT,
            subject="URGENT: Tamil school closure announcement",
        )
        assert result is not None
        assert result.pk == existing.pk

    def test_subject_match_kind_isolation(self):
        Broadcast.objects.create(
            subject="URGENT: Something",
            kind=Broadcast.Kind.URGENT_ALERT,
            status=Broadcast.Status.SENT,
        )

        # MONTHLY_BLAST with same subject should NOT match — different kind.
        result = check_duplicate(
            kind=Broadcast.Kind.MONTHLY_BLAST,
            subject="URGENT: Something",
        )
        assert result is None

    def test_no_match_key_returns_none(self):
        Broadcast.objects.create(
            subject="X",
            kind=Broadcast.Kind.MONTHLY_BLAST,
            status=Broadcast.Status.SENT,
        )
        # No coverage dates AND no subject — guard cannot match.
        result = check_duplicate(kind=Broadcast.Kind.MONTHLY_BLAST)
        assert result is None


@pytest.mark.django_db
class TestFormatBlockMessage:
    def test_message_includes_coverage_when_present(self):
        broadcast = Broadcast.objects.create(
            subject="April digest",
            kind=Broadcast.Kind.MONTHLY_BLAST,
            coverage_start_date=date(2026, 4, 1),
            coverage_end_date=date(2026, 4, 30),
            status=Broadcast.Status.SENT,
        )
        msg = format_block_message(broadcast)
        assert "Monthly Blast" in msg
        assert "2026-04-01" in msg
        assert "2026-04-30" in msg
        assert "--force-duplicate" in msg

    def test_message_omits_coverage_for_urgent_alerts(self):
        broadcast = Broadcast.objects.create(
            subject="URGENT: X",
            kind=Broadcast.Kind.URGENT_ALERT,
            status=Broadcast.Status.SENT,
        )
        msg = format_block_message(broadcast)
        assert "Urgent Alert" in msg
        assert "--force-duplicate" in msg
