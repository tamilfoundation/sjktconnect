"""
Compose a one-off WELCOME broadcast for a freshly-imported opted-in segment.

Creates a DRAFT Broadcast targeting a single ``source_tag`` (whatever
`import_email_batch` stamped on the batch). It is deliberately DRAFT-only:
an operator reviews it, optionally runs a test send, then releases it via
the normal send path — which drip-feeds under the daily Brevo cap, tracks
every delivery, adds the unsubscribe footer, and auto-deactivates bounces.

Usage:
  python manage.py compose_welcome_broadcast --source-tag TF_PARENTS_2026 --dry-run
  python manage.py compose_welcome_broadcast --source-tag TF_PARENTS_2026
  python manage.py compose_welcome_broadcast --source-tag TF_PARENTS_2026 \
      --subject "Welcome to Tamil Foundation" --template broadcasts/welcome_generic.html

Then to send (drip-feeds, tracked, self-cleaning):
  python manage.py send_broadcast --id <pk> --test-recipients you@example.com   # preview
  python manage.py send_broadcast --id <pk>                                     # release
"""

from django.core.management.base import BaseCommand, CommandError
from django.template.loader import render_to_string
from django.template import TemplateDoesNotExist

from broadcasts.models import Broadcast
from broadcasts.services.audience import get_filtered_subscribers

DEFAULT_SUBJECT = "Welcome to SJK(T) Connect — Tamil School Intelligence"
DEFAULT_TEMPLATE = "broadcasts/welcome_generic.html"


class Command(BaseCommand):
    help = "Compose a DRAFT welcome broadcast for one imported source_tag segment."

    def add_arguments(self, parser):
        parser.add_argument("--source-tag", required=True, help="Segment tag set by import_email_batch, e.g. TF_PARENTS_2026.")
        parser.add_argument("--subject", default=DEFAULT_SUBJECT, help="Email subject line.")
        parser.add_argument("--template", default=DEFAULT_TEMPLATE, help="Inner-content template path.")
        parser.add_argument("--dry-run", action="store_true", help="Preview audience without creating the draft.")

    def handle(self, *args, **options):
        source_tag = options["source_tag"].strip()
        subject = options["subject"]
        template = options["template"]
        dry_run = options["dry_run"]

        if not source_tag:
            raise CommandError("--source-tag must not be empty.")

        audience_filter = {"source_tag": source_tag}
        audience = get_filtered_subscribers(audience_filter)
        count = audience.count()

        self.stdout.write(f"Segment '{source_tag}': {count} active subscriber(s)")
        if count == 0:
            self.stdout.write(self.style.WARNING(
                "  No active subscribers with that source_tag. "
                "Did import_email_batch run with the same --source-tag?"
            ))

        try:
            html = render_to_string(template, {})
        except TemplateDoesNotExist:
            raise CommandError(f"Template not found: {template}")

        if dry_run:
            self.stdout.write("\nSample recipients (first 5):")
            for sub in audience[:5]:
                self.stdout.write(f"  - {sub.name or '(no name)'} <{sub.email}>")
            self.stdout.write(f"\nSubject:  {subject}")
            self.stdout.write(f"Template: {template}")
            self.stdout.write("\nDRY RUN — no draft created. Re-run without --dry-run to create it.")
            return

        broadcast = Broadcast.objects.create(
            subject=subject,
            html_content=html,
            audience_filter=audience_filter,
            kind=Broadcast.Kind.WELCOME,
            status=Broadcast.Status.DRAFT,
            recipient_count=count,
        )
        self.stdout.write(self.style.SUCCESS(
            f"\nDRAFT welcome broadcast #{broadcast.pk} created for '{source_tag}' "
            f"({count} recipients)."
        ))
        self.stdout.write(
            "\nNext steps:"
            f"\n  Preview:  python manage.py send_broadcast --id {broadcast.pk} --test-recipients you@example.com"
            f"\n  Release:  python manage.py send_broadcast --id {broadcast.pk}"
            "\n  (sends drip-feed under the daily cap; delivery is tracked and bounces auto-deactivate)"
        )
