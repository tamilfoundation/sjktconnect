"""Unified Hansard pipeline: calendar sync through meeting reports.

Usage:
    python manage.py run_hansard_pipeline              # Full pipeline
    python manage.py run_hansard_pipeline --dry-run     # Preview
    python manage.py run_hansard_pipeline --skip-calendar
    python manage.py run_hansard_pipeline --skip-analysis
"""

import time

from django.core.management import call_command
from django.core.management.base import BaseCommand

from hansard.models import HansardMention
from hansard.pipeline.calendar_scraper import sync_calendar
from hansard.pipeline.matcher import match_mentions
from parliament.services.scorecard import update_all_scorecards
from parliament.services.brief_generator import generate_all_pending_briefs
from parliament.services.report_generator import generate_all_pending_reports


def run_matching() -> dict:
    """Run school matching on all unmatched mentions."""
    unmatched = HansardMention.objects.filter(matched_schools__isnull=True)
    if not unmatched.exists():
        return {"matched": 0, "unmatched": 0, "total": 0}
    return match_mentions(unmatched)


def run_analysis() -> dict:
    """Run Gemini analysis on all un-analysed mentions."""
    from django.db import connection
    from parliament.services.gemini_client import analyse_mention, apply_analysis
    from parliament.services.mp_resolver import resolve_mp

    mentions = list(
        HansardMention.objects.filter(ai_summary="")
        .select_related("sitting")
        .order_by("sitting__sitting_date", "page_number")
    )
    if not mentions:
        return {"success": 0, "failed": 0}

    success = 0
    failed = 0
    for mention in mentions:
        analysis = analyse_mention(mention)
        if analysis:
            # Cross-reference against MP database
            resolved = resolve_mp(
                analysis["mp_name"], analysis["mp_constituency"], analysis["mp_party"]
            )
            analysis["mp_name"] = resolved["mp_name"]
            analysis["mp_constituency"] = resolved["mp_constituency"]
            analysis["mp_party"] = resolved["mp_party"]

            apply_analysis(mention, analysis)
            connection.close()
            success += 1
        else:
            failed += 1
        time.sleep(0.5)
    return {"success": success, "failed": failed}


class Command(BaseCommand):
    help = "Run the full Hansard pipeline: calendar sync through meeting reports."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview what each step would do without making changes.",
        )
        parser.add_argument(
            "--skip-calendar",
            action="store_true",
            help="Skip the calendar sync step.",
        )
        parser.add_argument(
            "--skip-analysis",
            action="store_true",
            help="Skip the Gemini AI analysis step.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        skip_calendar = options["skip_calendar"]
        skip_analysis = options["skip_analysis"]

        if dry_run:
            self._dry_run(skip_calendar, skip_analysis)
            return

        steps = self._build_steps(skip_calendar, skip_analysis)

        self.stdout.write(self.style.MIGRATE_HEADING(
            f"Hansard Pipeline — {len(steps)} steps"
        ))

        for i, (name, func) in enumerate(steps, 1):
            self.stdout.write(f"\n[{i}/{len(steps)}] {name}...")
            try:
                result = func()
                self.stdout.write(self.style.SUCCESS(
                    f"  OK: {result}"
                ))
            except Exception as e:
                self.stdout.write(self.style.ERROR(
                    f"  FAILED: {e}"
                ))

        self.stdout.write(self.style.SUCCESS("\nPipeline complete."))

    def _build_steps(self, skip_calendar, skip_analysis):
        """Build the list of (name, callable) steps."""
        steps = []

        if not skip_calendar:
            steps.append(("Sync calendar", self._step_sync_calendar))

        steps.append(("Check new Hansards", self._step_check_new_hansards))
        steps.append(("Match mentions", self._step_match_mentions))

        if not skip_analysis:
            steps.append(("Analyse mentions", self._step_analyse_mentions))

        steps.append(("Update scorecards", self._step_update_scorecards))
        steps.append(("Generate briefs", self._step_generate_briefs))
        steps.append(("Generate meeting reports", self._step_generate_reports))

        return steps

    def _step_sync_calendar(self):
        return sync_calendar()

    def _step_check_new_hansards(self):
        call_command("check_new_hansards", auto_process=True)
        return "done"

    def _step_match_mentions(self):
        return run_matching()

    def _step_analyse_mentions(self):
        return run_analysis()

    def _step_update_scorecards(self):
        return update_all_scorecards()

    def _step_generate_briefs(self):
        return generate_all_pending_briefs()

    def _step_generate_reports(self):
        return generate_all_pending_reports()

    def _dry_run(self, skip_calendar, skip_analysis):
        """Print what each step would do without making changes."""
        self.stdout.write(self.style.WARNING("=== DRY RUN ==="))
        self.stdout.write("No changes will be made.\n")

        if not skip_calendar:
            self.stdout.write("1. Sync calendar — fetch parliament sitting dates")
        else:
            self.stdout.write("1. Sync calendar — SKIPPED")

        self.stdout.write(
            "2. Check new Hansards — discover and process new PDFs"
        )

        unmatched_count = HansardMention.objects.filter(
            matched_schools__isnull=True
        ).count()
        self.stdout.write(
            f"3. Match mentions — {unmatched_count} unmatched mention(s)"
        )

        if not skip_analysis:
            unanalysed_count = HansardMention.objects.filter(
                ai_summary=""
            ).count()
            self.stdout.write(
                f"4. Analyse mentions — {unanalysed_count} un-analysed mention(s)"
            )
        else:
            self.stdout.write("4. Analyse mentions — SKIPPED")

        self.stdout.write("5. Update scorecards — recalculate all MP scorecards")
        self.stdout.write("6. Generate briefs — create briefs for sittings without one")
        self.stdout.write("7. Generate meeting reports — create reports for meetings without one")

        self.stdout.write(self.style.WARNING("\n=== DRY RUN COMPLETE ==="))
