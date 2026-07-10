"""
Generic, reusable importer for an opted-in email batch.

Brings any list of people who willingly gave their email to hear from
Tamil Foundation (parents, alumni, donors, event attendees...) into the
subscriber base — tagged, and enrolled in all newsletters from day one.

This REPLACES the old one-off governance scripts. Two deliberate rules
learned from the 2026-07 governance import:
  1. Creates SubscriptionPreference rows at import time, so nobody ends
     up "active but subscribed to nothing" (the 131-orphan bug).
  2. NEVER resurrects a previously-unsubscribed / bounced-out address —
     opting out must stick. Those are reported and skipped.

Input: a CSV with an ``email`` column (required) and optional ``name``.
Column matching is case-insensitive; extra columns are ignored.

Usage:
  python manage.py import_email_batch --file parents.csv --source-tag TF_PARENTS_2026 --dry-run
  python manage.py import_email_batch --file parents.csv --source-tag TF_PARENTS_2026
"""

import csv
import re
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from subscribers.models import Subscriber
from subscribers.services.subscriber_service import _ensure_preferences_exist

EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
INVALID_LITERALS = {"n/a", "na", "none", "-", "tiada", ""}


def _clean_email(value):
    if not value:
        return ""
    email = str(value).strip().lower()
    if email in INVALID_LITERALS or not EMAIL_RE.match(email):
        return ""
    return email


class Command(BaseCommand):
    help = "Import an opted-in email batch: tag + auto-enrol in all newsletters."

    def add_arguments(self, parser):
        parser.add_argument("--file", required=True, help="Path to a CSV with an 'email' column (optional 'name').")
        parser.add_argument("--source-tag", required=True, help="Stable tag stamped on the whole batch, e.g. TF_PARENTS_2026.")
        parser.add_argument("--source", default="BULK_IMPORT", help="Subscriber.source value (default: BULK_IMPORT).")
        parser.add_argument("--dry-run", action="store_true", help="Preview without writing.")

    def handle(self, *args, **options):
        path = Path(options["file"])
        source_tag = options["source_tag"].strip()
        source = options["source"].strip()
        dry_run = options["dry_run"]

        if not source_tag:
            raise CommandError("--source-tag must not be empty.")
        if not path.exists():
            raise CommandError(f"File not found: {path}")

        rows = self._read_rows(path)
        self.stdout.write(f"Read {len(rows)} data rows from {path.name}")

        # Dedup within the file (keep first name seen for an email)
        batch = {}
        invalid = 0
        for r in rows:
            email = _clean_email(r.get("email"))
            if not email:
                invalid += 1
                continue
            if email not in batch:
                batch[email] = (r.get("name") or "").strip()
        self.stdout.write(f"  valid unique emails: {len(batch)} | invalid/blank skipped: {invalid}")

        # Classify against existing subscribers
        existing = {
            s.email.lower(): s
            for s in Subscriber.objects.filter(email__in=list(batch.keys()))
        }
        to_create = {e: n for e, n in batch.items() if e not in existing}
        already_active = [e for e in batch if e in existing and existing[e].is_active]
        opted_out = [e for e in batch if e in existing and not existing[e].is_active]

        self.stdout.write(
            f"\n  new subscribers to create:        {len(to_create)}"
            f"\n  already active (ensure prefs only): {len(already_active)}"
            f"\n  previously opted-out (SKIP):        {len(opted_out)}"
        )
        if opted_out:
            self.stdout.write("  opted-out addresses skipped (consent stays):")
            for e in opted_out[:20]:
                self.stdout.write(f"    - {e}")
            if len(opted_out) > 20:
                self.stdout.write(f"    ...and {len(opted_out) - 20} more")

        if dry_run:
            self.stdout.write("\nDRY RUN — nothing written. Re-run without --dry-run to import.")
            return

        created, prefs_added = self._commit(to_create, already_active, existing, source, source_tag)
        self.stdout.write(
            f"\nIMPORT COMPLETE — created {created} subscribers, "
            f"ensured newsletter preferences on {prefs_added}, "
            f"skipped {len(opted_out)} opted-out."
        )

    def _read_rows(self, path):
        with open(path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames:
                raise CommandError("CSV has no header row.")
            # case-insensitive column map
            cols = {c.lower().strip(): c for c in reader.fieldnames}
            if "email" not in cols:
                raise CommandError(f"CSV needs an 'email' column. Found: {reader.fieldnames}")
            email_c = cols["email"]
            name_c = cols.get("name")
            out = []
            for row in reader:
                out.append({
                    "email": row.get(email_c, ""),
                    "name": row.get(name_c, "") if name_c else "",
                })
            return out

    @transaction.atomic
    def _commit(self, to_create, already_active, existing, source, source_tag):
        created = 0
        prefs_added = 0
        for email, name in to_create.items():
            sub, was_created = Subscriber.objects.get_or_create(
                email=email,
                defaults={
                    "name": name,
                    "source": source,
                    "source_tag": source_tag,
                    "is_active": True,
                },
            )
            if was_created:
                created += 1
            _ensure_preferences_exist(sub)
            prefs_added += 1
        # Existing active subscribers: guarantee they have newsletter rows too
        for email in already_active:
            _ensure_preferences_exist(existing[email])
            prefs_added += 1
        return created, prefs_added
