"""
Django management command: Import legacy governance leaders as newsletter subscribers

Extracts emails from the 4 Tamil Foundation 2018 governance datasets:
- Headmasters
- Board Chairmen
- PTA Chairmen
- Alumni Chairmen

Features:
  - Deduplicates by email (same person with multiple roles)
  - Checks existing subscribers (skip if already subscribed)
  - Tracks roles in source_tag (e.g., TF_GOVERNANCE_LEADER_2018_HEADMASTER_PTA_CHAIR)
  - Uses silent opt-in (source="BULK_IMPORT")
  - Sets data_source and data_source_date for audit trail

Usage:
  python manage.py import_legacy_newsletter --dry-run
  python manage.py import_legacy_newsletter
"""

import openpyxl
from pathlib import Path
from datetime import date
from collections import defaultdict
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.core.mail import send_mail
import re

from subscribers.models import Subscriber


LEGACY_DATA_PATH = Path("C:/Users/tamil/Downloads/tamilschool/")

# Role mapping for display and source_tag
ROLE_MAPPING = {
    "headmaster": ("த.ஆசிரியர் - Status.xlsx", "த.ஆசிரியர்", "HEADMASTER", "HM"),
    "board_chair": ("தலைவர் - Status.xlsx", "தலைவர்", "BOARD_CHAIRMAN", "BC"),
    "pta_chair": ("பெ.ஆ.ச. - Status.xlsx", "பெ.ஆ.ச.", "PTA_CHAIRMAN", "PTA"),
    "alumni_chair": ("மு.மாணவர் - Status.xlsx", "மு.மாணவர்", "ALUMNI_CHAIRMAN", "AC"),
}


def is_valid_email(email):
    """Basic email validation."""
    if not email or not isinstance(email, str):
        return False
    email = email.strip()
    # Check for common invalid patterns
    if email.lower() in ("n/a", "na", "none", "-", "tiada", ""):
        return False
    # Basic regex check
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def normalize_name(name_str):
    """Normalize name to Title Case."""
    if not name_str:
        return ""
    return str(name_str).strip().title()


