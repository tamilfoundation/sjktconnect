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

from django.core.management.base import BaseCommand

from broadcasts.models import Broadcast, BroadcastRecipient
from broadcasts.services.sender import resume_broadcast


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
