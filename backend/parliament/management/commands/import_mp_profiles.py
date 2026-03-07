"""Management command to import MP profiles from parlimen.gov.my and mymp.org.my.

Usage:
    python manage.py import_mp_profiles
    python manage.py import_mp_profiles --dry-run
    python manage.py import_mp_profiles --constituency P078
"""

import logging
import time

from django.core.management.base import BaseCommand

from parliament.services.mp_scraper import (
    fetch_mymp_sitemap,
    fetch_parlimen_listing,
    fetch_parlimen_profile,
)
from schools.models import Constituency

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Import MP profiles from parlimen.gov.my and mymp.org.my."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print what would be imported without saving to the database.",
        )
        parser.add_argument(
            "--constituency",
            type=str,
            default=None,
            help="Filter to a single constituency code (e.g. P078).",
        )

    def handle(self, **options):
        dry_run = options["dry_run"]
        filter_code = options["constituency"]

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — no records will be saved."))

        # Step 1: Fetch parlimen.gov.my listing
        self.stdout.write("Fetching MP listing from parlimen.gov.my...")
        listing = fetch_parlimen_listing()
        self.stdout.write(f"Found {len(listing)} MPs in listing.")

        # Step 2: Fetch MyMP sitemap for slug mapping
        self.stdout.write("Fetching MyMP sitemap...")
        mymp_slugs = fetch_mymp_sitemap()
        self.stdout.write(f"Found {len(mymp_slugs)} MyMP slugs.")

        # Step 3: Build set of known constituency codes
        known_codes = set(Constituency.objects.values_list("code", flat=True))

        created = 0
        updated = 0
        skipped = 0

        for mp_data in listing:
            code = mp_data["constituency_code"]

            # Filter if --constituency specified
            if filter_code and code != filter_code:
                continue

            # Skip if constituency not in database
            if code not in known_codes:
                self.stdout.write(f"  Skipping {mp_data['name']} — constituency {code} not in database.")
                skipped += 1
                continue

            # Step 4: Fetch profile for contact details
            profile_id = mp_data.get("parlimen_profile_id", "")
            profile = {}
            if profile_id:
                self.stdout.write(f"  Fetching profile for {mp_data['name']} ({code})...")
                profile = fetch_parlimen_profile(profile_id)
                time.sleep(0.5)

            # Step 5: Match MyMP slug
            mp_name_lower = mp_data["name"].lower()
            mymp_slug = ""
            for mymp_name, slug in mymp_slugs.items():
                if mymp_name in mp_name_lower:
                    mymp_slug = slug
                    break

            # Build fields
            defaults = {
                "name": mp_data["name"],
                "photo_url": mp_data.get("photo_url", ""),
                "party": mp_data.get("party", ""),
                "parlimen_profile_id": profile_id,
                "mymp_slug": mymp_slug,
                "phone": profile.get("phone"),
                "fax": profile.get("fax"),
                "email": profile.get("email"),
                "facebook_url": profile.get("facebook_url"),
                "service_centre_address": profile.get("service_centre_address"),
                "portfolio": profile.get("portfolio", ""),
            }

            if dry_run:
                self.stdout.write(f"  [DRY RUN] Would import: {mp_data['name']} ({code})")
                for key, value in defaults.items():
                    if value:
                        self.stdout.write(f"    {key}: {value}")
                continue

            # Step 6: Create or update
            from parliament.models import MP

            constituency = Constituency.objects.get(code=code)
            _, was_created = MP.objects.update_or_create(
                constituency=constituency,
                defaults=defaults,
            )

            if was_created:
                created += 1
                self.stdout.write(f"  Created: {mp_data['name']} ({code})")
            else:
                updated += 1
                self.stdout.write(f"  Updated: {mp_data['name']} ({code})")

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN complete — no records saved."))
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Done: {created} created, {updated} updated, {skipped} skipped."
                )
            )
