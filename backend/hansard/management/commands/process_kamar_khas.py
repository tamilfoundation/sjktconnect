"""Ingest Kamar Khas (Special Chamber) Hansards for existing sittings.

Fetches KKDR-<date>-N.pdf for each sitting in range and appends
chamber=KAMAR_KHAS mentions (which then flow through the normal
analyse/brief steps). Idempotent via HansardSitting.kamar_khas_checked_at.

Usage:
    python manage.py process_kamar_khas --date 2026-06-22
    python manage.py process_kamar_khas --since 2026-06-22
    python manage.py process_kamar_khas --since 2026-06-22 --until 2026-07-10
    python manage.py process_kamar_khas --since 2026-06-22 --dry-run
    python manage.py process_kamar_khas --since 2026-06-22 --force   # re-check already-checked
"""

from datetime import date

from django.core.management.base import BaseCommand, CommandError

from hansard.models import HansardSitting
from hansard.pipeline.kamar_khas import process_kamar_khas


class Command(BaseCommand):
    help = "Fetch + process Kamar Khas (Special Chamber) Hansards for sittings in a date range."

    def add_arguments(self, parser):
        parser.add_argument("--date", type=str, help="Single sitting date (YYYY-MM-DD).")
        parser.add_argument("--since", type=str, help="Start date (YYYY-MM-DD) inclusive.")
        parser.add_argument("--until", type=str, help="End date (YYYY-MM-DD) inclusive. Default: today.")
        parser.add_argument("--force", action="store_true", help="Re-process even if already Kamar-Khas-checked.")
        parser.add_argument("--dry-run", action="store_true", help="List target sittings without fetching.")

    def _parse(self, s):
        try:
            return date.fromisoformat(s)
        except ValueError as e:
            raise CommandError(f"Invalid date '{s}', use YYYY-MM-DD.") from e

    def handle(self, *args, **options):
        force = options["force"]
        dry_run = options["dry_run"]

        qs = HansardSitting.objects.all()
        if options["date"]:
            qs = qs.filter(sitting_date=self._parse(options["date"]))
        elif options["since"]:
            qs = qs.filter(sitting_date__gte=self._parse(options["since"]))
            if options["until"]:
                qs = qs.filter(sitting_date__lte=self._parse(options["until"]))
        else:
            raise CommandError("Provide --date or --since.")

        # Only sittings that actually have a Hansard (COMPLETED main chamber).
        qs = qs.filter(status=HansardSitting.Status.COMPLETED)
        if not force:
            qs = qs.filter(kamar_khas_checked_at__isnull=True)
        qs = qs.order_by("sitting_date")

        sittings = list(qs)
        self.stdout.write(f"Kamar Khas ingestion: {len(sittings)} sitting(s) to process"
                          + (" (dry run)" if dry_run else ""))
        if dry_run:
            for s in sittings:
                self.stdout.write(f"  {s.sitting_date}  (checked_at={s.kamar_khas_checked_at})")
            self.stdout.write("\nDRY RUN — nothing fetched. Re-run without --dry-run.")
            return

        tot_parts = tot_mentions = tot_matched = done = errors = 0
        for s in sittings:
            try:
                r = process_kamar_khas(s)
                done += 1
                tot_parts += r["parts"]; tot_mentions += r["mentions"]; tot_matched += r["matched"]
                self.stdout.write(
                    f"  {s.sitting_date}: {r['parts']} part(s), "
                    f"{r['mentions']} mention(s), {r['matched']} matched"
                )
            except Exception as e:  # one bad sitting must not kill the batch
                errors += 1
                self.stdout.write(self.style.ERROR(f"  {s.sitting_date}: FAILED — {e}"))

        self.stdout.write(self.style.SUCCESS(
            f"\nDone. {done} sitting(s) processed, {errors} failed. "
            f"Kamar Khas totals: {tot_parts} parts, {tot_mentions} mentions, {tot_matched} matched."
        ))
        if tot_mentions:
            self.stdout.write(
                "New mentions have ai_summary='' — the next run_hansard_pipeline "
                "(or `analyse_mentions`) will Gemini-analyse them + regenerate briefs."
            )
