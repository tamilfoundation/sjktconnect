"""Backfill speaker names using Hansard formatting patterns.

Instead of calling Gemini, this uses regex to find the speaker identification
pattern (e.g. "Tuan Name [Constituency]:") in the stored context_before text.
This is faster, free, and more reliable than AI for structured Hansard text.
"""

import re

from django.core.management.base import BaseCommand

from hansard.models import HansardMention
from hansard.pipeline.searcher import SPEAKER_PATTERN, _clean_speaker_name

CONSTITUENCY_RE = re.compile(r'\[([^\]]+)\]')


class Command(BaseCommand):
    help = "Backfill missing speaker names from Hansard formatting in stored context."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be updated without saving.",
        )
        parser.add_argument(
            "--all",
            action="store_true",
            help="Re-extract for all mentions, not just those with empty mp_name.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        process_all = options["all"]

        if process_all:
            qs = (
                HansardMention.objects
                .exclude(verbatim_quote="")
                .select_related("sitting")
                .order_by("-sitting__sitting_date")
            )
        else:
            qs = (
                HansardMention.objects
                .filter(mp_name="")
                .exclude(verbatim_quote="")
                .select_related("sitting")
                .order_by("-sitting__sitting_date")
            )

        mentions = list(qs)
        self.stdout.write(f"Processing {len(mentions)} mentions.")

        updated = 0
        for m in mentions:
            # Search context_before for speaker pattern
            text = m.context_before or ""
            speaker_matches = list(SPEAKER_PATTERN.finditer(text))

            if not speaker_matches:
                if not dry_run:
                    self.stdout.write(
                        f"  #{m.id} {m.sitting.sitting_date} p.{m.page_number}: "
                        f"no speaker found"
                    )
                continue

            last = speaker_matches[-1]
            raw_speaker = last.group(1).strip()

            # Extract constituency
            constituency = ""
            const_match = CONSTITUENCY_RE.search(raw_speaker)
            if const_match:
                constituency = const_match.group(1).strip()

            # Clean name
            name = _clean_speaker_name(raw_speaker)
            if not name:
                continue

            if dry_run:
                self.stdout.write(
                    f"  #{m.id} {m.sitting.sitting_date} p.{m.page_number}: "
                    f"{name} ({constituency})"
                )
            else:
                m.mp_name = name
                if constituency:
                    m.mp_constituency = constituency
                m.save(update_fields=["mp_name", "mp_constituency", "updated_at"])
                self.stdout.write(
                    f"  #{m.id} {m.sitting.sitting_date} p.{m.page_number}: "
                    f"{name} ({constituency})"
                )

            updated += 1

        action = "Would update" if dry_run else "Updated"
        self.stdout.write(
            self.style.SUCCESS(
                f"\n{action} {updated} of {len(mentions)} mentions."
            )
        )
