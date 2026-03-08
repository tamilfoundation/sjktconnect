"""Rebuild all Hansard sittings: re-download, re-extract, re-search, re-match.

Usage:
    python manage.py rebuild_all_hansards                # Full rebuild
    python manage.py rebuild_all_hansards --dry-run      # Preview
    python manage.py rebuild_all_hansards --skip-analysis # Skip Gemini (fast re-extract)
    python manage.py rebuild_all_hansards --include-failed # Include FAILED sittings
    python manage.py rebuild_all_hansards --limit 10     # Process only first 10
"""

import tempfile
import time

from django.core.management.base import BaseCommand
from django.db import connection
from django.utils import timezone

from hansard.models import HansardMention, HansardSitting, SchoolAlias
from hansard.pipeline.downloader import download_hansard
from hansard.pipeline.extractor import extract_text
from hansard.pipeline.keywords import get_all_keywords
from hansard.pipeline.matcher import match_mentions
from hansard.pipeline.searcher import search_keywords


def process_single_sitting(sitting, keywords, skip_matching=False):
    """Re-process a single sitting through the pipeline.

    Returns dict with processing results.
    """
    dest_dir = tempfile.mkdtemp(prefix="hansard_rebuild_")

    # Download
    pdf_path = download_hansard(sitting.pdf_url, dest_dir)

    # Extract
    pages = extract_text(pdf_path)
    sitting.total_pages = len(pages)

    # Search
    matches = search_keywords(pages, keywords)

    # Delete old mentions and close stale connection
    sitting.mentions.all().delete()
    connection.close()

    # Store new mentions (deduplicated: one per page per speaker)
    # Different keywords often match the same speech on a page.
    # Different speakers (e.g. MP question + Deputy Minister response) are preserved.
    seen = set()
    mentions = []
    for match in matches:
        dedup_key = (match["page_number"], match.get("speaker_name", ""))
        if dedup_key in seen:
            continue
        seen.add(dedup_key)
        mentions.append(HansardMention(
            sitting=sitting,
            page_number=match["page_number"],
            verbatim_quote=match["verbatim_quote"],
            context_before=match["context_before"],
            context_after=match["context_after"],
            keyword_matched=match["keyword_matched"],
            mp_name=match.get("speaker_name", ""),
            mp_constituency=match.get("speaker_constituency", ""),
        ))
    HansardMention.objects.bulk_create(mentions)
    connection.close()

    # Match to schools
    matched_count = 0
    if not skip_matching and SchoolAlias.objects.exists() and mentions:
        mention_qs = HansardMention.objects.filter(sitting=sitting)
        result = match_mentions(mention_qs)
        matched_count = result.get("matched", 0)
        connection.close()

    # Update sitting
    sitting.mention_count = len(mentions)
    sitting.processed_at = timezone.now()
    sitting.status = HansardSitting.Status.COMPLETED
    sitting.error_message = ""
    sitting.save(update_fields=[
        "total_pages", "mention_count", "processed_at", "status", "error_message",
    ])

    return {
        "mentions": len(mentions),
        "matched": matched_count,
        "pages": len(pages),
        "status": "ok",
    }


class Command(BaseCommand):
    help = "Rebuild all Hansard sittings: re-download, re-extract, re-search, re-match."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Preview what would be rebuilt without making changes.",
        )
        parser.add_argument(
            "--skip-analysis", action="store_true",
            help="Skip Gemini AI analysis (run extraction + matching only).",
        )
        parser.add_argument(
            "--include-failed", action="store_true",
            help="Include FAILED sittings in the rebuild.",
        )
        parser.add_argument(
            "--skip-matching", action="store_true",
            help="Skip school name matching (run extraction only, match later via pipeline).",
        )
        parser.add_argument(
            "--limit", type=int, default=0,
            help="Process only the first N sittings (for testing).",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        skip_analysis = options["skip_analysis"]
        skip_matching = options["skip_matching"]
        include_failed = options["include_failed"]
        limit = options["limit"]

        # Build queryset
        statuses = [HansardSitting.Status.COMPLETED]
        if include_failed:
            statuses.append(HansardSitting.Status.FAILED)

        sittings = (
            HansardSitting.objects.filter(status__in=statuses)
            .order_by("sitting_date")
        )
        if limit:
            sittings = sittings[:limit]

        sitting_list = list(sittings)
        total = len(sitting_list)

        if dry_run:
            self.stdout.write(self.style.WARNING("=== DRY RUN ==="))
            self.stdout.write(f"Would rebuild {total} sitting(s):")
            for s in sitting_list:
                self.stdout.write(
                    f"  {s.sitting_date} -- {s.mention_count} mentions, "
                    f"{s.total_pages or '?'} pages"
                )
            total_mentions = sum(s.mention_count for s in sitting_list)
            self.stdout.write(f"\nTotal mentions to reprocess: {total_mentions}")
            if not skip_analysis:
                self.stdout.write(f"Estimated Gemini calls: ~{total_mentions}")
            self.stdout.write(self.style.WARNING("=== DRY RUN COMPLETE ==="))
            return

        self.stdout.write(self.style.MIGRATE_HEADING(
            f"Rebuilding {total} Hansard sittings"
        ))

        keywords = get_all_keywords()
        success = 0
        failed = 0
        total_mentions = 0

        for i, sitting in enumerate(sitting_list, 1):
            self.stdout.write(
                f"\n[{i}/{total}] {sitting.sitting_date} "
                f"({sitting.pdf_filename})..."
            )
            try:
                result = process_single_sitting(sitting, keywords, skip_matching=skip_matching)
                total_mentions += result["mentions"]
                self.stdout.write(self.style.SUCCESS(
                    f"  OK: {result['pages']} pages, "
                    f"{result['mentions']} mentions, "
                    f"{result['matched']} matched"
                ))
                success += 1
                connection.close()
            except Exception as e:
                sitting.status = HansardSitting.Status.FAILED
                sitting.error_message = str(e)[:500]
                sitting.save(update_fields=["status", "error_message"])
                self.stdout.write(self.style.ERROR(f"  FAILED: {e}"))
                failed += 1

        self.stdout.write(self.style.MIGRATE_HEADING("\nExtraction complete"))
        self.stdout.write(f"  Success: {success}/{total}")
        self.stdout.write(f"  Failed: {failed}/{total}")
        self.stdout.write(f"  Total mentions: {total_mentions}")

        # Run analysis if not skipped
        if not skip_analysis and total_mentions > 0:
            self.stdout.write(self.style.MIGRATE_HEADING(
                "\nRunning Gemini analysis..."
            ))
            from hansard.management.commands.run_hansard_pipeline import run_analysis
            analysis_result = run_analysis()
            self.stdout.write(self.style.SUCCESS(
                f"  Analysis: {analysis_result['success']} success, "
                f"{analysis_result['failed']} failed"
            ))

        # Regenerate scorecards and briefs
        self.stdout.write(self.style.MIGRATE_HEADING(
            "\nRegenerating scorecards and briefs..."
        ))
        from parliament.services.scorecard import update_all_scorecards
        from parliament.services.brief_generator import generate_all_pending_briefs
        update_all_scorecards()
        generate_all_pending_briefs()
        self.stdout.write(self.style.SUCCESS("Done."))

        self.stdout.write(self.style.SUCCESS(
            f"\nRebuild complete! {success} sittings, {total_mentions} mentions."
        ))
