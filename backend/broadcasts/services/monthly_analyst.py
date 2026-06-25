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
from datetime import date

from google import genai
from google.genai import types

from broadcasts.services.blast_aggregator import aggregate_month

logger = logging.getLogger(__name__)

# Sprint 23: by_the_numbers is no longer in REQUIRED_KEYS — it's
# composed in Python from real DB counts (see _compose_by_the_numbers
# below) and merged into the analysis dict before returning.
REQUIRED_KEYS = {"executive_summary", "trend_lines"}

ANALYST_PROMPT = """\
You are an intelligence analyst writing a monthly brief about Tamil schools \
(SJK(T)) in Malaysia for stakeholders — parents, school board members, NGOs, \
and community leaders.

Below is data from TWO months so you can identify trends and changes.

IMPORTANT: The lists below are SAMPLES (top items by relevance/significance) \
from a larger pool. The TRUE TOTALS for the current month are:
  - Parliament was {current_parliament_session_state} ({current_parliament_sitting_count} sittings)
  - {current_parliament_total} parliamentary mentions of SJK(T)s
  - {current_news_total} approved news articles ({current_sentiment_pos} positive, \
{current_sentiment_neg} negative, {current_sentiment_neu} neutral)
  - {current_schools_total} unique schools mentioned across news + parliament
Use these totals when discussing scale or volume. Do NOT invent counts.

--- CURRENT MONTH: {current_month_label} ---
Parliament mentions (showing top {current_parliament_count} of {current_parliament_total}):
{current_parliament_text}

Sitting briefs ({current_brief_count}):
{current_brief_text}

Meeting reports ({current_meeting_count}):
{current_meeting_text}

News articles (showing top {current_news_count} of {current_news_total}):
{current_news_text}

Top MP scorecards{current_scorecard_qualifier}:
{current_scorecard_text}

--- PREVIOUS MONTH: {previous_month_label} ---
Parliament mentions (showing top {previous_parliament_count} of {previous_parliament_total}):
{previous_parliament_text}

News articles (showing top {previous_news_count} of {previous_news_total}):
{previous_news_text}
--- END DATA ---

Analyse the data and return a JSON object with these keys:

1. "executive_summary" (string): 3-4 sentences summarising the month. Compare \
with previous month. Highlight the single most important development. Written \
for a busy parent — clear, direct, no jargon. If Parliament was not in session, \
say so explicitly rather than treating zero mentions as a signal.

2. "trend_lines" (array of objects): Each trend has:
   - "trend" (string): Short label (e.g. "Parliamentary attention")
   - "direction" (string): One of "up", "down", "stable", "new"
   - "detail" (string): 1-2 sentences explaining the trend with specific \
numbers or comparisons.
   Include 2-4 trends.
   RECESS: If Parliament was NOT in session this month, do NOT emit a \
trend with direction="up" or "down" for parliamentary attention — zero \
mentions during recess is structural, not a signal of declining focus. \
Either omit the parliamentary trend entirely OR include it with \
direction="stable" and detail noting the recess explicitly (e.g. \
"Parliament in recess; next sitting expected MONTH YYYY.").

3. "emerging_signals" (array of strings): 1-3 new patterns or developments \
that appeared this month and deserve attention. Each 1-2 sentences. \
RECESS: If Parliament was NOT in session, do NOT cite parliamentary \
patterns as emerging signals — focus on news, NGO, private sector, or \
community signals.

4. "fading_from_view" (array of strings): 1-2 issues that were active before \
but received less attention this month. Each 1-2 sentences. Can be empty. \
RECESS: If Parliament was NOT in session, do NOT list parliamentary \
discourse as "fading" — recess is structural, not a fade. A topic only \
counts as fading if it was active in both months and dropped off; do not \
compare a recess month against a sitting month for parliamentary topics.

5. "opportunity_watch" (array of strings): 1-3 actionable opportunities \
stakeholders should act on. Be specific — name people, deadlines, or events. \
RECESS: If Parliament is in recess, MP outreach IS a valid opportunity — \
MPs are most reachable in their constituencies during recess. Suggest \
specific MPs (from the scorecard data) and what to raise with them.

6. "school_spotlight" (object or null): If a specific school stood out this \
month, include:
   - "name" (string): School name
   - "reason" (string): 1-2 sentences on why it stood out.
   Set to null if no school was particularly notable.

7. "headline" (string): A short, punchy single-line headline (max 70 chars) \
capturing the most important news of the month, suitable for an email subject \
line. **ONE story only — never join two stories with a semicolon, "and", "+" \
or "&".** Lead with the single most newsworthy specific item (a policy \
announcement, a funding figure, a major project milestone). Avoid generic \
phrasing like "Monthly update". Examples of good style: "Special ed coming to \
Tamil schools in 2027" or "RM15.7M committed to SJK(T) infrastructure". \
Counter-example to avoid: "Funding boost; new playground opens" — pick one. \
If the month is genuinely quiet, return a calm honest line rather than \
fabricating drama.

Rules:
- Be specific: use names, amounts, dates, constituency names from the data.
- Compare current vs previous month wherever possible.
- Write in British English.
- Do not pad or use filler phrases.
- If data is sparse, say so honestly — do not fabricate trends or counts.
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


def _format_briefs(queryset) -> str:
    """Format sitting briefs into text blocks for the prompt."""
    items = list(queryset)
    if not items:
        return "No sitting briefs published this period."
    lines = []
    for b in items:
        sitting_date = b.sitting.sitting_date.strftime("%d %b %Y") if b.sitting else "Unknown"
        lines.append(f"- [{sitting_date}] {b.title}")
    return "\n".join(lines)


def _format_meetings(queryset) -> str:
    """Format meeting reports into text blocks for the prompt."""
    items = list(queryset)
    if not items:
        return "No meeting reports active this period."
    lines = []
    for m in items:
        period = (
            f"{m.start_date.strftime('%d %b')} \u2192 "
            f"{m.end_date.strftime('%d %b %Y')}"
        )
        summary = (m.executive_summary or "")[:200].replace("\n", " ").strip()
        lines.append(f"- {m.short_name} ({period}): {summary}")
    return "\n".join(lines)


def _previous_month(year: int, month: int) -> tuple[int, int]:
    """Return (year, month) for the month before the given one."""
    if month == 1:
        return year - 1, 12
    return year, month - 1


def _compose_by_the_numbers(current_data: dict) -> dict:
    """Sprint 23: build by_the_numbers from real DB counts.

    Replaces the previous LLM-imputed version which counted from a
    5-row text sample and routinely fabricated schools_affected and
    sentiment counts.
    """
    sentiment = current_data.get("news_sentiment_breakdown") or {}
    return {
        "parliament_mentions": current_data.get("parliament_total", 0),
        "news_articles": current_data.get("news_total", 0),
        "schools_affected": current_data.get("schools_mentioned_total", 0),
        "sentiment_positive": sentiment.get("positive", 0),
        "sentiment_negative": sentiment.get("negative", 0),
    }


def generate_monthly_analysis(
    year: int,
    month: int,
    backfill_since: date | None = None,
) -> dict | None:
    """Generate analytical monthly content via Gemini.

    Aggregates data for the current and previous months, sends to Gemini
    for comparative trend analysis.

    Args:
        year: Target year.
        month: Target month (1-12).
        backfill_since: Forwarded to aggregate_month — see its docstring.
            Sprint 18 added so a one-time digest can pull older briefs +
            meeting reports that prior digests missed.

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
    current_data = aggregate_month(year, month, backfill_since=backfill_since)
    prev_year, prev_month = _previous_month(year, month)
    previous_data = aggregate_month(prev_year, prev_month)

    current_month_label = f"{calendar.month_name[month]} {year}"
    previous_month_label = f"{calendar.month_name[prev_month]} {prev_year}"

    scorecard_qualifier = (
        " (lifetime fallback — no MP active this month)"
        if current_data["scorecards_are_lifetime_fallback"]
        else ""
    )

    sentiment = current_data.get("news_sentiment_breakdown") or {}
    prompt = ANALYST_PROMPT.format(
        current_month_label=current_month_label,
        current_parliament_count=len(list(current_data["parliament"])),
        current_parliament_total=current_data.get("parliament_total", 0),
        current_parliament_text=_format_parliament(current_data["parliament"]),
        current_parliament_session_state=(
            "in session" if current_data.get("parliament_was_in_session")
            else "not in session"
        ),
        current_parliament_sitting_count=current_data.get("parliament_sitting_count", 0),
        current_brief_count=len(list(current_data["briefs"])),
        current_brief_text=_format_briefs(current_data["briefs"]),
        current_meeting_count=len(list(current_data["meeting_reports"])),
        current_meeting_text=_format_meetings(current_data["meeting_reports"]),
        current_news_count=len(list(current_data["news"])),
        current_news_total=current_data.get("news_total", 0),
        current_news_text=_format_news(current_data["news"]),
        current_sentiment_pos=sentiment.get("positive", 0),
        current_sentiment_neg=sentiment.get("negative", 0),
        current_sentiment_neu=sentiment.get("neutral", 0),
        current_schools_total=current_data.get("schools_mentioned_total", 0),
        current_scorecard_qualifier=scorecard_qualifier,
        current_scorecard_text=_format_scorecards(current_data["scorecards"]),
        previous_month_label=previous_month_label,
        previous_parliament_count=len(list(previous_data["parliament"])),
        previous_parliament_total=previous_data.get("parliament_total", 0),
        previous_parliament_text=_format_parliament(previous_data["parliament"]),
        previous_news_count=len(list(previous_data["news"])),
        previous_news_total=previous_data.get("news_total", 0),
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

    # Sprint 23: overlay deterministic by_the_numbers onto the LLM
    # output. If the LLM returned its own by_the_numbers (the prompt no
    # longer asks for it, but tolerate extras), we replace it. The
    # downstream template references analysis.by_the_numbers.* so the
    # key must exist with the right shape.
    data["by_the_numbers"] = _compose_by_the_numbers(current_data)

    return data
