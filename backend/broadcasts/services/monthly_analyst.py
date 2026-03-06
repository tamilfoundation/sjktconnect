"""Monthly Intelligence Blast analyst — trend analysis via Gemini.

Takes aggregated month data (parliament mentions, news articles, scorecards)
for the current and previous months, sends to Gemini for comparative analysis,
and returns structured analytical content: trends, emerging signals, fading
issues, opportunities, and a school spotlight.

Uses the google.genai SDK (same pattern as parliament_digest.py).
"""

import calendar
import json
import logging
import os

from google import genai
from google.genai import types

from broadcasts.services.blast_aggregator import aggregate_month

logger = logging.getLogger(__name__)

REQUIRED_KEYS = {"executive_summary", "trend_lines", "by_the_numbers"}

ANALYST_PROMPT = """\
You are an intelligence analyst writing a monthly brief about Tamil schools \
(SJK(T)) in Malaysia for stakeholders — parents, school board members, NGOs, \
and community leaders.

Below is data from TWO months so you can identify trends and changes.

--- CURRENT MONTH: {current_month_label} ---
Parliament mentions ({current_parliament_count}):
{current_parliament_text}

News articles ({current_news_count}):
{current_news_text}

Top MP scorecards:
{current_scorecard_text}

--- PREVIOUS MONTH: {previous_month_label} ---
Parliament mentions ({previous_parliament_count}):
{previous_parliament_text}

News articles ({previous_news_count}):
{previous_news_text}
--- END DATA ---

Analyse the data and return a JSON object with these keys:

1. "executive_summary" (string): 3-4 sentences summarising the month. Compare \
with previous month. Highlight the single most important development. Written \
for a busy parent — clear, direct, no jargon.

2. "trend_lines" (array of objects): Each trend has:
   - "trend" (string): Short label (e.g. "Parliamentary attention")
   - "direction" (string): One of "up", "down", "stable", "new"
   - "detail" (string): 1-2 sentences explaining the trend with specific \
numbers or comparisons.
   Include 2-4 trends.

3. "emerging_signals" (array of strings): 1-3 new patterns or developments \
that appeared this month and deserve attention. Each 1-2 sentences.

4. "fading_from_view" (array of strings): 1-2 issues that were active before \
but received less attention this month. Each 1-2 sentences. Can be empty.

5. "opportunity_watch" (array of strings): 1-3 actionable opportunities \
stakeholders should act on. Be specific — name people, deadlines, or events.

6. "school_spotlight" (object or null): If a specific school stood out this \
month, include:
   - "name" (string): School name
   - "reason" (string): 1-2 sentences on why it stood out.
   Set to null if no school was particularly notable.

7. "by_the_numbers" (object): Key statistics:
   - "parliament_mentions" (int): Total mentions this month
   - "news_articles" (int): Total news articles this month
   - "schools_affected" (int): Approximate unique schools mentioned
   - "sentiment_positive" (int): Count of positive sentiment items
   - "sentiment_negative" (int): Count of negative sentiment items

Rules:
- Be specific: use names, amounts, dates, constituency names from the data.
- Compare current vs previous month wherever possible.
- Write in British English.
- Do not pad or use filler phrases.
- If data is sparse, say so honestly — do not fabricate trends.
- Return ONLY valid JSON, no markdown fences, no extra text.
"""


def _format_parliament(queryset) -> str:
    """Format parliament mentions into text blocks for the prompt."""
    items = list(queryset)
    if not items:
        return "No parliament mentions this month."
    lines = []
    for m in items:
        sitting_date = m.sitting.sitting_date.strftime("%d %b %Y") if hasattr(m, "sitting") and m.sitting else "Unknown"
        lines.append(
            f"- {m.mp_name} ({m.mp_constituency or 'Unknown'}), "
            f"{sitting_date}, significance {m.significance}/5"
            f"{': ' + m.ai_summary if m.ai_summary else ''}"
        )
    return "\n".join(lines)


def _format_news(queryset) -> str:
    """Format news articles into text blocks for the prompt."""
    items = list(queryset)
    if not items:
        return "No news articles this month."
    lines = []
    for a in items:
        pub_date = a.published_date.strftime("%d %b %Y") if a.published_date else "Unknown"
        lines.append(
            f"- [{a.source_name or 'Unknown'}] {a.title} ({pub_date}), "
            f"relevance {a.relevance_score}/5, sentiment: {a.sentiment}"
            f"{': ' + a.ai_summary[:200] if a.ai_summary else ''}"
        )
    return "\n".join(lines)


def _format_scorecards(queryset) -> str:
    """Format MP scorecards into text blocks for the prompt."""
    items = list(queryset)
    if not items:
        return "No scorecard data available."
    lines = []
    for sc in items:
        lines.append(
            f"- {sc.mp_name} ({sc.constituency or 'Unknown'}): "
            f"{sc.total_mentions} mentions, {sc.substantive_mentions} substantive"
        )
    return "\n".join(lines)


def _previous_month(year: int, month: int) -> tuple[int, int]:
    """Return (year, month) for the month before the given one."""
    if month == 1:
        return year - 1, 12
    return year, month - 1


def generate_monthly_analysis(year: int, month: int) -> dict | None:
    """Generate analytical monthly content via Gemini.

    Aggregates data for the current and previous months, sends to Gemini
    for comparative trend analysis.

    Args:
        year: Target year.
        month: Target month (1-12).

    Returns:
        dict with executive_summary, trend_lines, emerging_signals,
        fading_from_view, opportunity_watch, school_spotlight, by_the_numbers.
        None if API key missing, generation fails, or response invalid.
    """
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        logger.warning("GEMINI_API_KEY not set — skipping monthly analysis")
        return None

    # Aggregate current and previous months
    current_data = aggregate_month(year, month)
    prev_year, prev_month = _previous_month(year, month)
    previous_data = aggregate_month(prev_year, prev_month)

    current_month_label = f"{calendar.month_name[month]} {year}"
    previous_month_label = f"{calendar.month_name[prev_month]} {prev_year}"

    prompt = ANALYST_PROMPT.format(
        current_month_label=current_month_label,
        current_parliament_count=len(list(current_data["parliament"])),
        current_parliament_text=_format_parliament(current_data["parliament"]),
        current_news_count=len(list(current_data["news"])),
        current_news_text=_format_news(current_data["news"]),
        current_scorecard_text=_format_scorecards(current_data["scorecards"]),
        previous_month_label=previous_month_label,
        previous_parliament_count=len(list(previous_data["parliament"])),
        previous_parliament_text=_format_parliament(previous_data["parliament"]),
        previous_news_count=len(list(previous_data["news"])),
        previous_news_text=_format_news(previous_data["news"]),
    )

    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.4,
            ),
        )
        raw_text = response.text.strip()
    except Exception:
        logger.exception("Gemini API call failed for monthly analysis")
        return None

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError:
        logger.error(
            "Gemini returned invalid JSON for monthly analysis: %s",
            raw_text[:200],
        )
        return None

    # Validate required keys
    if not REQUIRED_KEYS.issubset(data.keys()):
        missing = REQUIRED_KEYS - data.keys()
        logger.error("Monthly analysis missing required keys: %s", missing)
        return None

    return data
