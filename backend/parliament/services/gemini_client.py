"""Gemini Flash API client for analysing Hansard mentions.

Sends a structured prompt with the mention verbatim quote + context,
and receives back a JSON object with fields:
  mp_name, mp_constituency, mp_party, mention_type, significance,
  sentiment, change_indicator, summary

Token budgeting: only sends ~1500 chars (mention + context), never
the full Hansard text.

Uses the google.genai SDK (not the deprecated google.generativeai).
"""

import json
import logging
import os
import time

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

# Valid enum values for validation
MENTION_TYPES = {"BUDGET", "QUESTION", "POLICY", "COMMITMENT", "THROWAWAY", "OTHER"}
SENTIMENTS = {"ADVOCATING", "DEFLECTING", "PROMISING", "NEUTRAL", "CRITICAL"}
CHANGE_INDICATORS = {"NEW", "REPEAT", "ESCALATION", "REVERSAL"}

ANALYSIS_PROMPT = """\
You are analysing a Malaysian parliamentary Hansard excerpt that mentions Tamil schools (SJK(T)).

Extract the following fields as a JSON object:
- mp_name: Name of the MP speaking (string, or "" if unclear)
- mp_constituency: Parliamentary constituency of the MP (string, or "" if unclear)
- mp_party: Political party of the MP (string, or "" if unclear)
- mention_type: One of BUDGET, QUESTION, POLICY, COMMITMENT, THROWAWAY, OTHER
  - BUDGET: Allocation, funding, or financial request
  - QUESTION: Parliamentary question (oral or written)
  - POLICY: Policy discussion, proposal, or announcement
  - COMMITMENT: Specific promise or pledge by MP/minister
  - THROWAWAY: Passing mention without substance
  - OTHER: Does not fit the above categories
- significance: Integer 1-5 (1 = trivial passing mention, 5 = major debate/commitment)
- sentiment: One of ADVOCATING, DEFLECTING, PROMISING, NEUTRAL, CRITICAL
- change_indicator: One of NEW, REPEAT, ESCALATION, REVERSAL
  - NEW: First time this topic is raised in this context
  - REPEAT: Previously raised, no change in stance
  - ESCALATION: Stronger language or urgency than before
  - REVERSAL: Changed position from previous stance
- summary: 1-2 sentence English summary of what was said about Tamil schools

Return ONLY valid JSON, no markdown fences, no extra text.

--- HANSARD EXCERPT ---
{excerpt}
--- END EXCERPT ---
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


def _build_excerpt(mention):
    """Build a token-budgeted excerpt from a mention.

    Concatenates context_before + verbatim_quote + context_after,
    truncating to ~1500 chars total.
    """
    parts = []
    if mention.context_before:
        parts.append(mention.context_before.strip())
    parts.append(mention.verbatim_quote.strip())
    if mention.context_after:
        parts.append(mention.context_after.strip())

    excerpt = "\n\n".join(parts)

    # Truncate to ~1500 chars to stay within token budget
    max_chars = 1500
    if len(excerpt) > max_chars:
        excerpt = excerpt[:max_chars] + "..."

    return excerpt


def _validate_response(data):
    """Validate and normalise the Gemini response fields.

    Returns a clean dict with all expected fields, filling in defaults
    for any missing or invalid values.
    """
    result = {
        "mp_name": str(data.get("mp_name", "")).strip(),
        "mp_constituency": str(data.get("mp_constituency", "")).strip(),
        "mp_party": str(data.get("mp_party", "")).strip(),
        "mention_type": str(data.get("mention_type", "OTHER")).strip().upper(),
        "significance": data.get("significance"),
        "sentiment": str(data.get("sentiment", "NEUTRAL")).strip().upper(),
        "change_indicator": str(data.get("change_indicator", "NEW")).strip().upper(),
        "summary": str(data.get("summary", "")).strip(),
    }

    # Clamp enum fields to valid values
    if result["mention_type"] not in MENTION_TYPES:
        result["mention_type"] = "OTHER"
    if result["sentiment"] not in SENTIMENTS:
        result["sentiment"] = "NEUTRAL"
    if result["change_indicator"] not in CHANGE_INDICATORS:
        result["change_indicator"] = "NEW"

    # Clamp significance to 1-5
    try:
        sig = int(result["significance"])
        result["significance"] = max(1, min(5, sig))
    except (TypeError, ValueError):
        result["significance"] = 1

    return result


def analyse_mention(mention):
    """Analyse a single HansardMention using Gemini Flash.

    Args:
        mention: HansardMention instance with verbatim_quote and context fields.

    Returns:
        dict with validated analysis fields, or None on failure.

    Raises:
        ValueError: If GEMINI_API_KEY is not set.
    """
    client = _get_client()

    excerpt = _build_excerpt(mention)
    prompt = ANALYSIS_PROMPT.format(excerpt=excerpt)

    max_retries = 3
    for attempt in range(max_retries):
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
            break
        except Exception as e:
            if "429" in str(e) and attempt < max_retries - 1:
                wait = 15 * (attempt + 1)
                logger.info("Rate limited, waiting %ds...", wait)
                time.sleep(wait)
                continue
            logger.exception("Gemini API call failed for mention %s", mention.pk)
            return None

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError:
        logger.error(
            "Gemini returned invalid JSON for mention %s: %s",
            mention.pk, raw_text[:200],
        )
        return None

    result = _validate_response(data)
    result["raw_response"] = data
    return result


def apply_analysis(mention, analysis):
    """Apply validated analysis dict to a HansardMention and save.

    Args:
        mention: HansardMention instance.
        analysis: dict from analyse_mention().
    """
    mention.mp_name = analysis["mp_name"]
    mention.mp_constituency = analysis["mp_constituency"]
    mention.mp_party = analysis["mp_party"]
    mention.mention_type = analysis["mention_type"]
    mention.significance = analysis["significance"]
    mention.sentiment = analysis["sentiment"]
    mention.change_indicator = analysis["change_indicator"]
    mention.ai_summary = analysis["summary"]
    mention.ai_raw_response = analysis.get("raw_response", {})
    mention.save(update_fields=[
        "mp_name", "mp_constituency", "mp_party", "mention_type",
        "significance", "sentiment", "change_indicator",
        "ai_summary", "ai_raw_response", "updated_at",
    ])
