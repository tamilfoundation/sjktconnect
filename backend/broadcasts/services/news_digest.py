"""News Watch fortnightly digest generator — Economist-style editorial via Gemini.

Selects top approved, analysed articles from the past fortnight and generates
structured editorial content suitable for email broadcasts.

Returns a dict with: editors_note, big_story, in_brief, the_number, worth_knowing.

Uses the google.genai SDK (same pattern as broadcasts/services/parliament_digest.py).
"""

import json
import logging
import os
from datetime import timedelta

from django.utils import timezone
from google import genai
from google.genai import types

from newswatch.models import NewsArticle

logger = logging.getLogger(__name__)

REQUIRED_KEYS = {"editors_note", "big_story", "in_brief", "the_number"}

DIGEST_PROMPT = """\
You are the editor of a fortnightly intelligence briefing about Malaysian \
Tamil schools (SJK(T)) for school board members, parents, NGOs, and community \
leaders. Write in the style of The Economist — authoritative, concise, witty \
where appropriate, and always focused on what matters.

Below are the top {article_count} news articles from the past {days} days, \
ranked by relevance to Tamil schools.

{articles_block}

Transform these articles into an EDITORIAL DIGEST. Return a JSON object with \
these keys:

1. "editors_note" (string): 2-3 sentences setting the scene for this \
fortnight. What's the dominant theme? Is the news good or bad overall? \
Written as a confident editorial voice — not a summary, but a framing.

2. "big_story" (object): The single most important story. Keys:
   - "title" (string): Headline (rewrite for clarity, don't just copy)
   - "url" (string): Original article URL
   - "source" (string): Publication name
   - "summary" (string): 3-4 sentences explaining what happened and why \
it matters for Tamil schools
   - "why_it_matters" (string): 1-2 sentences on the broader implications

3. "in_brief" (array of objects): 3-5 other noteworthy stories. Each has:
   - "title" (string): Short headline (rewrite for clarity)
   - "url" (string): Original article URL
   - "source" (string): Publication name
   - "sentiment" (string): "positive", "negative", "neutral", or "mixed"
   - "one_liner" (string): One punchy sentence summarising the story

4. "the_number" (object): One striking statistic or figure from the \
articles. Keys:
   - "number" (string): The figure itself (e.g. "47", "RM2.3 million", "3 schools")
   - "context" (string): 1 sentence explaining what this number means

5. "worth_knowing" (string or null): One hidden gem, overlooked detail, \
or emerging trend that most readers would miss. Null if nothing qualifies.

Rules:
- Be specific: use names, amounts, dates, school names.
- The big_story must be the highest-impact article, not just the first one.
- in_brief should cover different topics — don't repeat the big_story.
- Write in British English.
- Do not pad or use filler phrases.
- Return ONLY valid JSON, no markdown fences, no extra text.

--- ARTICLES ---
{articles_block}
--- END ARTICLES ---
"""


def generate_news_digest(days=14) -> dict | None:
    """Generate Economist-style editorial content from recent news articles.

    Args:
        days: Number of days to look back for articles (default: 14).

    Returns:
        dict with editors_note, big_story, in_brief, the_number, worth_knowing.
        None if no articles found, API key missing, or generation fails.
    """
    since = timezone.now() - timedelta(days=days)

    articles = (
        NewsArticle.objects.filter(
            review_status=NewsArticle.APPROVED,
            status=NewsArticle.ANALYSED,
            published_date__gte=since,
        )
        .order_by("-relevance_score", "-published_date")[:15]
    )

    if not articles:
        return None

    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        logger.warning("GEMINI_API_KEY not set — skipping news digest generation")
        return None

    # Build articles block for the prompt
    articles_block = _build_articles_block(articles)

    prompt = DIGEST_PROMPT.format(
        article_count=len(articles),
        days=days,
        articles_block=articles_block,
    )

    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.5,
            ),
        )
        raw_text = response.text.strip()
    except Exception:
        logger.exception("Gemini API call failed for news digest")
        return None

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError:
        logger.error(
            "Gemini returned invalid JSON for news digest: %s",
            raw_text[:200],
        )
        return None

    # Validate required keys
    if not REQUIRED_KEYS.issubset(data.keys()):
        missing = REQUIRED_KEYS - data.keys()
        logger.error("News digest missing required keys: %s", missing)
        return None

    return data


def _build_articles_block(articles) -> str:
    """Build a formatted text block of articles for the Gemini prompt."""
    lines = []
    for rank, article in enumerate(articles, 1):
        schools = ""
        if article.mentioned_schools:
            school_names = [
                s.get("name", "") for s in article.mentioned_schools
                if isinstance(s, dict)
            ]
            schools = ", ".join(school_names) if school_names else ""

        lines.append(
            f"[{rank}] Relevance: {article.relevance_score}/5 | "
            f"Sentiment: {article.sentiment} | "
            f"Urgent: {'YES' if article.is_urgent else 'No'}\n"
            f"Title: {article.title}\n"
            f"Source: {article.source_name} | "
            f"Date: {article.published_date}\n"
            f"URL: {article.url}\n"
            f"Summary: {article.ai_summary}"
        )
        if schools:
            lines[-1] += f"\nSchools mentioned: {schools}"
        lines.append("")  # blank line between articles

    return "\n".join(lines)
