"""Clear is_urgent=True on articles that never triggered an alert.

Ran once after the urgency classifier rewrite (2026-04-21) to sweep
out historical false-positives. The new classifier is stricter, but
already-flagged articles retain the old classification unless swept.

Keeps is_urgent=True on articles that have a corresponding URGENT_ALERT
broadcast — those are part of the sent record and should not be edited.

Usage:
    python manage.py clear_stale_urgent_flags --dry-run
    python manage.py clear_stale_urgent_flags
"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from broadcasts.models import Broadcast
from newswatch.models import NewsArticle


class Command(BaseCommand):
    help = "Clear is_urgent=True on articles older than 30 days that never fired an alert."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print what would be cleared without making changes.",
        )
        parser.add_argument(
            "--days",
            type=int,
            default=30,
            help="Age threshold in days (default: 30).",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        cutoff = timezone.now() - timedelta(days=options["days"])

        alerted_titles = set(
            Broadcast.objects.filter(
                kind=Broadcast.Kind.URGENT_ALERT,
            ).values_list("subject", flat=True)
        )
        alerted_article_titles = {
            s.removeprefix("URGENT: ") for s in alerted_titles
        }

        candidates = NewsArticle.objects.filter(
            is_urgent=True,
            published_date__lt=cutoff,
        ).exclude(title__in=alerted_article_titles)

        count = candidates.count()
        self.stdout.write(
            f"Found {count} stale urgent article(s) "
            f"(published before {cutoff:%Y-%m-%d}, no alert fired)."
        )

        if dry_run:
            for a in candidates[:20]:
                safe_title = a.title[:80].encode("ascii", "replace").decode("ascii")
                self.stdout.write(f"  [pk={a.pk}] {safe_title}")
            if count > 20:
                self.stdout.write(f"  ... and {count - 20} more")
            self.stdout.write(self.style.WARNING("DRY RUN — no changes made."))
            return

        updated = candidates.update(is_urgent=False, urgent_reason="")
        self.stdout.write(
            self.style.SUCCESS(
                f"Cleared is_urgent flag on {updated} stale article(s)."
            )
        )
