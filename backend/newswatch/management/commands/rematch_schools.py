"""Re-resolve unmatched school mentions in news articles.

Finds articles where mentioned_schools contains entries with empty moe_code
and re-runs the matching pipeline against the current school database.
"""

import sys

from django.core.management.base import BaseCommand

from newswatch.models import NewsArticle
from newswatch.services.news_analyser import _resolve_school_codes


class Command(BaseCommand):
    help = "Re-match school mentions in news articles (un-matched by default; --force-all also re-resolves rows that already have a moe_code)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be updated without saving",
        )
        parser.add_argument(
            "--force-all",
            action="store_true",
            help=(
                "Re-resolve EVERY mention even when it already has a "
                "moe_code. Use this after extending alias coverage so "
                "previously WRONG matches get re-evaluated against the "
                "new aliases. Without this flag, only un-matched mentions "
                "(moe_code=='') are re-tried."
            ),
        )

    def handle(self, *args, **options):
        # Force UTF-8 stdout so Tamil-character article titles don't crash
        # the run on Windows (where the default is cp1252). Bare attribute
        # check to avoid AttributeError on TextIOBase replacements that
        # don't support reconfigure().
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")

        dry_run = options["dry_run"]
        force_all = options["force_all"]
        updated_count = 0

        articles = NewsArticle.objects.exclude(mentioned_schools=[]).exclude(
            mentioned_schools__isnull=True
        )

        for article in articles:
            unmatched = [
                s for s in article.mentioned_schools if not s.get("moe_code")
            ]
            # Sprint 28: --force-all also re-processes articles whose
            # mentions ALL have moe_codes — to catch wrong-match cases
            # after an alias-coverage extension. Without the flag we
            # preserve the historical fast-path (skip if no gaps).
            if not unmatched and not force_all:
                continue

            self.stdout.write(
                f"\nArticle {article.id}: {article.title[:60]}"
            )
            for s in unmatched:
                self.stdout.write(f"  Unmatched: {s['name']}")

            # Re-resolve all schools (not just unmatched — keeps matched ones too)
            resolved = _resolve_school_codes(article.mentioned_schools, article)

            # Check if any previously unmatched schools are now matched
            newly_matched = []
            for old, new in zip(article.mentioned_schools, resolved):
                if not old.get("moe_code") and new.get("moe_code"):
                    newly_matched.append(
                        f"  -> Matched: {old['name']} => "
                        f"{new['name']} ({new['moe_code']})"
                    )

            if newly_matched:
                for msg in newly_matched:
                    self.stdout.write(self.style.SUCCESS(msg))
                updated_count += 1
                if not dry_run:
                    article.mentioned_schools = resolved
                    article.save(update_fields=["mentioned_schools"])
            else:
                self.stdout.write("  (no new matches found)")

        action = "Would update" if dry_run else "Updated"
        self.stdout.write(
            self.style.SUCCESS(f"\n{action} {updated_count} article(s)")
        )
