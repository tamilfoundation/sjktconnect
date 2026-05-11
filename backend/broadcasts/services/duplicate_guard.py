"""
Duplicate-broadcast guard.

The 2026-05-02 incident saw 4 ``Broadcast`` rows created in a 40-minute
window for the same April monthly digest, because ``compose_monthly_blast``
re-ran four times during a crashed Claude session and the command had no
idempotency check. This module is the check that should have existed.

Match key for date-coverage broadcasts (MONTHLY_BLAST / NEWS_DIGEST /
PARLIAMENT_WATCH): ``(kind, coverage_start_date, coverage_end_date)`` in
a recent window. For URGENT_ALERT (no coverage dates), match on
``(kind, subject)`` in the same window.

Status filter is SENT or SENDING — a prior DRAFT shouldn't block a
retry, and a FAILED row should be re-attemptable.
"""

import logging
from datetime import date, timedelta

from django.utils import timezone

from broadcasts.models import Broadcast

logger = logging.getLogger(__name__)

DEFAULT_WINDOW_DAYS = 7


def check_duplicate(
    kind: str,
    coverage_start: date | None = None,
    coverage_end: date | None = None,
    subject: str | None = None,
    window_days: int = DEFAULT_WINDOW_DAYS,
) -> Broadcast | None:
    """Return an existing in-flight/sent Broadcast that matches, or None.

    For broadcasts with a coverage window, pass ``coverage_start`` and
    ``coverage_end``. For broadcasts without coverage dates (urgent
    alerts), pass ``subject`` for exact-match dedupe.

    ``window_days`` bounds the lookback so re-sends after a recipient-list
    correction or a spam-flag fix aren't blocked indefinitely.
    """
    cutoff = timezone.now() - timedelta(days=window_days)
    qs = Broadcast.objects.filter(
        kind=kind,
        status__in=[Broadcast.Status.SENT, Broadcast.Status.SENDING],
        created_at__gte=cutoff,
    )

    if coverage_start is not None and coverage_end is not None:
        qs = qs.filter(
            coverage_start_date=coverage_start,
            coverage_end_date=coverage_end,
        )
    elif subject is not None:
        qs = qs.filter(subject=subject)
    else:
        # No usable match key — caller didn't supply enough info.
        logger.warning(
            "check_duplicate(kind=%s) called without coverage dates or subject — "
            "cannot dedupe",
            kind,
        )
        return None

    return qs.order_by("-created_at").first()


def format_block_message(existing: Broadcast) -> str:
    """Human-readable message for the abort path in compose commands."""
    coverage = ""
    if existing.coverage_start_date and existing.coverage_end_date:
        coverage = f" {existing.coverage_start_date} \u2192 {existing.coverage_end_date}"
    return (
        f"A {existing.get_status_display().lower()} broadcast for "
        f"{existing.get_kind_display()}{coverage} already exists "
        f"(id={existing.pk}, created {existing.created_at:%Y-%m-%d %H:%M}). "
        "Pass --force-duplicate to override."
    )
