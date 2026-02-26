"""Check parlimen.gov.my for new Hansard PDFs and optionally process them.

Usage:
    python manage.py check_new_hansards                     # Last 14 days
    python manage.py check_new_hansards --days 30           # Last 30 days
    python manage.py check_new_hansards --start 2026-02-01 --end 2026-02-28
    python manage.py check_new_hansards --auto-process      # Discover + process
"""

from datetime import date, timedelta

from django.core.management import call_command
from django.core.management.base import BaseCommand

from hansard.models import HansardSitting
from hansard.pipeline.scraper import discover_new_pdfs


class Command(BaseCommand):
    help = "Check parlimen.gov.my for new Hansard PDFs not yet processed."

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=14,
            help="Number of days to look back (default: 14).",
        )
        parser.add_argument(
            "--start",
            type=str,
            default="",
            help="Start date (YYYY-MM-DD). Overrides --days.",
        )
        parser.add_argument(
            "--end",
            type=str,
            default="",
            help="End date (YYYY-MM-DD). Defaults to today.",
        )
        parser.add_argument(
            "--auto-process",
            action="store_true",
            help="Automatically run process_hansard for each new PDF found.",
        )

    def handle(self, *args, **options):
        end_date = (
            date.fromisoformat(options["end"]) if options["end"]
            else date.today()
        )
        start_date = (
            date.fromisoformat(options["start"]) if options["start"]
            else end_date - timedelta(days=options["days"])
        )

        self.stdout.write(f"Checking for new Hansards: {start_date} to {end_date}")

        # Get already-processed dates
        processed_dates = set(
            HansardSitting.objects.filter(
                status=HansardSitting.Status.COMPLETED,
            ).values_list("sitting_date", flat=True)
        )
        self.stdout.write(f"Already processed: {len(processed_dates)} sittings")

        # Discover PDFs on parlimen.gov.my
        self.stdout.write("Probing parlimen.gov.my...")
        found = discover_new_pdfs(start_date, end_date)
        self.stdout.write(f"Found {len(found)} PDFs in date range")

        # Filter out already-processed
        new_pdfs = [
            pdf for pdf in found
            if pdf["sitting_date"] not in processed_dates
        ]

        if not new_pdfs:
            self.stdout.write(self.style.SUCCESS("No new Hansards to process."))
            return

        self.stdout.write(self.style.WARNING(
            f"{len(new_pdfs)} new Hansard(s) found:"
        ))
        for pdf in new_pdfs:
            self.stdout.write(f"  {pdf['sitting_date']} — {pdf['pdf_url']}")

        if not options["auto_process"]:
            self.stdout.write(
                "\nRun with --auto-process to process them automatically, "
                "or use 'process_hansard <url>' for each."
            )
            return

        # Auto-process each new PDF
        for pdf in new_pdfs:
            self.stdout.write(f"\nProcessing {pdf['sitting_date']}...")
            try:
                call_command(
                    "process_hansard",
                    pdf["pdf_url"],
                    f"--sitting-date={pdf['sitting_date'].isoformat()}",
                    stdout=self.stdout,
                    stderr=self.stderr,
                )
            except Exception as e:
                self.stderr.write(self.style.ERROR(
                    f"Failed to process {pdf['sitting_date']}: {e}"
                ))
                continue

        self.stdout.write(self.style.SUCCESS("\nDone."))
