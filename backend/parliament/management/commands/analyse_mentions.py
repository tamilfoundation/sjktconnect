"""Management command to analyse unprocessed Hansard mentions with Gemini.

Usage:
    python manage.py analyse_mentions                  # All unanalysed
    python manage.py analyse_mentions --sitting-date 2026-01-26  # One sitting
    python manage.py analyse_mentions --limit 10       # First 10 only
    python manage.py analyse_mentions --dry-run        # Show what would be processed
"""

import logging
import time

from django.core.management.base import BaseCommand
from django.db import connection

from hansard.models import HansardMention
from parliament.services.gemini_client import analyse_mention, apply_analysis

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Analyse unprocessed Hansard mentions using Gemini Flash AI."

    def add_arguments(self, parser):
        parser.add_argument(
            "--sitting-date",
            help="Only process mentions from this sitting date (YYYY-MM-DD).",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=0,
            help="Maximum number of mentions to process (0 = all).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be processed without calling Gemini.",
        )

    def handle(self, **options):
        # Unanalysed = no AI summary yet (mp_name may be empty if
        # the speaker couldn't be identified from the quote)
        qs = HansardMention.objects.filter(ai_summary="")

        if options["sitting_date"]:
            qs = qs.filter(sitting__sitting_date=options["sitting_date"])

        qs = qs.select_related("sitting").order_by("sitting__sitting_date", "page_number")

        if options["limit"]:
            qs = qs[:options["limit"]]

        mentions = list(qs)
        total = len(mentions)

        if total == 0:
            self.stdout.write("No unanalysed mentions found.")
            return

        if options["dry_run"]:
            self.stdout.write(f"Would analyse {total} mention(s):")
            for m in mentions:
                self.stdout.write(
                    f"  - {m.sitting.sitting_date} p.{m.page_number}: "
                    f"'{m.keyword_matched}' ({len(m.verbatim_quote)} chars)"
                )
            return

        self.stdout.write(f"Analysing {total} mention(s) with Gemini Flash...")

        success = 0
        failed = 0

        for i, mention in enumerate(mentions, 1):
            self.stdout.write(
                f"  [{i}/{total}] {mention.sitting.sitting_date} "
                f"p.{mention.page_number}...",
                ending="",
            )

            analysis = analyse_mention(mention)
            if analysis:
                apply_analysis(mention, analysis)
                # Close DB connection after each write to prevent stale
                # pooled connections from silently dropping writes
                connection.close()
                self.stdout.write(
                    f" {analysis['mention_type']} "
                    f"(sig={analysis['significance']}, {analysis['sentiment']})"
                )
                success += 1
            else:
                self.stdout.write(" FAILED")
                failed += 1

            # Paid tier 1: 1000 RPM — minimal delay to be polite
            time.sleep(0.5)

        self.stdout.write(
            self.style.SUCCESS(
                f"\nDone: {success} analysed, {failed} failed out of {total}."
            )
        )
