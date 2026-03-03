"""Gemini Flash API client for analysing news articles about Tamil schools.

Sends article title + body text (truncated to ~3000 chars) to Gemini,
receives back a JSON object with:
  relevance_score, sentiment, summary, mentioned_schools, is_urgent, urgent_reason

Follows the same pattern as parliament/services/gemini_client.py.
"""

import json
import logging
import os

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

# Valid enum values for validation
SENTIMENTS = {"POSITIVE", "NEGATIVE", "NEUTRAL", "MIXED"}

ANALYSIS_PROMPT = """\
You are analysing a news article that may be about Malaysian Tamil schools (SJK(T)).

Analyse the article and return a JSON object with these fields:

- relevance_score: Integer 1-5
  - 1: No mention of Tamil schools, unrelated
  - 2: Passing mention, not the focus
  - 3: Mentions Tamil schools as part of a broader topic
  - 4: Primarily about Tamil schools
  - 5: Entirely focused on Tamil schools, major news

- sentiment: One of POSITIVE, NEGATIVE, NEUTRAL, MIXED
  - POSITIVE: Good news for Tamil schools (funding, improvements, recognition)
  - NEGATIVE: Bad news (closures, problems, neglect, declining enrolment)
  - NEUTRAL: Factual reporting without clear positive/negative slant
  - MIXED: Contains both positive and negative aspects

- summary: 2-3 sentence English summary focused on what this means for Tamil schools.
  Be specific about names, locations, and figures mentioned.

- mentioned_schools: Array of objects for SJK(T) / Tamil schools ONLY.
  Do NOT include non-Tamil schools (SK, SMK, SJK(C), SRJK(C), etc.).
  Each object has:
  - name: School name as mentioned in the article (string)
  - moe_code: MOE code if identifiable (string, or "" if unknown)
  Keep empty array [] if no specific Tamil schools are named.

- is_urgent: Boolean. True ONLY if the article reports:
  - School closure or merger threat
  - Safety crisis (building collapse, flood, etc.)
  - Student/teacher safety issue
  - Funding cut or budget crisis affecting operations
  - Political controversy requiring immediate response

- urgent_reason: If is_urgent is true, one sentence explaining why.
  Empty string if not urgent.

Return ONLY valid JSON, no markdown fences, no extra text.

--- ARTICLE ---
Title: {title}

{body}
--- END ARTICLE ---
"""


def _get_client():
    """Create a Gemini API client with the API key."""
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY environment variable is not set. "
            "Get one from https://aistudio.google.com/apikey"
        )
    return genai.Client(api_key=api_key)


def _build_body(article):
    """Build a token-budgeted body from an article.

    Uses title + first ~3000 chars of body text.
    """
    body = article.body_text.strip()
    max_chars = 3000
    if len(body) > max_chars:
        body = body[:max_chars] + "..."
    return body


def _validate_response(data):
    """Validate and normalise the Gemini response fields.

    Returns a clean dict with all expected fields, filling in defaults
    for any missing or invalid values.
    """
    result = {
        "relevance_score": data.get("relevance_score"),
        "sentiment": str(data.get("sentiment", "NEUTRAL")).strip().upper(),
        "summary": str(data.get("summary", "")).strip(),
        "mentioned_schools": data.get("mentioned_schools", []),
        "is_urgent": bool(data.get("is_urgent", False)),
        "urgent_reason": str(data.get("urgent_reason", "")).strip(),
    }

    # Clamp sentiment to valid values
    if result["sentiment"] not in SENTIMENTS:
        result["sentiment"] = "NEUTRAL"

    # Clamp relevance_score to 1-5
    try:
        score = int(result["relevance_score"])
        result["relevance_score"] = max(1, min(5, score))
    except (TypeError, ValueError):
        result["relevance_score"] = 1

    # Ensure mentioned_schools is a list
    if not isinstance(result["mentioned_schools"], list):
        result["mentioned_schools"] = []

    # Clean up urgent_reason if not urgent
    if not result["is_urgent"]:
        result["urgent_reason"] = ""

    return result


def analyse_article(article):
    """Analyse a single NewsArticle using Gemini Flash.

    Args:
        article: NewsArticle instance with body_text populated.

    Returns:
        dict with validated analysis fields, or None on failure.

    Raises:
        ValueError: If GEMINI_API_KEY is not set.
    """
    client = _get_client()

    body = _build_body(article)
    prompt = ANALYSIS_PROMPT.format(title=article.title, body=body)

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.1,
            ),
        )
        raw_text = response.text.strip()
    except Exception:
        logger.exception("Gemini API call failed for article %s", article.pk)
        return None

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError:
        logger.error(
            "Gemini returned invalid JSON for article %s: %s",
            article.pk, raw_text[:200],
        )
        return None

    result = _validate_response(data)
    result["raw_response"] = data
    return result


def apply_analysis(article, analysis):
    """Apply validated analysis dict to a NewsArticle and save.

    Sets status to ANALYSED and populates all AI fields.

    Args:
        article: NewsArticle instance.
        analysis: dict from analyse_article().
    """
    from newswatch.models import NewsArticle as NA

    article.relevance_score = analysis["relevance_score"]
    article.sentiment = analysis["sentiment"]
    article.ai_summary = analysis["summary"]
    article.mentioned_schools = analysis["mentioned_schools"]
    article.is_urgent = analysis["is_urgent"]
    article.urgent_reason = analysis["urgent_reason"]
    article.ai_raw_response = analysis.get("raw_response", {})
    article.status = NA.ANALYSED

    # Auto-approve articles with relevance_score >= 3
    if article.relevance_score and article.relevance_score >= 3:
        article.review_status = NA.APPROVED

    article.save(update_fields=[
        "relevance_score", "sentiment", "ai_summary", "mentioned_schools",
        "is_urgent", "urgent_reason", "ai_raw_response", "status",
        "review_status", "updated_at",
    ])


def analyse_pending_articles(batch_size=10):
    """Analyse all EXTRACTED articles that haven't been analysed yet.

    Args:
        batch_size: Maximum number of articles to process in one run.

    Returns:
        dict with counts: {"analysed": int, "failed": int, "skipped": int}
    """
    from newswatch.models import NewsArticle as NA

    articles = NA.objects.filter(status=NA.EXTRACTED).order_by("created_at")[:batch_size]

    counts = {"analysed": 0, "failed": 0, "skipped": 0}

    for article in articles:
        if not article.body_text.strip():
            counts["skipped"] += 1
            continue

        analysis = analyse_article(article)
        if analysis is None:
            counts["failed"] += 1
            continue

        apply_analysis(article, analysis)
        counts["analysed"] += 1
        logger.info(
            "Analysed article %s: relevance=%s, urgent=%s",
            article.pk, analysis["relevance_score"], analysis["is_urgent"],
        )

    return counts
