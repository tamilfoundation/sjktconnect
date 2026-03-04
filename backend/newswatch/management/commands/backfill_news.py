"""
Management command to backfill historical news articles from Google News RSS.

Uses Google News RSS search to find articles matching Tamil school keywords,
decodes Google News redirect URLs to actual article URLs, and creates
NewsArticle records for the existing extract → analyse pipeline.

Usage:
    python manage.py backfill_news
    python manage.py backfill_news --months 6
    python manage.py backfill_news --dry-run
"""

import logging
import time
from datetime import datetime, timezone
from time import mktime

import feedparser
from django.core.management.base import BaseCommand
from googlenewsdecoder import new_decoderv1

from newswatch.models import NewsArticle

logger = logging.getLogger(__name__)

# Google News RSS search queries for Tamil school news
# Each tuple: (query, hl, ceid) — hl/ceid control the language of results
SEARCH_QUERIES = [
    ('SJKT', 'en-MY', 'MY:en'),
    ('"SJK(T)"', 'en-MY', 'MY:en'),
    ('"sekolah Tamil" Malaysia', 'en-MY', 'MY:en'),
    ('"Tamil school" Malaysia', 'en-MY', 'MY:en'),
    # Tamil script queries for Tamil-language sources (no time filter — when: breaks Tamil queries)
    ('\u0ba4\u0bae\u0bbf\u0bb4\u0bcd\u0baa\u0bcd\u0baa\u0bb3\u0bcd\u0bb3\u0bbf', 'ta', 'MY:ta'),  # தமிழ்ப்பள்ளி
    ('\u0ba4\u0bae\u0bbf\u0bb4\u0bcd \u0baa\u0bb3\u0bcd\u0bb3\u0bbf \u0bae\u0bb2\u0bc7\u0b9a\u0bbf\u0baf\u0bbe', 'ta', 'MY:ta'),  # தமிழ் பள்ளி மலேசியா
    ('SJKT \u0ba4\u0bae\u0bbf\u0bb4\u0bcd', 'ta', 'MY:ta'),  # SJKT தமிழ்
    ('\u0ba4\u0bae\u0bbf\u0bb4\u0bcd \u0baa\u0bb3\u0bcd\u0bb3\u0bbf \u0b86\u0b9a\u0bbf\u0bb0\u0bbf\u0baf\u0bb0\u0bcd', 'ta', 'MY:ta'),  # தமிழ் பள்ளி ஆசிரியர்
]


def _build_google_news_url(query, months=3, hl='en-MY', ceid='MY:en'):
    """Build a Google News RSS search URL with time filter.

    Note: the when: time filter breaks Tamil script queries on Google News RSS,
    so we skip it for non-ASCII queries.
    """
    from urllib.parse import quote
    # when: filter doesn't work with Tamil script queries
    has_non_ascii = any(ord(c) > 127 for c in query)
    if has_non_ascii:
        time_param = ""
    else:
        when = f"{months}m" if months <= 12 else f"{months // 12}y"
        time_param = f"+when:{when}"
    return (
        f"https://news.google.com/rss/search?"
        f"q={quote(query)}{time_param}"
        f"&hl={hl}&gl=MY&ceid={ceid}"
    )


def _parse_published_date(entry):
    """Extract published date from an RSS entry."""
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        return datetime.fromtimestamp(
            mktime(entry.published_parsed), tz=timezone.utc
        )
    if hasattr(entry, "updated_parsed") and entry.updated_parsed:
        return datetime.fromtimestamp(
            mktime(entry.updated_parsed), tz=timezone.utc
        )
    return None


def _decode_google_news_url(google_url):
    """Decode a Google News redirect URL to the actual article URL.

    Returns the decoded URL or None on failure.
    """
    try:
        result = new_decoderv1(google_url)
        if result.get("status"):
            return result["decoded_url"]
        logger.warning("Decode failed for %s: %s", google_url[:80], result.get("message", ""))
        return None
    except Exception:
        logger.exception("Error decoding URL: %s", google_url[:80])
        return None


