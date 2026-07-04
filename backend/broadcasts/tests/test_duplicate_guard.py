"""Tests for the duplicate-broadcast guard."""

from datetime import date, timedelta

import pytest
from django.db import IntegrityError, transaction
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


@pytest.mark.django_db
class TestUniqueCoverageConstraint:
    """DB-level backstop (migration broadcasts/0008, audit 2026-07-01)
    for the check-then-create race that caused the 2026-05-02 4-broadcast
    incident. When two schedulers both pass the app-layer guard within
    the check window, the DB rejects the second insert."""

    def test_duplicate_sent_broadcast_raises_integrityerror(self):
        Broadcast.objects.create(
            subject="April digest",
            kind=Broadcast.Kind.MONTHLY_BLAST,
            coverage_start_date=date(2026, 4, 1),
            coverage_end_date=date(2026, 4, 30),
            status=Broadcast.Status.SENT,
        )
        with pytest.raises(IntegrityError), transaction.atomic():
            Broadcast.objects.create(
                subject="April digest (dup)",
                kind=Broadcast.Kind.MONTHLY_BLAST,
                coverage_start_date=date(2026, 4, 1),
                coverage_end_date=date(2026, 4, 30),
                status=Broadcast.Status.SENT,
            )

    def test_draft_status_bypasses_constraint(self):
        """A DRAFT can coexist with a SENT for the same window —
        allows re-composition after a failed send."""
        Broadcast.objects.create(
            subject="April digest",
            kind=Broadcast.Kind.MONTHLY_BLAST,
            coverage_start_date=date(2026, 4, 1),
            coverage_end_date=date(2026, 4, 30),
            status=Broadcast.Status.SENT,
        )
        Broadcast.objects.create(
            subject="April digest (retry)",
            kind=Broadcast.Kind.MONTHLY_BLAST,
            coverage_start_date=date(2026, 4, 1),
            coverage_end_date=date(2026, 4, 30),
            status=Broadcast.Status.DRAFT,
        )
        assert Broadcast.objects.count() == 2

    def test_null_coverage_bypasses_constraint(self):
        """Historical rows with null coverage dates (pre-Sprint-24) don't
        conflict — Postgres treats NULLs as distinct in unique indexes,
        and the constraint additionally requires both dates non-null."""
        for i in range(3):
            Broadcast.objects.create(
                subject=f"legacy urgent {i}",
                kind=Broadcast.Kind.URGENT_ALERT,
                status=Broadcast.Status.SENT,
            )
        assert Broadcast.objects.count() == 3

    def test_different_kinds_dont_conflict(self):
        Broadcast.objects.create(
            subject="April digest",
            kind=Broadcast.Kind.MONTHLY_BLAST,
            coverage_start_date=date(2026, 4, 1),
            coverage_end_date=date(2026, 4, 30),
            status=Broadcast.Status.SENT,
        )
        Broadcast.objects.create(
            subject="News digest 15-30 Apr",
            kind=Broadcast.Kind.NEWS_DIGEST,
            coverage_start_date=date(2026, 4, 1),
            coverage_end_date=date(2026, 4, 30),
            status=Broadcast.Status.SENT,
        )
        assert Broadcast.objects.count() == 2
