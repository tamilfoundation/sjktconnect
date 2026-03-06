"""
Management command to process inbound feedback emails.

Runs the full feedback pipeline:
1. Fetch new emails from Gmail (unless --skip-fetch)
2. Classify all UNCLASSIFIED emails with Gemini AI
3. Auto-respond to all PENDING emails (unless --dry-run)

Usage:
    python manage.py process_feedback
    python manage.py process_feedback --skip-fetch
    python manage.py process_feedback --dry-run
    python manage.py process_feedback --skip-fetch --dry-run
"""

from django.core.management.base import BaseCommand

from feedback.models import InboundEmail
from feedback.services.classifier import classify_email
from feedback.services.gmail_fetcher import fetch_new_emails
from feedback.services.responder import auto_respond


class Command(BaseCommand):
    help = "Process inbound feedback: fetch, classify, and auto-respond."

    def add_arguments(self, parser):
        parser.add_argument(
            "--skip-fetch",
            action="store_true",
            help="Skip fetching new emails from Gmail.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Classify emails but skip sending auto-responses.",
        )

    def handle(self, *args, **options):
        skip_fetch = options["skip_fetch"]
        dry_run = options["dry_run"]

        self.stdout.write(self.style.MIGRATE_HEADING("Processing feedback emails"))
        self.stdout.write("")

        # Step 1: Fetch new emails
        fetch_count = 0
        if skip_fetch:
            self.stdout.write("Step 1: Fetch — SKIPPED (--skip-fetch)")
        else:
            self.stdout.write("Step 1: Fetching new emails from Gmail...")
            result = fetch_new_emails()
            fetch_count = result["fetched"]
            self.stdout.write(
                f"  Fetched: {result['fetched']}, "
                f"Skipped: {result['skipped']}, "
                f"Errors: {len(result['errors'])}"
            )
            for error in result["errors"]:
                self.stderr.write(self.style.ERROR(f"  {error}"))

        # Step 2: Classify unclassified emails
        unclassified = InboundEmail.objects.filter(classification="UNCLASSIFIED")
        classify_count = unclassified.count()
        self.stdout.write(
            f"\nStep 2: Classifying {classify_count} unclassified emails..."
        )

        classified = 0
        for email in unclassified:
            classify_email(email)
            email.refresh_from_db()
            if email.classification != "UNCLASSIFIED":
                classified += 1
                self.stdout.write(
                    f"  {email.gmail_message_id}: {email.classification}"
                    f"{' [ESCALATED]' if email.escalated else ''}"
                )

        self.stdout.write(f"  Classified: {classified}/{classify_count}")

        # Step 3: Auto-respond to pending emails
        pending = InboundEmail.objects.filter(response_status="PENDING").exclude(
            classification="UNCLASSIFIED"
        )
        respond_count = pending.count()

        if dry_run:
            self.stdout.write(
                f"\nStep 3: Auto-respond — SKIPPED (--dry-run, "
                f"{respond_count} would be processed)"
            )
        else:
            self.stdout.write(
                f"\nStep 3: Auto-responding to {respond_count} pending emails..."
            )
            responded = 0
            for email in pending:
                auto_respond(email)
                email.refresh_from_db()
                if email.response_status in ("AUTO_RESPONDED", "RESOLVED"):
                    responded += 1
            self.stdout.write(f"  Responded: {responded}/{respond_count}")

        # Summary
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Summary:"))
        self.stdout.write(f"  Fetched:    {fetch_count}")
        self.stdout.write(f"  Classified: {classified}/{classify_count}")
        if not dry_run:
            self.stdout.write(f"  Responded:  {responded}/{respond_count}")
        else:
            self.stdout.write(f"  Respond:    {respond_count} pending (dry run)")