class Command(BaseCommand):
    help = "Backfill historical news articles from Google News RSS search."

    def add_arguments(self, parser):
        parser.add_argument(
            "--months",
            type=int,
            default=14,
            help="How many months back to search (default: 14, i.e. Jan 2025).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print articles found without creating records.",
        )
        parser.add_argument(
            "--delay",
            type=float,
            default=1.0,
            help="Seconds to wait between URL decoding requests (default: 1.0).",
        )

    def handle(self, *args, **options):
        months = options["months"]
        dry_run = options["dry_run"]
        delay = options["delay"]

        # Collect all entries from all queries, dedup by Google News URL
        all_entries = {}  # google_url -> entry dict

        for query, hl, ceid in SEARCH_QUERIES:
            url = _build_google_news_url(query, months, hl=hl, ceid=ceid)
            safe_query = query.encode("ascii", "replace").decode()
            self.stdout.write(f"Fetching: {safe_query} (hl={hl})...")
            feed = feedparser.parse(url)
            count = 0
            for entry in feed.entries:
                link = getattr(entry, "link", "")
                if link and link not in all_entries:
                    all_entries[link] = entry
                    count += 1
            self.stdout.write(f"  {len(feed.entries)} results, {count} new unique")

        self.stdout.write(f"\nTotal unique articles found: {len(all_entries)}")

        if dry_run:
            self.stdout.write(self.style.WARNING("\n--- DRY RUN ---"))
            for i, (gurl, entry) in enumerate(all_entries.items(), 1):
                title = getattr(entry, "title", "?")
                source = entry.get("source", {}).get("title", "?") if hasattr(entry, "source") else "?"
                date = _parse_published_date(entry)
                date_str = date.strftime("%Y-%m-%d") if date else "?"
                # Encode safely for Windows console
                display = f"{i}. [{date_str}] {title} ({source})"
                self.stdout.write(display.encode("ascii", "replace").decode("ascii"))
            return

        # Decode URLs and create articles
        created = 0
        skipped = 0
        failed = 0

        # Pre-fetch existing URLs to avoid N+1
        existing_urls = set(
            NewsArticle.objects.values_list("url", flat=True)
        )

        for i, (google_url, entry) in enumerate(all_entries.items(), 1):
            title = getattr(entry, "title", "Untitled")
            source_name = ""
            if hasattr(entry, "source") and isinstance(entry.source, dict):
                source_name = entry.source.get("title", "")
            elif hasattr(entry, "source"):
                source_name = getattr(entry.source, "title", "")

            # Decode the Google News URL
            real_url = _decode_google_news_url(google_url)
            if not real_url:
                safe_title = title[:60].encode("ascii", "replace").decode()
                self.stderr.write(
                    self.style.WARNING(f"  [{i}] FAILED to decode: {safe_title}")
                )
                failed += 1
                time.sleep(delay)
                continue

            # Check for duplicates
            if real_url in existing_urls:
                skipped += 1
                continue

            published_date = _parse_published_date(entry)

            NewsArticle.objects.create(
                url=real_url,
                title=title,
                source_name=source_name,
                published_date=published_date,
                alert_title="Google News Backfill",
            )
            existing_urls.add(real_url)
            created += 1
            safe_title = title[:60].encode("ascii", "replace").decode()
            date_str = published_date.strftime("%Y-%m-%d") if published_date else "?"
            self.stdout.write(f"  [{i}] Created: {safe_title} ({date_str})")
            time.sleep(delay)

        self.stdout.write(
            self.style.SUCCESS(
                f"\nBackfill complete. "
                f"Created: {created}, Skipped: {skipped}, Failed: {failed}"
            )
        )

        if created > 0:
            self.stdout.write(
                "\nNext steps:\n"
                "  python manage.py run_news_pipeline --extract-only\n"
                "  python manage.py run_news_pipeline --analyse-only"
            )
