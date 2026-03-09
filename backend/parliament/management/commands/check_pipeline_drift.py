"""
Check pipeline component versions and detect prompt drift.

Usage:
    python manage.py check_pipeline_drift           # Show status
    python manage.py check_pipeline_drift --update   # Update stored hashes
"""
from django.core.management.base import BaseCommand
from parliament.services.pipeline_registry import (
    COMPONENTS, get_pipeline_version, check_drift,
)


class Command(BaseCommand):
    help = "Check pipeline version and detect prompt drift"

    def add_arguments(self, parser):
        parser.add_argument(
            "--update", action="store_true",
            help="Update stored hashes to current values",
        )

    def handle(self, *args, **options):
        self.stdout.write(f"\nPipeline Version: {get_pipeline_version()}\n")
        self.stdout.write("-" * 60)

        results = check_drift()
        any_drift = False

        for name, drifted, detail in results:
            version = COMPONENTS[name]["version"]
            icon = "!!" if drifted else "ok"
            self.stdout.write(f"  [{icon}] {name} v{version} — {detail}")
            if drifted:
                any_drift = True

        self.stdout.write("-" * 60)
        if any_drift:
            self.stderr.write(
                self.style.WARNING(
                    "DRIFT DETECTED: Prompt content changed but version "
                    "was not bumped. Update pipeline_registry.py."
                )
            )
        else:
            self.stdout.write(self.style.SUCCESS("All components clean."))
