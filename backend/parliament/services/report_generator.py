"""Meeting report generator — synthesises sitting briefs into an executive report.

Uses Gemini Flash to generate an HTML report, executive summary, and social
post for a ParliamentaryMeeting based on its SittingBrief records.

Uses the google.genai SDK (same as gemini_client.py).
"""

import datetime
import json
import logging
import os

from parliament.models import ParliamentaryMeeting, SittingBrief

logger = logging.getLogger(__name__)

REPORT_PROMPT = """\
You are writing an executive intelligence brief about Tamil schools (SJK(T)) \
in the Malaysian parliament for Tamil school stakeholders — parents, teachers, \
NGOs, and community leaders.

Below are the sitting-by-sitting summaries from {meeting_name} \
({start_date} to {end_date}, {sitting_count} sittings with Tamil school mentions).

Write a meeting report with these sections:
1. **Key Findings** — the 3-5 most important takeaways
2. **MP Activity** — which MPs raised Tamil school issues, how substantive
3. **Policy Signals** — any policy changes, commitments, or budget allocations
4. **What to Watch** — issues likely to resurface or need community attention

Rules:
- Be factual and analytical. Every sentence must add information or insight.
- Length must match substance. A quiet meeting: 200 words. A significant one: up to 1,000.
- Do not repeat what individual briefs say — synthesise and draw connections.
- Do not pad, ramble, or use filler phrases.
- Write in British English.
- Output valid HTML (use <h2>, <p>, <ul>, <li> tags). No markdown.

Also provide:
- executive_summary: 2-3 sentences for a preview card (plain text, no HTML)
- social_post_text: max 280 characters for social media

Return as JSON with keys: report_html, executive_summary, social_post_text

--- SITTING SUMMARIES ---
{briefs}
--- END SUMMARIES ---
"""


def _call_gemini(prompt: str) -> dict | None:
    """Call Gemini Flash and return parsed JSON dict, or None on failure."""
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        logger.warning("GEMINI_API_KEY not set — skipping report generation")
        return None

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.2,
            ),
        )
        data = json.loads(response.text.strip())
        return data
    except Exception:
        logger.exception("Gemini API call failed for meeting report")
        return None


def generate_meeting_report(meeting: ParliamentaryMeeting) -> bool:
    """Generate an AI report for a single meeting.

    Returns True if a report was generated, False if skipped or failed.
    """
    # Skip if already has a report
    if meeting.report_html:
        return False

    # Gather briefs with non-empty summaries
    briefs = SittingBrief.objects.filter(
        sitting__meeting=meeting,
    ).exclude(
        summary_html="",
    ).select_related("sitting").order_by("sitting__sitting_date")

    if not briefs.exists():
        return False

    # Build the brief text block
    brief_texts = []
    for brief in briefs:
        brief_texts.append(
            f"### {brief.sitting.sitting_date}\n{brief.summary_html}"
        )
    briefs_block = "\n\n".join(brief_texts)

    prompt = REPORT_PROMPT.format(
        meeting_name=meeting.name,
        start_date=meeting.start_date.isoformat(),
        end_date=meeting.end_date.isoformat(),
        sitting_count=briefs.count(),
        briefs=briefs_block,
    )

    result = _call_gemini(prompt)
    if result is None:
        return False

    meeting.report_html = result.get("report_html", "")
    meeting.executive_summary = result.get("executive_summary", "")
    meeting.social_post_text = result.get("social_post_text", "")[:280]
    meeting.save(update_fields=[
        "report_html", "executive_summary", "social_post_text", "updated_at",
    ])

    logger.info("Generated report for meeting: %s", meeting.name)
    return True


def generate_all_pending_reports() -> dict:
    """Generate reports for all past meetings that lack one.

    Returns dict with key 'generated' (count of reports created).
    """
    today = datetime.date.today()
    pending = ParliamentaryMeeting.objects.filter(
        end_date__lt=today,
        report_html="",
    )

    generated = 0
    for meeting in pending:
        if generate_meeting_report(meeting):
            generated += 1

    return {"generated": generated}
