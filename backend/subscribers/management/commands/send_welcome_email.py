"""
Send the welcome/introduction email to bulk-imported subscribers.

Only targets subscribers with source=BULK_IMPORT who haven't received
a welcome broadcast yet. Sends in batches to respect Brevo rate limits.

Usage:
    python manage.py send_welcome_email
    python manage.py send_welcome_email --dry-run
    python manage.py send_welcome_email --limit 300
"""

from django.core.management.base import BaseCommand
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from broadcasts.models import Broadcast
from broadcasts.services.sender import send_broadcast


class Command(BaseCommand):
    help = "Send welcome email to bulk-imported subscribers."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview without sending",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=300,
            help="Max recipients per batch (default: 300, Brevo free tier daily limit)",
        )

    def handle(self, *args, **options):
        from broadcasts.models import BroadcastRecipient
        from subscribers.models import Subscriber

        dry_run = options["dry_run"]
        limit = options["limit"]

        subject = "Introducing SJK(T) Connect — Tamil School Intelligence for Our Community"

        # Find all bulk-imported active subscribers
        all_bulk = Subscriber.objects.filter(
            source="BULK_IMPORT", is_active=True
        )

        # Exclude subscribers who already received a welcome broadcast.
        # Filter on SENT *or* DELIVERED: the Brevo webhook (Sprint 8.5)
        # transitions BroadcastRecipient.status from SENT to DELIVERED
        # within seconds of inbox confirmation, so a retry run hours
        # later sees status=DELIVERED for the successful recipients —
        # if we filtered on SENT alone, those people would be retried
        # and receive the welcome twice. (Discovered 2026-04-28 when
        # broadcasts 70+71 double-sent to 14 recipients.)
        sent_broadcasts = Broadcast.objects.filter(subject=subject, status="SENT")
        already_sent_ids = BroadcastRecipient.objects.filter(
            broadcast__in=sent_broadcasts,
            status__in=("SENT", "DELIVERED"),
        ).values_list("subscriber_id", flat=True)

        remaining = all_bulk.exclude(pk__in=already_sent_ids)
        count = remaining.count()

        if count == 0:
            self.stdout.write("All bulk-imported subscribers have already received the welcome email.")
            return

        if dry_run:
            self.stdout.write(
                "DRY RUN — %d of %d bulk-imported subscribers still need the welcome email "
                "(batch limit: %d)." % (count, all_bulk.count(), limit)
            )
            return

        html_content = render_to_string(
            "broadcasts/welcome_import.html",
            {"name": ""},  # Name is personalised per-recipient by the wrapper
        )
        text_content = strip_tags(html_content)

        # Store the IDs of remaining subscribers so the audience filter can target them
        remaining_ids = list(remaining[:limit].values_list("pk", flat=True))

        broadcast = Broadcast.objects.create(
            subject=subject,
            html_content=html_content,
            text_content=text_content,
            audience_filter={
                "category": "",
                "source": "BULK_IMPORT",
                "subscriber_ids": remaining_ids,
            },
            status=Broadcast.Status.DRAFT,
        )

        send_broadcast(broadcast.pk)
        self.stdout.write(
            self.style.SUCCESS(
                "Welcome broadcast %d sent to %d subscribers." % (broadcast.pk, len(remaining_ids))
            )
        )
