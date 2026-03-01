"""
Article extractor service using trafilatura.

Fetches the full text of a news article from its URL and updates
the corresponding NewsArticle record.
"""

import logging

import trafilatura

from newswatch.models import NewsArticle

logger = logging.getLogger(__name__)


def _extract_metadata(downloaded, url):
    """
    Extract article body text, source name, and published date
    from a downloaded page using trafilatura.

    Returns:
        dict with keys: body_text, source_name, published_date
    """
    result = {
        "body_text": "",
        "source_name": "",
        "published_date": None,
    }

    if not downloaded:
        return result

    # Extract main text
    body = trafilatura.extract(downloaded)
    if body:
        result["body_text"] = body.strip()

    # Extract metadata (source, date)
    metadata = trafilatura.extract_metadata(downloaded)
    if metadata:
        if metadata.sitename:
            result["source_name"] = metadata.sitename
        if metadata.date:
            # trafilatura returns date as string "YYYY-MM-DD"
            from datetime import datetime, timezone

            try:
                result["published_date"] = datetime.strptime(
                    metadata.date, "%Y-%m-%d"
                ).replace(tzinfo=timezone.utc)
            except (ValueError, TypeError):
                pass

    return result


def extract_article(article):
    """
    Fetch and extract body text for a single NewsArticle.

    Args:
        article: NewsArticle instance (status should be NEW).

    Returns:
        The updated NewsArticle instance.
    """
    logger.info("Extracting article: %s", article.url)

    try:
        downloaded = trafilatura.fetch_url(article.url)

        if not downloaded:
            article.status = NewsArticle.FAILED
            article.extraction_error = "Failed to download page."
            article.save()
            logger.warning("Download failed: %s", article.url)
            return article

        metadata = _extract_metadata(downloaded, article.url)

        if not metadata["body_text"]:
            article.status = NewsArticle.FAILED
            article.extraction_error = "No text content extracted."
            article.save()
            logger.warning("No text extracted: %s", article.url)
            return article

        article.body_text = metadata["body_text"]
        if metadata["source_name"]:
            article.source_name = metadata["source_name"]
        if metadata["published_date"] and not article.published_date:
            article.published_date = metadata["published_date"]
        article.status = NewsArticle.EXTRACTED
        article.extraction_error = ""
        article.save()
        logger.info(
            "Extracted %d chars from: %s",
            len(article.body_text),
            article.url,
        )

    except Exception as exc:
        article.status = NewsArticle.FAILED
        article.extraction_error = str(exc)[:500]
        article.save()
        logger.exception("Extraction error for %s: %s", article.url, exc)

    return article


def extract_pending_articles(batch_size=20):
    """
    Extract body text for all NEW articles.

    Args:
        batch_size: Maximum number of articles to process in one run.

    Returns:
        dict with:
            - extracted: count of successfully extracted articles
            - failed: count of articles that failed extraction
            - skipped: count of articles already processed
    """
    result = {"extracted": 0, "failed": 0, "total": 0}

    articles = NewsArticle.objects.filter(status=NewsArticle.NEW)[:batch_size]
    result["total"] = len(articles)

    for article in articles:
        extract_article(article)
        article.refresh_from_db()

        if article.status == NewsArticle.EXTRACTED:
            result["extracted"] += 1
        else:
            result["failed"] += 1

    logger.info(
        "Extraction batch complete: %d extracted, %d failed out of %d",
        result["extracted"],
        result["failed"],
        result["total"],
    )
    return result
