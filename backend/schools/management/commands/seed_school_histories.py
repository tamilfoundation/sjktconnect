"""Bulk import per-school history JSON from the Sprint 31 Wikipedia sweep.

Reads a directory of `<state>.results.json` files (or a single combined JSON file)
produced by the Sprint 31 research agents, and updates each School's `history`,
`history_source_urls`, `history_status`, and `history_updated_at` fields.

Safety:
- `--dry-run` prints what would change without writing.
- Skips schools whose `history_status` is already SCHOOL_REVIEWED or VERIFIED —
  AI-research never overwrites human-curated content.
- Only writes entries with `yield == "full"` (the others have empty histories
  by definition; no point bumping history_updated_at on no-op writes).
- Reports per-state counts + a final summary.

Usage:
    python manage.py seed_school_histories --dir scratchpad/school-history-research/
    python manage.py seed_school_histories --file /path/to/combined.json --dry-run

Expected input JSON shape (per file is an array of school result objects):
    [
        {
            "moe_code": "PBD1082",
            "name": "SJK(T) Azad",
            "wikipedia_url": "https://...",
            "yield": "full" | "stub" | "none",
            "history_ms": "...",
            "history_en": "...",
            "source_urls": ["..."]
        },
        ...
    ]
"""

import json
from collections import Counter
from pathlib import Path

from django.core.management.base import BaseCommand
from django.utils import timezone

from schools.models import School


class Command(BaseCommand):
    help = "Bulk import per-school history JSON from the Sprint 31 Wikipedia sweep."

    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument(
            "--dir",
            type=str,
            help="Directory of *.results.json files (one per state).",
        )
        group.add_argument(
            "--file",
            type=str,
            help="Single combined JSON file (array of all entries).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print what would change without writing.",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Overwrite SCHOOL_REVIEWED and VERIFIED histories (DANGEROUS — only if you know what you're doing).",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        force = options["force"]

        # Collect all entries from --dir or --file
        entries = []
        if options["dir"]:
            d = Path(options["dir"])
            if not d.is_dir():
                self.stderr.write(self.style.ERROR(f"Not a directory: {d}"))
                return
            for f in sorted(d.glob("*.results.json")):
                with open(f, encoding="utf-8") as fh:
                    entries.extend(json.load(fh))
                self.stdout.write(f"  Loaded {f.name}")
        else:
            with open(options["file"], encoding="utf-8") as fh:
                entries = json.load(fh)
            self.stdout.write(f"  Loaded {options['file']}")

        self.stdout.write(self.style.WARNING(f"\nTotal entries: {len(entries)}"))
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — no writes will be made.\n"))

        # Aggregate by yield
        yield_counts = Counter(e.get("yield") for e in entries)
        self.stdout.write(f"Yield breakdown: {dict(yield_counts)}\n")

        # Process each entry
        stats = Counter()
        skipped_human = []
        skipped_missing = []
        now = timezone.now()

        for entry in entries:
            moe = entry.get("moe_code")
            if not moe:
                stats["no_moe_code"] += 1
                continue

            try:
                school = School.objects.get(moe_code=moe)
            except School.DoesNotExist:
                stats["school_not_found"] += 1
                skipped_missing.append(moe)
                continue

            # Skip schools with human-curated history (unless --force)
            if not force and school.history_status in ("SCHOOL_REVIEWED", "VERIFIED"):
                stats["skipped_human_curated"] += 1
                skipped_human.append(moe)
                continue

            # Only write entries with usable content
            if entry.get("yield") != "full":
                stats["skipped_no_content"] += 1
                continue

            # Build the per-locale history dict (skip empty strings).
            # Sprint 31.1 (2026-06-28): Tamil now allowed too. Originally
            # excluded per tamil-style-guide; owner-approved policy flip
            # backfilled the ~70 ms-Wikipedia-sourced rows + future Tamil-
            # Wikipedia sourced batches. All entries stay UNVERIFIED so
            # owner / school admin can flag awkward Tamil.
            history = {}
            if entry.get("history_en", "").strip():
                history["en"] = entry["history_en"].strip()
            if entry.get("history_ms", "").strip():
                history["ms"] = entry["history_ms"].strip()
            if entry.get("history_ta", "").strip():
                history["ta"] = entry["history_ta"].strip()

            if not history:
                stats["skipped_empty_after_clean"] += 1
                continue

            source_urls = entry.get("source_urls", []) or []
            key_dates = {}
            if entry.get("key_dates_en"):
                key_dates["en"] = entry["key_dates_en"]
            if entry.get("key_dates_ms"):
                key_dates["ms"] = entry["key_dates_ms"]
            if entry.get("key_dates_ta"):
                key_dates["ta"] = entry["key_dates_ta"]

            if dry_run:
                locales = "+".join(sorted(history.keys()))
                self.stdout.write(
                    f"  [DRY] {moe} {school.short_name[:45]:45} "
                    f"+history({locales}) "
                    f"sources={len(source_urls)} "
                    f"key_dates={sum(len(v) for v in key_dates.values())}"
                )
                stats["would_update"] += 1
            else:
                school.history = history
                school.history_source_urls = source_urls
                school.history_status = "UNVERIFIED"
                school.history_updated_at = now
                school.history_key_dates = key_dates
                school.save(update_fields=[
                    "history",
                    "history_source_urls",
                    "history_status",
                    "history_updated_at",
                    "history_key_dates",
                ])
                stats["updated"] += 1

        # Summary
        self.stdout.write(self.style.SUCCESS("\n=== Summary ==="))
        for k, v in sorted(stats.items()):
            self.stdout.write(f"  {k:30} {v}")

        if skipped_human:
            self.stdout.write(self.style.WARNING(
                f"\nSkipped {len(skipped_human)} schools with human-curated history "
                f"(use --force to override): {', '.join(skipped_human[:10])}"
                f"{'...' if len(skipped_human) > 10 else ''}"
            ))
        if skipped_missing:
            self.stdout.write(self.style.WARNING(
                f"\nSkipped {len(skipped_missing)} moe_codes not found in DB: "
                f"{', '.join(skipped_missing[:10])}"
                f"{'...' if len(skipped_missing) > 10 else ''}"
            ))
