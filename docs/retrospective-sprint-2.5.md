# Sprint 2.5 Retrospective — News Watch Pipeline: RSS + Article Extraction

**Date**: 2 March 2026
**Duration**: Single session
**Sprint goal**: Build the newswatch app with RSS fetching and article body extraction

## What Was Built

- `newswatch` Django app with `NewsArticle` model (status lifecycle: NEW → EXTRACTED or FAILED)
- RSS fetcher service: parses Google Alerts RSS, unwraps redirect URLs, deduplicates by URL
- Article extractor service: uses trafilatura to extract body text, source name, published date
- Two management commands: `fetch_news_alerts` (RSS polling) and `extract_articles` (body extraction)
- Django admin with status/source filters and search
- 36 new backend tests across 4 test files

## What Went Well

- **Clean service layer separation**: RSS fetching and article extraction are independent services with clear interfaces. `fetch_news_from_rss()` returns `{created, skipped, errors}`, `extract_pending_articles()` returns `{extracted, failed, total}`. Easy to compose and test.
- **Batch URL deduplication**: The RSS fetcher batch-checks existing URLs with a single `filter(url__in=...)` query instead of N+1. Also tracks newly-created URLs within the same feed run to prevent intra-feed duplicates.
- **Graceful failure handling**: Both services handle errors without crashing. Failed articles get status=FAILED with an error message, so they can be inspected and retried.
- **Test-first approach**: All service functions are fully mocked — no network calls in tests. Tests cover success, failure, edge cases (no metadata, existing published date, empty feeds, bozo feeds).

## What Went Wrong

- **Missing Python dependency**: trafilatura requires `lxml_html_clean` as a separate package (split from lxml). This wasn't in the initial `requirements.txt` and caused an ImportError during test collection. Fixed by adding `lxml_html_clean>=0.4`.
- **Ordering test flakiness**: A test asserting `ordering = ["-created_at"]` by creating two records and comparing positions failed because both records got the same `auto_now_add` timestamp in SQLite. Fixed by testing `Meta.ordering` directly instead.

## Design Decisions

- **Google Alerts redirect unwrapping**: Google Alerts wraps article URLs in `google.com/url?...&url=ACTUAL_URL`. The RSS fetcher extracts the real URL from the query parameter, falling back to the raw link if no redirect is found.
- **Two-phase pipeline**: RSS fetching and article extraction are separate steps (separate management commands). This allows batch processing, independent scheduling, and easy retry of failed extractions.
- **trafilatura for extraction**: Chosen for its all-in-one approach — handles HTTP fetching, HTML parsing, main content extraction, and metadata extraction. Alternatives (newspaper3k, readability) are less maintained.
- **No API endpoints yet**: Sprint 2.5 is backend-only. The newswatch app is managed via management commands and Django admin. API endpoints will come in Sprint 2.6 or 2.8 when the frontend needs them.
- **`NEWS_WATCH_RSS_FEEDS` setting**: The `fetch_news_alerts` command reads a list of RSS URLs from Django settings, or accepts a single `--url` flag for ad-hoc use.

## Numbers

- Files created: 10 (1 model, 2 services, 2 commands, 4 test files, 1 admin)
- Files modified: 2 (requirements.txt, settings/base.py)
- Tests: 36 new backend, 719 total (552 backend + 167 frontend)
- Lines of code: ~450 new (services + tests + commands)
