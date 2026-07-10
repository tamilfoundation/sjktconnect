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
        parser.add_argument(
            "--retry-failed-days",
            type=int,
            default=7,
            help=(
                "Before discovery, retry any FAILED or NO_PDF sittings from "
                "the last N days (default 7). Catches PDFs that landed late "
                "after the morning cron's first attempt. Set 0 to disable."
            ),
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        skip_calendar = options["skip_calendar"]
        skip_analysis = options["skip_analysis"]
        retry_days = options["retry_failed_days"]

        if dry_run:
            self._dry_run(skip_calendar, skip_analysis)
            return

        if retry_days > 0:
            n = self._reset_recent_failures(retry_days)
            if n:
                self.stdout.write(self.style.WARNING(
                    f"Reset {n} stuck-PROCESSING / recent FAILED/NO_PDF "
                    f"sitting(s) back to PENDING for retry."
                ))

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
        steps.append(("Ingest Kamar Khas", self._step_process_kamar_khas))
        steps.append(("Match mentions", self._step_match_mentions))

        if not skip_analysis:
            steps.append(("Analyse mentions", self._step_analyse_mentions))

        steps.append(("Update scorecards", self._step_update_scorecards))
        steps.append(("Generate briefs", self._step_generate_briefs))
        steps.append(("Generate meeting reports", self._step_generate_reports))
        steps.append(("Compose Parliament Watch drafts", self._step_compose_parliament_watch))

        return steps

    def _reset_recent_failures(self, days: int) -> int:
        """Reset stuck/failed sittings back to PENDING so they retry.

        Two cases:
        - **Stuck PROCESSING (any age):** a previous run died mid-extraction
          (e.g. the 2026-07 OOM crash). The pipeline is single-threaded and
          this runs at start-of-run, so any PROCESSING row is necessarily
          stale — reset it regardless of age so a crash can never orphan a
          sitting permanently (before this fix, 29/30 Jun sat stuck for days).
        - **Recent FAILED/NO_PDF (last `days`):** the morning cron tried a
          date before parlimen posted the PDF; the PDF may be up now.
        """
        from datetime import timedelta
        from django.utils import timezone as _tz
        from hansard.models import HansardSitting

        stale_processing = HansardSitting.objects.filter(
            status=HansardSitting.Status.PROCESSING,
        ).update(status=HansardSitting.Status.PENDING, error_message="")

        cutoff = _tz.localdate() - timedelta(days=days)
        recent_failed = HansardSitting.objects.filter(
            sitting_date__gte=cutoff,
            status__in=[HansardSitting.Status.FAILED, HansardSitting.Status.NO_PDF],
        ).update(status=HansardSitting.Status.PENDING, error_message="")

        return stale_processing + recent_failed

    def _step_sync_calendar(self):
        return sync_calendar()

    def _step_check_new_hansards(self):
        call_command("check_new_hansards", auto_process=True)
        return "done"

    def _step_process_kamar_khas(self):
        """Fetch Special-Chamber (KKDR-*.pdf) Hansards for recently-completed
        sittings not yet checked. Runs BEFORE match/analyse so its mentions
        flow through the same enrichment + brief generation this run.
        Idempotent via kamar_khas_checked_at, so it never re-analyses (no
        repeated Gemini cost); bounded to the last 30 days for the daily run.
        """
        from datetime import timedelta
        from django.utils import timezone as _tz
        from hansard.models import HansardSitting
        from hansard.pipeline.kamar_khas import process_kamar_khas
        cutoff = _tz.localdate() - timedelta(days=30)
        pending = list(HansardSitting.objects.filter(
            status=HansardSitting.Status.COMPLETED,
            kamar_khas_checked_at__isnull=True,
            sitting_date__gte=cutoff,
        ).order_by("sitting_date"))
        parts = mentions = 0
        for s in pending:
            try:
                r = process_kamar_khas(s)
                parts += r["parts"]
                mentions += r["mentions"]
            except Exception as e:
                self.stdout.write(self.style.ERROR(
                    f"    Kamar Khas {s.sitting_date} failed: {e}"
                ))
        return {"sittings": len(pending), "parts": parts, "mentions": mentions}

    def _step_match_mentions(self):
        return run_matching()

    def _step_analyse_mentions(self):
        return run_analysis()

    def _step_update_scorecards(self):
        return update_all_scorecards()

    def _step_generate_briefs(self):
        return generate_all_pending_briefs()

    def _step_generate_reports(self):
        call_command("generate_meeting_reports")
        return "done"

    def _step_compose_parliament_watch(self):
        # Idempotent — only composes drafts for published meetings that
        # don't already have a PARLIAMENT_WATCH broadcast (dedupe by
        # coverage start+end dates). Skip silently if nothing new.
        call_command("compose_parliament_watch", auto=True)
        return "done"

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
        self.stdout.write("8. Compose Parliament Watch drafts — auto-create DRAFT broadcasts for any new published reports (idempotent)")

        self.stdout.write(self.style.WARNING("\n=== DRY RUN COMPLETE ==="))
