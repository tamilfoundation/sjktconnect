"""
Resume sending broadcasts that are stuck in SENDING status.

Finds all broadcasts in SENDING status with PENDING recipients and
sends the next batch. Designed to be called daily by Cloud Scheduler
to drip-feed large broadcasts under Brevo's daily email limit.

Usage:
    python manage.py resume_sending
    python manage.py resume_sending --batch-size 250
    python manage.py resume_sending --dry-run
"""

from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Max
from django.utils import timezone

from broadcasts.models import Broadcast, BroadcastRecipient
from broadcasts.services.sender import resume_broadcast

# How far back the post-run FAILED sweep looks. 7 days means a FAILED
# broadcast makes this DAILY job exit non-zero for a week — long enough
# that the Cloud Run console shows a red streak and the job-failure
# alert has multiple chances to fire (2026-06-11 incident: four digests
# sat FAILED for five weeks while every job involved kept exiting 0).
FAILED_SWEEP_DAYS = 7

# Minimum time between drain passes on the SAME broadcast. Prevents the
# 2026-07-05 double-send: fortnightly-digest cron fires at 09:00 MYT and
# resume-sending fires at 10:00 MYT the same day, so both crons touched
# the same broadcast an hour apart and drained today's full Brevo quota
# in one calendar day instead of spreading across two.
#
# 20h (not 24h) gives a small forgiveness margin so a drain that fired
# at 10:00 yesterday still runs at 10:00 today — the cron cadence itself
# jitters by a few minutes so a strict 24h would silently skip the
# intended daily drain every other day.
MIN_HOURS_BETWEEN_BATCHES = 20


def _hours_since_last_batch(broadcast):
    """Return hours since the most recent recipient was marked SENT.

    Returns None when no recipient has ever been sent (fresh broadcast
    with initial send failed, or manually flipped to SENDING) -- callers
    should treat None as "no recent batch, safe to drain".
    """
    latest = broadcast.recipients.filter(
        status=BroadcastRecipient.DeliveryStatus.SENT,
        sent_at__isnull=False,
    ).aggregate(latest=Max("sent_at"))["latest"]
    if latest is None:
        return None
    return (timezone.now() - latest).total_seconds() / 3600.0


class Command(BaseCommand):
    help = "Resume sending broadcasts in SENDING status (batch mode)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--batch-size",
            type=int,
            default=250,
            help="Max emails to send per broadcast (default: 250)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be sent without sending",
        )

    def handle(self, *args, **options):
        batch_size = options["batch_size"]
        dry_run = options["dry_run"]

        sending = Broadcast.objects.filter(
            status=Broadcast.Status.SENDING
        ).order_by("created_at")

        if not sending.exists():
            self.stdout.write("No broadcasts in SENDING status.")
            self._fail_on_recent_failed_broadcasts(dry_run)
            return

        for broadcast in sending:
            pending = broadcast.recipients.filter(
                status=BroadcastRecipient.DeliveryStatus.PENDING
            ).count()
            total = broadcast.recipients.count()
            sent = broadcast.recipients.filter(
                status=BroadcastRecipient.DeliveryStatus.SENT
            ).count()

            if pending == 0:
                self.stdout.write(
                    f"Broadcast {broadcast.pk}: no pending recipients, "
                    f"marking SENT."
                )
                if not dry_run:
                    broadcast.status = Broadcast.Status.SENT
                    broadcast.save(update_fields=["status", "updated_at"])
                continue

            self.stdout.write(
                f"Broadcast {broadcast.pk} ({broadcast.subject[:50]}): "
                f"{sent}/{total} sent, {pending} pending"
            )

            hours_since = _hours_since_last_batch(broadcast)
            if hours_since is not None and hours_since < MIN_HOURS_BETWEEN_BATCHES:
                self.stdout.write(
                    self.style.WARNING(
                        f"  Skipping — last batch was {hours_since:.1f}h ago "
                        f"(< {MIN_HOURS_BETWEEN_BATCHES}h min gap). "
                        f"Drains on next daily run."
                    )
                )
                continue

            if dry_run:
                to_send = min(pending, batch_size)
                self.stdout.write(
                    f"  DRY RUN — would send next {to_send} emails"
                )
                continue

            result = resume_broadcast(broadcast.pk, batch_size=batch_size)
            if result:
                remaining = result.recipients.filter(
                    status=BroadcastRecipient.DeliveryStatus.PENDING
                ).count()
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  Batch sent. Status: {result.status}. "
                        f"Remaining: {remaining}"
                    )
                )

        self._fail_on_recent_failed_broadcasts(dry_run)

    def _fail_on_recent_failed_broadcasts(self, dry_run):
        """Exit non-zero while any recently FAILED broadcast needs attention.

        A FAILED broadcast is rare now (quota exhaustion stays SENDING),
        so one means something genuinely broke. Failing this daily job
        turns that into a visible red execution in the Cloud Run console
        and feeds the job-failure Cloud Monitoring alert — closing the
        monitoring gap that let the 2026-06-11 stuck-digest incident hide
        for five weeks. Resolve by fixing the cause and setting the
        broadcast to CANCELLED (abandoned) or SENDING (re-attempt).
        """
        cutoff = timezone.now() - timedelta(days=FAILED_SWEEP_DAYS)
        failed = list(
            Broadcast.objects.filter(
                status=Broadcast.Status.FAILED,
                updated_at__gte=cutoff,
            ).values_list("pk", flat=True)
        )
        if not failed:
            return
        message = (
            f"BROADCAST_FAILED_ALERT: broadcasts {failed} are FAILED "
            f"(updated within {FAILED_SWEEP_DAYS} days). Investigate, then "
            "set each to CANCELLED (abandon) or SENDING (re-attempt)."
        )
        if dry_run:
            self.stdout.write(self.style.WARNING(f"DRY RUN — {message}"))
            return
        raise CommandError(message)
