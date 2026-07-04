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

--- NEWS STORIES (clustered) ---
The individual articles above have been clustered into {news_cluster_count} \
distinct stories. THESE are the stories the reader will see in the "In The \
News" section of the email. Your executive_summary MUST be primarily about \
one of these stories, chosen for newsworthiness (biggest funding, most \
significant policy shift, most impactful for the community). If none of the \
clusters is a genuinely big story and Parliament is quiet, say so plainly.

{news_cluster_text}

Return "top_story_cluster_index" as an integer: the 0-based index of the \
cluster your executive_summary features. This is used to promote that \
story to the top of the news section, ensuring subject line + summary + \
news all point at the same story.

--- PREVIOUS MONTH: {previous_month_label} ---
Parliament mentions (showing top {previous_parliament_count} of {previous_parliament_total}):
{previous_parliament_text}

News articles (showing top {previous_news_count} of {previous_news_total}):
{previous_news_text}
--- END DATA ---

CRITICAL RULE — NO STORY REUSE
Each specific story, school name, funding figure, or named MP may appear in
AT MOST ONE analytical section below. If you cite it in `executive_summary`,
it must NOT reappear in `trend_lines`, `opportunity_watch`, or
`school_spotlight`. This forces the four sections to say four different
things instead of four rephrasings of the top story. If a section has
nothing distinct to say after this filter, return an empty array — do not
pad with restatements.

Analyse the data and return a JSON object with these keys:

1. "executive_summary" (string): The single most important development this
month, in 2-3 sentences. Name it once. Include the specifics (school, amount,
MP, date). Compare with previous month IF the comparison is directly relevant.
Written for a busy parent — clear, direct, no jargon. If Parliament was not
in session, say so explicitly. This section OWNS the top story; nothing
below may restate it.

2. "trend_lines" (array of 2-4 objects): DIRECTIONAL statements about
themes, not restatements of stories. Themes: media coverage volume,
funding levels, parliamentary attention, community advocacy, infrastructure
investment, student achievements, policy announcements, land title
resolution. Each object:
   - "trend" (string): The theme, not a story
   - "direction" (string): One of "up", "down", "stable", "new"
   - "detail" (string): 1-2 sentences of DIRECTIONAL evidence: counts,
     percentages, or "N-of-M pattern" statements. DO NOT name the top
     story from `executive_summary` as the exemplar; if a theme was
     driven mostly by one story that's already in the summary, either
     skip that theme or find a different exemplar. Every trend must
     stand on evidence beyond the single headline story.
   RECESS: If Parliament was NOT in session this month, do NOT emit a
   trend with direction="up" or "down" for parliamentary attention — zero
   mentions during recess is structural, not a signal of declining focus.
   Either omit the parliamentary trend entirely OR include it with
   direction="stable" and detail noting the recess explicitly.

3. "opportunity_watch" (array of 1-3 strings): FORWARD-LOOKING actions
stakeholders can take in the next 4-6 weeks. Each 1-2 sentences. Every
opportunity must:
   - Name a specific person, deadline, event, or policy window
   - Be actionable by school boards, parents, or NGOs
   - NOT restate the top story or the trends — this section is about
     what to DO next, not what already happened
   RECESS: If Parliament is in recess, MP outreach in constituencies IS a
   valid opportunity — name specific MPs from the scorecard data.

4. "school_spotlight" (object or null): A HIDDEN GEM — a school with
quiet progress that would otherwise go unnoticed. Explicitly NOT the
school already named in `executive_summary`. Prefer schools with steady
achievement, community initiative, or under-the-radar wins over the
biggest-headline school of the month. Object shape:
   - "name" (string): School name
   - "reason" (string): 1-2 sentences on why it deserves attention that
     it wouldn't get otherwise.
   Set to null if no such quieter school stood out.

5. "headline" (string): A short, punchy single-line headline (max 70 chars) \
capturing the most important news of the month, suitable for an email subject \
line. **ONE story only — never join two stories with a semicolon, "and", "+" \
or "&".** Lead with the single most newsworthy specific item (a policy \
announcement, a funding figure, a major project milestone). Avoid generic \
phrasing like "Monthly update". Examples of good style: "Special ed coming to \
Tamil schools in 2027" or "RM15.7M committed to SJK(T) infrastructure". \
Counter-example to avoid: "Funding boost; new playground opens" — pick one. \
If the month is genuinely quiet, return a calm honest line rather than \
fabricating drama. **The headline must be about the same story as your \
executive_summary and top_story_cluster_index.**

6. "top_story_cluster_index" (integer): The 0-based index of the news \
cluster your executive_summary + headline are primarily about, using the \
NEWS STORIES list above. This is required whenever news clusters are \
present. If there are zero news clusters this month (a completely quiet \
month), return -1.

Rules:
- Be specific: use names, amounts, dates, constituency names from the data.
- Compare current vs previous month wherever it adds signal.
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


def _format_clusters(clusters) -> str:
    """Format news clusters as a numbered list for the analyst prompt.

    Each line: "Cluster N: <headline> - K articles, relevance R, SENTIMENT
    | <lead-article summary excerpt>". Skips the "Other" bucket — that
    isn't a story the reader will see as a card.
    """
    if not clusters:
        return "No news clusters this month."
    lines = []
    idx = 0
    for c in clusters:
        if c.get("is_other"):
            continue
        headline = c.get("headline", "") or "(no headline)"
        n = c.get("article_count", 0)
        rel = c.get("max_relevance", 0)
        sentiment = c.get("sentiment_majority", "NEUTRAL")
        summary = (c.get("story_summary", "") or "")[:220]
        lines.append(
            f"Cluster {idx}: {headline} - {n} article{'s' if n != 1 else ''}, "
            f"relevance {rel}/5, {sentiment}"
            f"{' | ' + summary if summary else ''}"
        )
        idx += 1
    return "\n".join(lines) if lines else "No news clusters this month."


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
    news_clusters: list | None = None,
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
        news_clusters: List of clustered news stories from
            topic_clusterer.cluster_news_articles(). When supplied, the
            analyst is CONSTRAINED to pick its executive_summary top
            story from these clusters, and returns a
            `top_story_cluster_index` so the caller can promote that
            cluster to position #1 in the "In The News" section. This
            closes the coherence gap where the subject line named a
            story that never appeared in the news list (audit 2026-07-05).

    Returns:
        dict with executive_summary, trend_lines, opportunity_watch,
        school_spotlight, headline, top_story_cluster_index, by_the_numbers.
        None if API key missing, generation fails, or response invalid.

        Audit 2026-07-05a: dropped `emerging_signals` and `fading_from_view`
        after a reader-repetition audit found the two sections restated the
        top story instead of surfacing distinct ones.
        Audit 2026-07-05b: added news_clusters constraint + top_story_
        cluster_index return field so the subject line, executive_summary,
        and top news card always point at the same story.
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
    # Count non-Other clusters — Other is a rolled-up bucket, not a card.
    real_clusters = [
        c for c in (news_clusters or []) if not c.get("is_other")
    ]
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
        news_cluster_count=len(real_clusters),
        news_cluster_text=_format_clusters(news_clusters or []),
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
