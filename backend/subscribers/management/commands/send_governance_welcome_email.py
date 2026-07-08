"""
Django management command: Send welcome emails to governance leader subscribers

Sends welcome email to TF_2018 governance leader subscribers via Brevo API.

Usage:
  python manage.py send_governance_welcome_email --dry-run
  python manage.py send_governance_welcome_email --limit 300
"""

import os
import requests
from django.core.management.base import BaseCommand
from django.template.loader import render_to_string
from django.conf import settings

from subscribers.models import Subscriber

BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"
SENDER_EMAIL = "noreply@tamilschool.org"
SENDER_NAME = "SJK(T) Connect"


class Command(BaseCommand):
    help = "Send welcome emails to governance leader subscribers"

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview what would be sent without actually sending',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=300,
            help='Max emails to send per run (Brevo free tier: 300/day). Default: 300',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        limit = options['limit']

        self.stdout.write("=" * 100)
        self.stdout.write(
            "SENDING WELCOME EMAILS TO GOVERNANCE LEADERS"
            + (" (DRY RUN)" if dry_run else "")
        )
        self.stdout.write("=" * 100)

        # Find all TF_2018 subscribers
        self.stdout.write("\nFinding TF_2018 governance leader subscribers...")
        tf_2018_subscribers = Subscriber.objects.filter(
            source_tag__startswith="TF_2018",
            is_active=True,
        ).order_by('subscribed_at')

        total_count = tf_2018_subscribers.count()
        self.stdout.write(f"  Total TF_2018 subscribers: {total_count}")

        # For this version, we'll just send to all who don't have a flag
        # (In a real scenario, we'd track sent status per subscriber or in a broadcast log)
        to_send = tf_2018_subscribers[:limit]
        send_count = to_send.count()

        self.stdout.write(f"  Sending to: {send_count} subscribers (limit: {limit})")

        if dry_run:
            self._simulate_send(to_send, total_count)
        else:
            self._send_emails(to_send, total_count)

    def _simulate_send(self, subscribers, total_count):
        """Show what would be sent (dry run)."""
        self.stdout.write("\n" + "=" * 100)
        self.stdout.write("SIMULATION (DRY RUN)")
        self.stdout.write("=" * 100)

        self.stdout.write(f"\nWould send emails to {subscribers.count()} subscribers")
        self.stdout.write(f"Total remaining: {total_count - subscribers.count()}")

        # Show sample
        self.stdout.write("\nSample recipients (first 5):")
        for i, sub in enumerate(subscribers[:5], 1):
            self.stdout.write(f"  {i}. {sub.name} <{sub.email}> (roles: {sub.source_tag})")

        self.stdout.write("\nSubject: Introducing SJK(T) Connect - Tamil School Intelligence")
        self.stdout.write("Template: welcome_governance_2018.html")
        self.stdout.write("\n(This is a dry run. No emails have been sent.)")
        self.stdout.write("To send, run without --dry-run flag")

    def _send_emails(self, subscribers, total_count):
        """Actually send the welcome emails via Brevo API."""
        self.stdout.write("\n" + "=" * 100)
        self.stdout.write("SENDING EMAILS")
        self.stdout.write("=" * 100)

        # Prepare email subject and body
        subject = "Introducing SJK(T) Connect - Tamil School Intelligence"
        html_message = render_to_string('broadcasts/welcome_governance_2018.html', {})

        # Get Brevo API key
        api_key = os.environ.get("BREVO_API_KEY")
        if not api_key:
            raise ValueError("BREVO_API_KEY environment variable is required")

        sent_count = 0
        failed_count = 0

        try:
            for subscriber in subscribers:
                # Build Brevo API request
                payload = {
                    "sender": {"name": SENDER_NAME, "email": SENDER_EMAIL},
                    "to": [{"email": subscriber.email, "name": subscriber.name or ""}],
                    "subject": subject,
                    "htmlContent": html_message,
                }

                headers = {
                    "api-key": api_key,
                    "Content-Type": "application/json",
                }

                # Send via Brevo
                response = requests.post(
                    BREVO_API_URL,
                    json=payload,
                    headers=headers,
                    timeout=10
                )

                if response.status_code in (200, 201):
                    sent_count += 1
                    if sent_count % 50 == 0:
                        self.stdout.write(f"  Sent {sent_count} emails...")
                else:
                    failed_count += 1
                    self.stdout.write(
                        f"  WARNING: Failed to send to {subscriber.email} "
                        f"(status {response.status_code})"
                    )

            self.stdout.write("\n" + "=" * 100)
            self.stdout.write("EMAILS SENT")
            self.stdout.write("=" * 100)
            self.stdout.write(f"\nEmails sent: {sent_count}")
            if failed_count > 0:
                self.stdout.write(f"Failed: {failed_count}")
            self.stdout.write(f"Total remaining: {total_count - sent_count}")
            self.stdout.write(f"Subject: {subject}")

        except Exception as e:
            self.stdout.write(f"\nError sending emails: {e}")
            raise
