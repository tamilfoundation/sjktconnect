"""Urgent alert generator — concise, action-focused alerts via Gemini.

Takes a single NewsArticle flagged as urgent and generates structured
content for an immediate action alert email.

Returns a dict with: what_happened, who_affected, what_you_can_do, deadline.

Uses the google.genai SDK (same pattern as broadcasts/services/parliament_digest.py).
"""

import json
import logging
import os

from google import genai
from google.genai import types

from newswatch.models import NewsArticle

logger = logging.getLogger(__name__)

REQUIRED_KEYS = {"what_happened", "who_affected", "what_you_can_do"}

ALERT_PROMPT = """\
You are writing an URGENT ACTION ALERT about a crisis affecting Malaysian \
Tamil schools (SJK(T)). This alert goes directly to parents, school board \
members, NGOs, and community leaders who need to act immediately.

The article below has been flagged as urgent. Reason: {urgent_reason}

--- ARTICLE ---
Title: {title}
Source: {source_name}
Date: {published_date}
URL: {url}

{body_text}

--- AI SUMMARY ---
{ai_summary}
--- END ---

Generate a concise, action-focused alert. Return a JSON object with these keys:

1. "what_happened" (string): 2-3 sentences explaining what happened. \
Be factual, specific, and direct. Name the school(s), location, and \
the nature of the threat.

2. "who_affected" (string): 1-2 sentences identifying who is directly \
affected — students, teachers, parents, community. Include numbers \
and location details if available.

3. "what_you_can_do" (string): 2-4 sentences with specific, concrete \
actions readers can take RIGHT NOW. Name who to contact, what to say, \
where to go. Include addresses, reference numbers, or template phrases \
if the article provides them.

4. "deadline" (string or null): If there is a deadline for action \
(consultation period, submission date, etc.), state it clearly. \
Null if no specific deadline is mentioned.

Rules:
- Be specific: use names, dates, locations, reference numbers.
- Actions must be concrete and achievable by ordinary people.
- Keep it short — this is an emergency alert, not a newsletter.
- Write in British English.
- Do not pad or use filler phrases.
- Return ONLY valid JSON, no markdown fences, no extra text.
"""


def generate_urgent_alert(article: "NewsArticle") -> dict | None:
    """Generate action-focused alert content for an urgent NewsArticle.

    Args:
        article: NewsArticle instance flagged as urgent.

    Returns:
        dict with what_happened, who_affected, what_you_can_do, deadline.
        None if article is not urgent, not approved, API key missing,
        or generation fails.
    """
    if not article.is_urgent:
        return None

    if article.review_status != NewsArticle.APPROVED:
        return None

    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        logger.warning("GEMINI_API_KEY not set — skipping urgent alert generation")
        return None

    prompt = ALERT_PROMPT.format(
        urgent_reason=article.urgent_reason or "Not specified",
        title=article.title,
        source_name=article.source_name,
        published_date=article.published_date,
        url=article.url,
        body_text=article.body_text[:3000],  # Cap body to avoid token limits
        ai_summary=article.ai_summary,
    )

    try:
        client = genai.Client(api_key=api_key)
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
        logger.exception("Gemini API call failed for urgent alert")
        return None

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError:
        logger.error(
            "Gemini returned invalid JSON for urgent alert: %s",
            raw_text[:200],
        )
        return None

    # Validate required keys
    if not REQUIRED_KEYS.issubset(data.keys()):
        missing = REQUIRED_KEYS - data.keys()
        logger.error("Urgent alert missing required keys: %s", missing)
        return None

    return data
