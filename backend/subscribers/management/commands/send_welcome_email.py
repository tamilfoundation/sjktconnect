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
        dry_run = options["dry_run"]
        limit = options["limit"]

        # Check if welcome broadcast already exists
        existing = Broadcast.objects.filter(
            subject="Introducing SJK(T) Connect — Tamil School Intelligence for Our Community",
        ).first()

        if existing and existing.status == "SENT":
            self.stdout.write("Welcome broadcast already sent (ID: %d)." % existing.pk)
            return

        html_content = render_to_string(
            "broadcasts/welcome_import.html",
            {"name": ""},  # Name is personalised per-recipient by the wrapper
        )
        text_content = strip_tags(html_content)

        if dry_run:
            from subscribers.models import Subscriber
            count = Subscriber.objects.filter(
                source="BULK_IMPORT", is_active=True
            ).count()
            self.stdout.write(
                "DRY RUN — would send welcome email to %d bulk-imported subscribers "
                "(batch limit: %d)." % (count, limit)
            )
            return

        broadcast = Broadcast.objects.create(
            subject="Introducing SJK(T) Connect — Tamil School Intelligence for Our Community",
            html_content=html_content,
            text_content=text_content,
            audience_filter={
                "category": "",
                "source": "BULK_IMPORT",
                "limit": limit,
            },
            status=Broadcast.Status.DRAFT,
        )

        send_broadcast(broadcast.pk)
        self.stdout.write(
            self.style.SUCCESS("Welcome broadcast %d sent." % broadcast.pk)
        )
