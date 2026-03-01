"""
Management command to fetch news articles from Google Alerts RSS feeds.

Usage:
    python manage.py fetch_news_alerts
    python manage.py fetch_news_alerts --url "https://www.google.com/alerts/feeds/..."
"""

from django.conf import settings
from django.core.management.base import BaseCommand

from newswatch.services.rss_fetcher import fetch_news_from_rss


class Command(BaseCommand):
    help = "Fetch news articles from Google Alerts RSS feeds."

    def add_arguments(self, parser):
        parser.add_argument(
            "--url",
            type=str,
            help="Single RSS feed URL to fetch (overrides settings).",
        )

    def handle(self, *args, **options):
        urls = []

        if options["url"]:
            urls = [options["url"]]
        else:
            urls = getattr(settings, "NEWS_WATCH_RSS_FEEDS", [])

        if not urls:
            self.stderr.write(
                self.style.WARNING(
                    "No RSS feed URLs configured. "
                    "Set NEWS_WATCH_RSS_FEEDS in settings or use --url."
                )
            )
            return

        total_created = 0
        total_skipped = 0
        total_errors = 0

        for url in urls:
            self.stdout.write(f"Fetching: {url[:80]}...")
            result = fetch_news_from_rss(url)

            total_created += len(result["created"])
            total_skipped += result["skipped"]
            total_errors += len(result["errors"])

            for error in result["errors"]:
                self.stderr.write(self.style.WARNING(f"  Error: {error}"))

            self.stdout.write(
                f"  Created: {len(result['created'])}, "
                f"Skipped: {result['skipped']}"
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"\nDone. Created: {total_created}, "
                f"Skipped: {total_skipped}, "
                f"Errors: {total_errors}"
            )
        )
