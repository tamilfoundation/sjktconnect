"""Parliament Watch digest generator — action-oriented email content via Gemini.

Takes a ParliamentaryMeeting with a completed report and generates
structured, action-oriented content suitable for email broadcasts.

Returns a dict with: headlines, developments (each with actions for
school_boards/parents/ngos/community), scorecard_summary, one_thing.

Uses the google.genai SDK (same pattern as parliament/services/report_generator.py).
"""

import json
import logging
import os

from google import genai
from google.genai import types

from parliament.models import MPScorecard

logger = logging.getLogger(__name__)

REQUIRED_KEYS = {"headlines", "developments", "scorecard_summary", "one_thing"}

DIGEST_PROMPT = """\
You are writing an action-oriented email digest about Tamil schools (SJK(T)) \
in the Malaysian parliament for Tamil school stakeholders — parents, school \
board members, NGOs, and community leaders.

Below is the executive report from {meeting_name} \
({start_date} to {end_date}).

{scorecard_context}

Transform this report into an ACTION-ORIENTED digest. Every section must \
tell readers what they can DO, not just what happened.

Return a JSON object with these keys:

1. "headlines" (string): 2-3 sentence overview of the most important \
developments. Written as if briefing a busy parent — clear, direct, no jargon.

2. "developments" (array of objects): Each development has:
   - "topic" (string): Short topic label (e.g. "School Funding", "Teacher Shortage")
   - "summary" (string): 2-3 sentences explaining what happened in parliament
   - "actions" (object with 4 keys):
     - "school_boards": What school board members should do (1 sentence)
     - "parents": What parents should do (1 sentence)
     - "ngos": What NGOs/advocacy groups should do (1 sentence)
     - "community": What anyone in the community can do (1 sentence)

   Include 2-5 developments, covering only topics with clear actions.

3. "scorecard_summary" (string): 1-2 sentences summarising MP engagement. \
Name specific MPs who were active and what they did.

4. "one_thing" (string): The single most impactful action any reader can \
take right now. Be specific — name who to contact, what to say, or where to go.

Rules:
- Be specific: use names, amounts, dates, constituency names.
- Actions must be concrete and achievable by ordinary people.
- Write in British English.
- Do not pad or use filler phrases.
- Return ONLY valid JSON, no markdown fences, no extra text.

--- MEETING REPORT ---
{report_html}
--- END REPORT ---

--- EXECUTIVE SUMMARY ---
{executive_summary}
--- END SUMMARY ---
"""


def generate_parliament_digest(meeting) -> dict | None:
    """Generate action-oriented email content for a ParliamentaryMeeting.

    Args:
        meeting: ParliamentaryMeeting instance with report_html populated.

    Returns:
        dict with headlines, developments, scorecard_summary, one_thing.
        None if meeting has no report, API key missing, or generation fails.
    """
    if not meeting.report_html:
        return None

    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        logger.warning("GEMINI_API_KEY not set — skipping digest generation")
        return None

    # Gather top MP scorecards for context
    top_scorecards = MPScorecard.objects.order_by("-total_mentions")[:10]
    if top_scorecards:
        scorecard_lines = []
        for sc in top_scorecards:
            scorecard_lines.append(
                f"- {sc.mp_name} ({sc.constituency or 'Unknown'}): "
                f"{sc.total_mentions} mentions, "
                f"{sc.substantive_mentions} substantive"
            )
        scorecard_context = (
            "Top MP engagement scores:\n" + "\n".join(scorecard_lines)
        )
    else:
        scorecard_context = "No MP scorecard data available."

    prompt = DIGEST_PROMPT.format(
        meeting_name=meeting.name,
        start_date=str(meeting.start_date),
        end_date=str(meeting.end_date),
        report_html=meeting.report_html,
        executive_summary=meeting.executive_summary,
        scorecard_context=scorecard_context,
    )

    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.3,
            ),
        )
        raw_text = response.text.strip()
    except Exception:
        logger.exception("Gemini API call failed for parliament digest")
        return None

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError:
        logger.error(
            "Gemini returned invalid JSON for parliament digest: %s",
            raw_text[:200],
        )
        return None

    # Validate required keys
    if not REQUIRED_KEYS.issubset(data.keys()):
        missing = REQUIRED_KEYS - data.keys()
        logger.error("Parliament digest missing required keys: %s", missing)
        return None

    return data
