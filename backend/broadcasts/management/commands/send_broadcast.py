"""Management command to send a broadcast by ID.

Usage:
    python manage.py send_broadcast --id <broadcast_pk>

Designed for Cloud Run Job execution where a web request
is not appropriate.
"""

from django.core.management.base import BaseCommand, CommandError

from broadcasts.models import Broadcast
from broadcasts.services.sender import send_broadcast


class Command(BaseCommand):
    help = "Send a draft broadcast to its filtered audience via Brevo."

    def add_arguments(self, parser):
        parser.add_argument(
            "--id",
            type=int,
            required=True,
            help="Primary key of the Broadcast to send.",
        )

    def handle(self, *args, **options):
        broadcast_id = options["id"]

        try:
            broadcast = Broadcast.objects.get(pk=broadcast_id)
        except Broadcast.DoesNotExist:
            raise CommandError("Broadcast with ID %d does not exist." % broadcast_id)

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
