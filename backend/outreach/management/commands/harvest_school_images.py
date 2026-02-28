"""Harvest school images from Google APIs (satellite + Places).

Usage:
    python manage.py harvest_school_images                      # All schools, satellite + places
    python manage.py harvest_school_images --limit 10           # First 10 schools only
    python manage.py harvest_school_images --state Johor        # Only Johor schools
    python manage.py harvest_school_images --source satellite   # Satellite only
    python manage.py harvest_school_images --source places      # Places only
    python manage.py harvest_school_images --dry-run            # Preview without fetching
"""

from django.core.management.base import BaseCommand

from outreach.services.image_harvester import harvest_images_for_school
from schools.models import School


class Command(BaseCommand):
    help = "Harvest school images from Google Maps/Places APIs."

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=0,
            help="Max number of schools to process (0 = all).",
        )
        parser.add_argument(
            "--state",
            type=str,
            default="",
            help="Filter by state name (e.g. 'Johor').",
        )
        parser.add_argument(
            "--source",
            type=str,
            default="",
            help="Image source: 'satellite', 'places', or '' for both.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview which schools would be processed without fetching.",
        )

    def handle(self, *args, **options):
        qs = School.objects.filter(is_active=True)

        if options["state"]:
            qs = qs.filter(state__iexact=options["state"])

        if options["limit"]:
            qs = qs[: options["limit"]]

        schools = list(qs)
        self.stdout.write(f"Schools to process: {len(schools)}")

        sources = None
        if options["source"]:
            sources = [options["source"]]
            self.stdout.write(f"Source filter: {options['source']}")

        if options["dry_run"]:
            for school in schools:
                has_gps = bool(school.gps_lat and school.gps_lng)
                self.stdout.write(
                    f"  {school.moe_code} {school.short_name} "
                    f"(GPS: {'yes' if has_gps else 'no'})"
                )
            self.stdout.write(self.style.SUCCESS("Dry run complete."))
            return

        total_created = 0
        for i, school in enumerate(schools, 1):
            self.stdout.write(
                f"[{i}/{len(schools)}] {school.moe_code} {school.short_name}..."
            )
            images = harvest_images_for_school(school, sources)
            for img in images:
                self.stdout.write(
                    f"  + {img.source} ({'primary' if img.is_primary else 'secondary'})"
                )
            total_created += len(images)

        self.stdout.write(
            self.style.SUCCESS(f"Done. {total_created} images created/updated.")
        )
