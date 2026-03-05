"""Deduplicate Hansard mentions — merge overlapping mentions from the same page.

When the keyword searcher finds "SJK(T)" 5 times on the same page, it creates
5 separate mentions with overlapping 200-char quotes from the same speech.
This command merges them into one mention per page, keeping the longest quote
and the best AI analysis.
"""

import logging

from django.core.management.base import BaseCommand
from django.db.models import Count

from hansard.models import HansardMention, HansardSitting, MentionedSchool

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Merge duplicate mentions from the same sitting + page into one."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be merged without making changes.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        # Find all (sitting, page) groups with more than one mention
        dupes = (
            HansardMention.objects
            .values("sitting_id", "page_number")
            .annotate(cnt=Count("id"))
            .filter(cnt__gt=1)
            .order_by("sitting_id", "page_number")
        )

        total_removed = 0
        total_groups = 0

        for group in dupes:
            mentions = list(
                HansardMention.objects
                .filter(
                    sitting_id=group["sitting_id"],
                    page_number=group["page_number"],
                )
                .select_related("sitting")
                .order_by("id")
            )

            if len(mentions) <= 1:
                continue

            total_groups += 1
            sitting_date = mentions[0].sitting.sitting_date

            # Pick the "best" mention to keep:
            # 1. Prefer one with MP name identified
            # 2. Then highest significance
            # 3. Then longest verbatim quote
            def score(m):
                return (
                    1 if m.mp_name else 0,
                    m.significance or 0,
                    len(m.verbatim_quote),
                    len(m.ai_summary),
                )

            mentions.sort(key=score, reverse=True)
            keeper = mentions[0]
            to_remove = mentions[1:]

            # Merge: take the longest verbatim quote + context across all
            all_quotes = [m.verbatim_quote for m in mentions if m.verbatim_quote]
            longest_quote = max(all_quotes, key=len) if all_quotes else keeper.verbatim_quote

            all_context_before = [m.context_before for m in mentions if m.context_before]
            longest_before = max(all_context_before, key=len) if all_context_before else ""

            all_context_after = [m.context_after for m in mentions if m.context_after]
            longest_after = max(all_context_after, key=len) if all_context_after else ""

            # If keeper has no MP name but another does, take the name
            if not keeper.mp_name:
                for m in mentions[1:]:
                    if m.mp_name:
                        keeper.mp_name = m.mp_name
                        keeper.mp_constituency = m.mp_constituency or keeper.mp_constituency
                        keeper.mp_party = m.mp_party or keeper.mp_party
                        break

            # Move any school matches from removed mentions to keeper
            school_codes_on_keeper = set(
                MentionedSchool.objects
                .filter(mention=keeper)
                .values_list("school__moe_code", flat=True)
            )

            self.stdout.write(
                f"  {sitting_date} p.{group['page_number']}: "
                f"merge {len(to_remove)} into keeper #{keeper.id} "
                f"({keeper.mp_name or 'Unknown'})"
            )

            if not dry_run:
                # Update keeper with merged data
                keeper.verbatim_quote = longest_quote
                keeper.context_before = longest_before
                keeper.context_after = longest_after
                keeper.save(update_fields=[
                    "verbatim_quote", "context_before", "context_after",
                    "mp_name", "mp_constituency", "mp_party", "updated_at",
                ])

                # Reassign school matches
                for m in to_remove:
                    for ms in MentionedSchool.objects.filter(mention=m):
                        if ms.school.moe_code not in school_codes_on_keeper:
                            ms.mention = keeper
                            ms.save(update_fields=["mention"])
                            school_codes_on_keeper.add(ms.school.moe_code)

                # Delete duplicates
                ids_to_delete = [m.id for m in to_remove]
                HansardMention.objects.filter(id__in=ids_to_delete).delete()

            total_removed += len(to_remove)

        # Update sitting mention counts
        if not dry_run:
            for sitting in HansardSitting.objects.filter(mention_count__gt=0):
                actual = sitting.mentions.count()
                if sitting.mention_count != actual:
                    sitting.mention_count = actual
                    sitting.save(update_fields=["mention_count"])

        action = "Would remove" if dry_run else "Removed"
        self.stdout.write(
            self.style.SUCCESS(
                f"\n{action} {total_removed} duplicate mentions "
                f"across {total_groups} page groups."
            )
        )
