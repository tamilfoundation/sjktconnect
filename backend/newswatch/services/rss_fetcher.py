"""
RSS fetcher service for Google Alerts feeds.

Parses a Google Alerts RSS feed and creates NewsArticle records
for any new (unseen) articles. Deduplicates by URL.
"""

import logging
from datetime import datetime, timezone
from time import mktime

import feedparser

from newswatch.models import NewsArticle

logger = logging.getLogger(__name__)


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


def _resolve_url(entry):
    """
    Extract the actual article URL from a Google Alerts entry.

    Google Alerts wraps URLs in a redirect:
    https://www.google.com/url?...&url=ACTUAL_URL&...

    Falls back to entry.link if no redirect is found.
    """
    link = getattr(entry, "link", "")
    if not link:
        return ""

    # Google Alerts redirect URLs contain the real URL as a parameter
    if "google.com/url" in link:
        from urllib.parse import parse_qs, urlparse

        parsed = urlparse(link)
        params = parse_qs(parsed.query)
        if "url" in params:
            return params["url"][0]

    return link


def _clean_title(title):
    """Remove HTML tags from RSS title (Google Alerts uses <b> tags)."""
    import re
    return re.sub(r"<[^>]+>", "", title).strip()


def fetch_news_from_rss(rss_url):
    """
    Parse a Google Alerts RSS feed and create NewsArticle records.

    Args:
        rss_url: URL of the Google Alerts RSS feed.

    Returns:
        dict with:
            - created: list of newly created NewsArticle instances
            - skipped: count of articles already in database
            - errors: list of error messages
    """
    result = {"created": [], "skipped": 0, "errors": []}

    if not rss_url:
        result["errors"].append("No RSS URL provided.")
        return result

    logger.info("Fetching RSS feed: %s", rss_url)
    feed = feedparser.parse(rss_url)

    if feed.bozo and not feed.entries:
        error_msg = str(getattr(feed, "bozo_exception", "Unknown parse error"))
        logger.error("RSS feed parse error: %s", error_msg)
        result["errors"].append(f"Feed parse error: {error_msg}")
        return result

    feed_title = getattr(feed.feed, "title", "")
    logger.info(
        "Feed '%s' returned %d entries", feed_title, len(feed.entries)
    )

    # Batch-check existing URLs to avoid N+1
    entry_urls = []
    for entry in feed.entries:
        url = _resolve_url(entry)
        if url:
            entry_urls.append(url)

    existing_urls = set(
        NewsArticle.objects.filter(url__in=entry_urls).values_list(
            "url", flat=True
        )
    )

    for entry in feed.entries:
        url = _resolve_url(entry)
        if not url:
            result["errors"].append(
                f"No URL found for entry: {getattr(entry, 'title', '?')}"
            )
            continue

        if url in existing_urls:
            result["skipped"] += 1
            continue

        title = _clean_title(getattr(entry, "title", "Untitled"))
        published_date = _parse_published_date(entry)

        article = NewsArticle.objects.create(
            url=url,
            title=title,
            alert_title=feed_title,
            published_date=published_date,
        )
        result["created"].append(article)
        existing_urls.add(url)  # Prevent duplicates within same feed
        logger.info("Created article: %s", title[:80])

    logger.info(
        "RSS fetch complete: %d created, %d skipped, %d errors",
        len(result["created"]),
        result["skipped"],
        len(result["errors"]),
    )
    return result
