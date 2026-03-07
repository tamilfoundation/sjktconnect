"""Corrector service — applies targeted fixes to reports and briefs.

Four correction pathways:
1. Re-prompt Gemini (content issues — generic headlines, vague advice)
2. Code fix (mechanical — bracket regex, entity decode, table clamp)
3. School name repair (data — comma removal, fuzzy match)
4. Illustration regeneration (visual — more specific scene direction)
"""

import logging
import os
import re

from google import genai
from google.genai import types

from parliament.services.evaluator import EvaluationResult

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 3
MODEL = "gemini-2.5-flash"

CORRECTION_PROMPT = """\
You previously generated this report:

{draft}

An independent evaluator identified these issues:
{feedback}

Source material (ground truth):
{source_briefs}

Fix ONLY the flagged issues. Preserve all sections and content that passed
evaluation. Do not introduce new information not present in the source material.

Return the corrected report as plain text with markdown headings and tables.
No code fences.
"""


def apply_code_fixes(html: str) -> str:
    """Apply deterministic code-level fixes. No AI call needed."""
    # Fix "(SJK(T))" -> "SJK(T)"
    html = re.sub(r"\(SJK\(T\)\)", "SJK(T)", html)
    return html


def correct_report(
    current_draft: str,
    eval_result: EvaluationResult,
    source_briefs: str,
) -> str | None:
    """Re-prompt Gemini with targeted feedback to fix content issues.

    Returns corrected markdown text, or None if API unavailable.
    """
    api_key = os.environ.get("GEMINI_API_KEY", "").split("#")[0].strip()
    if not api_key:
        logger.warning("GEMINI_API_KEY not set — cannot correct report")
        return None

    # Build feedback from failed criteria
    feedback_lines = []
    for criterion, data in eval_result.tier2_scores.items():
        score = data.get("score", 10)
        fb = data.get("feedback")
        if score < 6 and fb:
            feedback_lines.append(f"- {criterion} (score {score}/10): {fb}")

    for criterion, data in eval_result.tier1_results.items():
        if not data.get("pass", True):
            details = data.get("details", "No details")
            feedback_lines.append(f"- RED LINE {criterion}: {details}")

    if not feedback_lines:
        return None

    feedback = "\n".join(feedback_lines)

    prompt = CORRECTION_PROMPT.format(
        draft=current_draft[:15000],
        feedback=feedback,
        source_briefs=source_briefs[:15000],
    )

    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.3,
                max_output_tokens=8192,
                thinking_config=types.ThinkingConfig(
                    thinking_budget=1024,
                ),
            ),
        )
        return response.text.strip()
    except Exception:
        logger.exception("Corrector API call failed")
        return None


def correct_brief(
    current_html: str,
    eval_result: EvaluationResult,
    source_summaries: str,
) -> str | None:
    """Re-prompt Gemini with targeted feedback to fix brief content issues."""
    return correct_report(current_html, eval_result, source_summaries)
