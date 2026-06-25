"""Management command to send a broadcast by ID.

Usage:
    python manage.py send_broadcast --id <broadcast_pk>
    python manage.py send_broadcast --id <broadcast_pk> --test-recipients a@x.com,b@y.com

Designed for Cloud Run Job execution where a web request
is not appropriate.
"""

from django.core.management.base import BaseCommand, CommandError

from broadcasts.models import Broadcast
from broadcasts.services.sender import send_broadcast, send_test


class Command(BaseCommand):
    help = "Send a draft broadcast to its filtered audience via Brevo."

    def add_arguments(self, parser):
        parser.add_argument(
            "--id",
            type=int,
            required=True,
            help="Primary key of the Broadcast to send.",
        )
        parser.add_argument(
            "--test-recipients",
            type=str,
            default="",
            help=(
                "Comma-separated email addresses for a TEST send. The "
                "broadcast stays in DRAFT — recipient_count and "
                "BroadcastRecipient rows are NOT touched. Use to sanity-"
                "check a Parliament Watch or Urgent Alert draft on your "
                "own inbox before releasing to all subscribers."
            ),
        )

    def handle(self, *args, **options):
        broadcast_id = options["id"]
        test_recipients_raw = options["test_recipients"].strip()

        try:
            broadcast = Broadcast.objects.get(pk=broadcast_id)
        except Broadcast.DoesNotExist:
            raise CommandError("Broadcast with ID %d does not exist." % broadcast_id)

        if test_recipients_raw:
            recipients = [
                e.strip() for e in test_recipients_raw.split(",") if e.strip()
            ]
            if not recipients:
                raise CommandError("--test-recipients was empty after parsing.")
            self.stdout.write(
                "TEST SEND of broadcast %d to %d recipient(s): %s"
                % (broadcast_id, len(recipients), ", ".join(recipients))
            )
            sent, failed = send_test(broadcast_id, recipients)
            self.stdout.write(
                self.style.SUCCESS(
                    "Test send done — %d sent, %d failed. Broadcast %d is still %s."
                    % (sent, failed, broadcast_id, broadcast.status)
                )
            )
            return

        if broadcast.status != Broadcast.Status.DRAFT:
            raise CommandError(
                "Broadcast %d is %s, not DRAFT. Only DRAFT broadcasts can be sent."
                % (broadcast_id, broadcast.status)
            )

        self.stdout.write(
            "Sending broadcast %d: %s" % (broadcast_id, broadcast.subject)
        )

        broadcast = send_broadcast(broadcast_id)

        self.stdout.write(
            self.style.SUCCESS(
                "Broadcast %d sent successfully — %d recipients."
                % (broadcast_id, broadcast.recipient_count)
            )
        )