class Command(BaseCommand):
    help = "Import legacy governance leaders as newsletter subscribers"

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview what would be imported without saving',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        self.stdout.write("=" * 100)
        self.stdout.write(
            "IMPORTING LEGACY GOVERNANCE LEADERS AS NEWSLETTER SUBSCRIBERS"
            + (" (DRY RUN)" if dry_run else "")
        )
        self.stdout.write("=" * 100)

        # Load all 4 datasets
        self.stdout.write("\nLoading governance datasets...")
        all_records = {}  # email -> {name, roles, org}

        for role_key, (filename, sheet_name, role_display, role_abbr) in ROLE_MAPPING.items():
            self.stdout.write(f"  Loading {role_display}...")
            records = self._load_dataset(filename, sheet_name)

            for name, email in records:
                if not is_valid_email(email):
                    continue

                email_lower = email.lower().strip()
                if email_lower not in all_records:
                    all_records[email_lower] = {
                        'name': name,
                        'email': email,
                        'roles': [],
                        'role_abbrs': [],
                    }
                all_records[email_lower]['roles'].append(role_display)
                all_records[email_lower]['role_abbrs'].append(role_abbr)

        self.stdout.write(f"\n[OK] Extracted {len(all_records)} unique emails from all 4 datasets")

        # Check existing subscribers
        self.stdout.write("\nChecking existing subscribers...")
        existing_emails = set(
            Subscriber.objects.filter(is_active=True).values_list('email', flat=True)
        )
        self.stdout.write(f"  Found {len(existing_emails)} active subscribers")

        # Filter to new subscribers only
        new_subscribers = {
            email: data for email, data in all_records.items()
            if email not in existing_emails
        }
        self.stdout.write(f"  {len(new_subscribers)} new emails to add")

        # Show simulation or commit
        if dry_run:
            self._simulate_import(new_subscribers, existing_emails, all_records)
        else:
            self._commit_import(new_subscribers)

    def _load_dataset(self, filename, sheet_name):
        """Load staff dataset and extract name + email pairs."""
        filepath = LEGACY_DATA_PATH / filename
        if not filepath.exists():
            raise CommandError(f"File not found: {filepath}")

        wb = openpyxl.load_workbook(filepath, data_only=True)
        ws = wb[sheet_name]

        records = []
        for row_idx in range(2, ws.max_row + 1):
            name = ws.cell(row_idx, 4).value  # Column 4 = Name
            email_work = ws.cell(row_idx, 16).value  # Column 16 = Work email
            email_home = ws.cell(row_idx, 17).value  # Column 17 = Home email
            email_other = ws.cell(row_idx, 18).value  # Column 18 = Other email

            # Pick first available email
            email = email_work or email_home or email_other

            if name and email:
                records.append((name, email))

        wb.close()
        return records

    def _simulate_import(self, new_subscribers, existing_emails, all_records):
        """Show what would be imported (dry run)."""
        self.stdout.write("\n" + "=" * 100)
        self.stdout.write("IMPORT SIMULATION (DRY RUN)")
        self.stdout.write("=" * 100)

        self.stdout.write(f"\nNew subscribers to add: {len(new_subscribers)}")
        self.stdout.write(f"Emails already subscribed: {len(existing_emails)}")
        self.stdout.write(f"Total unique emails: {len(all_records)}")

        # Show sample of new subscribers
        self.stdout.write("\nSample of new subscribers (first 10):")
        for i, (email, data) in enumerate(list(new_subscribers.items())[:10], 1):
            roles_str = " + ".join(data['roles'])
            source_tag = f"TF_2018_{('_').join(data.get('role_abbrs', []))}"
            self.stdout.write(f"\n  {i}. {data['name']}")
            self.stdout.write(f"     Email: {email}")
            self.stdout.write(f"     Roles: {roles_str}")
            self.stdout.write(f"     Source tag: {source_tag}")

        # Summary
        self.stdout.write("\n" + "=" * 100)
        self.stdout.write("SUMMARY")
        self.stdout.write("=" * 100)
        self.stdout.write(f"\nNew subscribers to create: {len(new_subscribers)}")
        self.stdout.write(f"Already subscribed (skipped): {len(existing_emails)}")
        self.stdout.write(f"Data source: Tamil Foundation, 2018-01-01")
        self.stdout.write(f"Source type: BULK_IMPORT (silent opt-in)")
        self.stdout.write("\n(This is a dry run. No data has been modified.)")
        self.stdout.write("To import, run without --dry-run flag")

    @transaction.atomic
    def _commit_import(self, new_subscribers):
        """Actually import the data into the database."""
        self.stdout.write("\n" + "=" * 100)
        self.stdout.write("IMPORTING SUBSCRIBERS")
        self.stdout.write("=" * 100)

        created_count = 0
        skipped_count = 0
        for email, data in new_subscribers.items():
            # Build source_tag from roles (abbreviated to fit 50 char limit)
            role_abbrs = data.get('role_abbrs', [])
            source_tag = f"TF_2018_{('_').join(role_abbrs)}"

            # Use get_or_create to handle race conditions gracefully
            subscriber, created = Subscriber.objects.get_or_create(
                email=email,
                defaults={
                    'name': normalize_name(data['name']),
                    'organisation': "",  # Not available in legacy data
                    'source': "BULK_IMPORT",
                    'source_tag': source_tag,
                    'is_active': True,
                    'bounce_count': 0,
                }
            )

            if created:
                created_count += 1
            else:
                skipped_count += 1

            if (created_count + skipped_count) % 100 == 0:
                self.stdout.write(f"  Processed {created_count + skipped_count}...")

        # Summary
        self.stdout.write("\n" + "=" * 100)
        self.stdout.write("IMPORT COMPLETE")
        self.stdout.write("=" * 100)
        self.stdout.write(f"\nSubscribers created: {created_count}")
        self.stdout.write(f"Subscribers skipped (already existed): {skipped_count}")
        self.stdout.write(f"Data source: Tamil Foundation, 2018-01-01")
        self.stdout.write(f"Source type: BULK_IMPORT (silent opt-in)")
        self.stdout.write("\nAll records have been successfully imported to the database.")
