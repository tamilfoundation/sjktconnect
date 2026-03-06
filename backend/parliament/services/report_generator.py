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
in the Malaysian parliament for stakeholders - parents, teachers, NGOs, \
community leaders.

Meeting: {meeting_name} ({start_date} to {end_date}).
{sitting_count} sitting(s) had Tamil school mentions. Summary of each below.

Write a meeting report. STRICT word limits:
- 1-2 sittings: 300-500 words
- 3-5 sittings: 500-800 words
- 6+ sittings: 800-1,000 words max
Do NOT exceed the upper limit. Cut ruthlessly.

Sections (use <h2> tags):
1. Key Findings - 3-5 bullet points, most important takeaways
2. MP Scorecard - table of MPs who spoke, party, what they pushed for (use <table>)
3. Policy Signals - commitments, allocations, or policy shifts (skip if none)
4. What to Watch - 2-3 issues for community attention

Rules:
- Synthesise and connect, do not summarise each sitting separately
- Every sentence must add information. No filler, no preamble
- British English. Valid HTML (<h2>, <p>, <ul>, <li>, <table>). No markdown.
- Be specific: amounts, school names, MP names, constituency

Also provide:
- executive_summary: 2-3 sentences, max 300 characters, plain text
- social_post_text: max 280 characters

Return as JSON: {{"report_html": "...", "executive_summary": "...", "social_post_text": "..."}}

--- SITTING BULLET POINTS ---
{briefs}
--- END ---
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
                max_output_tokens=2048,
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

    # Build condensed bullet points from briefs (not full HTML)
    import re
    brief_texts = []
    for brief in briefs:
        # Strip HTML tags to get plain text, then take first 500 chars
        plain = re.sub(r'<[^>]+>', ' ', brief.summary_html or '')
        plain = re.sub(r'\s+', ' ', plain).strip()
        if len(plain) > 500:
            plain = plain[:500] + "..."
        brief_texts.append(
            f"### {brief.sitting.sitting_date}\n{plain}"
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
