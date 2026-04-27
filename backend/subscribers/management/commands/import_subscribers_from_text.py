"""
Bulk-import subscribers from a free-form text file of email addresses.

Tolerates any of these formats per line (or comma-separated within lines):
  - bare:           foo@bar.com
  - angle-bracket:  <foo@bar.com>
  - named:          "Foo Name" <foo@bar.com>
  - whitespace + commas mixed freely

Lowercases + dedupes. Reports total parsed / unique / already-subscribed /
to-add. Default --dry-run prints the report without writing. --commit
actually creates Subscriber rows + all 3 preferences enabled by default.

Usage:
    python manage.py import_subscribers_from_text path/to/emails.txt
    python manage.py import_subscribers_from_text path/to/emails.txt --commit \
        --source-tag TF_NETWORK_2026_04
    python manage.py import_subscribers_from_text path/to/emails.txt --commit \
        --categories MONTHLY_BLAST,PARLIAMENT_WATCH

The command does NOT send a confirmation email — these are direct creates.
For opt-in confirmation flow, use the public POST /api/v1/subscribers/subscribe/
endpoint instead.
"""

import re
from pathlib import Path

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_email

from subscribers.models import Subscriber, SubscriptionPreference


# Matches RFC-5322-ish: most real-world addresses without going overboard.
# Captures the address itself; surrounding name / quotes / brackets / commas
# are ignored.
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


class Command(BaseCommand):
    help = "Bulk-import subscribers from a free-form text file of emails."

    def add_arguments(self, parser):
        parser.add_argument("file", type=str, help="Path to the email list text file")
        parser.add_argument(
            "--commit",
            action="store_true",
            help="Actually write to DB. Default is dry-run.",
        )
        parser.add_argument(
            "--source-tag",
            type=str,
            default="BULK_TEXT_IMPORT",
            help="Stored on Subscriber.source_tag for provenance.",
        )
        parser.add_argument(
            "--categories",
            type=str,
            default="",
            help=(
                "Comma-separated list of preference categories to enable "
                "(default: all three — PARLIAMENT_WATCH, NEWS_WATCH, "
                "MONTHLY_BLAST). Choices: "
                + ", ".join(c for c, _ in SubscriptionPreference.CATEGORY_CHOICES)
            ),
        )
        parser.add_argument(
            "--name-fallback",
            type=str,
            default="",
            help="Subscriber.name to use when the line has no display name.",
        )

    def handle(self, *args, **options):
        path = Path(options["file"])
        if not path.exists():
            raise CommandError(f"File not found: {path}")

        commit = options["commit"]
        source_tag = options["source_tag"]
        name_fallback = options["name_fallback"]

        if options["categories"]:
            requested = [c.strip().upper() for c in options["categories"].split(",")]
            valid = {c for c, _ in SubscriptionPreference.CATEGORY_CHOICES}
            unknown = set(requested) - valid
            if unknown:
                raise CommandError(
                    f"Unknown categories: {unknown}. "
                    f"Choices: {sorted(valid)}"
                )
            categories = requested
        else:
            categories = [c for c, _ in SubscriptionPreference.CATEGORY_CHOICES]

        text = path.read_text(encoding="utf-8", errors="replace")

        # Parse + dedupe
        all_matches = EMAIL_RE.findall(text)
        seen = set()
        unique = []
        for m in all_matches:
            lc = m.strip().lower()
            try:
                validate_email(lc)
            except ValidationError:
                continue
            if lc in seen:
                continue
            seen.add(lc)
            unique.append(lc)

        # Compare against DB
        existing_emails = set(
            Subscriber.objects.filter(email__in=unique).values_list("email", flat=True)
        )
        to_add = [e for e in unique if e not in existing_emails]

        # Report
        self.stdout.write("")
        self.stdout.write(f"  Total emails parsed:    {len(all_matches)}")
        self.stdout.write(f"  Unique (deduped):       {len(unique)}")
        self.stdout.write(f"  Already in DB:          {len(existing_emails)}")
        self.stdout.write(f"  To add:                 {len(to_add)}")
        self.stdout.write(f"  Source tag:             {source_tag}")
        self.stdout.write(f"  Categories enabled:     {', '.join(categories)}")
        self.stdout.write("")

        if not commit:
            self.stdout.write(
                self.style.WARNING(
                    "DRY RUN — pass --commit to actually create the subscribers."
                )
            )
            # Print first 10 to-add and first 5 already-exists for spot-check
            if to_add:
                self.stdout.write("\n  Sample of TO-ADD:")
                for e in to_add[:10]:
                    self.stdout.write(f"    + {e}")
                if len(to_add) > 10:
                    self.stdout.write(f"    ... ({len(to_add) - 10} more)")
            if existing_emails:
                self.stdout.write("\n  Sample of ALREADY-IN-DB:")
                for e in list(existing_emails)[:5]:
                    self.stdout.write(f"    = {e}")
                if len(existing_emails) > 5:
                    self.stdout.write(f"    ... ({len(existing_emails) - 5} more)")
            return

        # Commit
        created = 0
        for email in to_add:
            subscriber = Subscriber.objects.create(
                email=email,
                name=name_fallback,
                source="BULK_IMPORT",
                source_tag=source_tag,
                is_active=True,
            )
            for category in categories:
                SubscriptionPreference.objects.create(
                    subscriber=subscriber,
                    category=category,
                    is_enabled=True,
                )
            created += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Created {created} subscribers (skipped {len(existing_emails)} duplicates)."
            )
        )
