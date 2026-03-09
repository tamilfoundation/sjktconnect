"""Sitting brief generator.

Creates a prose summary of all approved mentions from a single
Hansard sitting using Gemini, renders it to HTML, and generates a
social media post (<= 280 chars).
"""

import json
import logging
import os
import time
from datetime import date

import markdown
from google import genai
from google.genai import types

from hansard.models import HansardMention, HansardSitting
from parliament.models import SittingBrief
from parliament.services.evaluator import evaluate_brief as _evaluate_brief
from parliament.services.pipeline_registry import get_pipeline_version
from parliament.services.corrector import apply_code_fixes, correct_brief

logger = logging.getLogger(__name__)


BRIEF_PROMPT = """\
You are a parliamentary reporter writing a concise sitting brief about SJK(T) \
mentions in the Malaysian Parliament.

Sitting date: {date}
Number of mentions: {mention_count}

{domain_context}

If there is only 1 mention, write a single tight section (no Executive Summary / \
Details split). For 2+ mentions, use the structure below.

## Executive Summary
2-3 sentences summarising what happened in this sitting. \
Lead with the most important development. Use past tense throughout.

## Details
For each mention, report: who spoke, what they said, and any context or response. \
Use past tense. Be specific — include amounts, school names, and actions. \
One paragraph per mention. Do NOT repeat what the Executive Summary already said.

## Verbatim Quotes
Include 1-3 direct quotes from the Hansard excerpt that are most significant. \
Format as blockquotes with attribution. Only include quotes that add value \
beyond the summary. If no quotes are significant, skip this section.

Data rules:
- The Speaker field in the mention data is the VERIFIED MP name. Use it as-is. \
Do not add "Unidentified MP" or any other prefix.
- Attribution format: "MP Name (Constituency)" — e.g. "Tuan X (Jelutong)".

Style rules:
- Past tense throughout (the sitting has already occurred)
- British English
- No editorial commentary
- CRITICAL — acronym rule: Use EITHER the full name OR the abbreviation, never \
both together. Wrong: "Sekolah Jenis Kebangsaan (Tamil) SJK(T)". \
Right: "SJK(T)" or "Tamil schools". This applies to ALL acronyms — KPM, PPKI, \
SJK(C), SK, JPN, etc. Pick the short form and use it throughout. Only expand \
once at first use if the reader may not know it.
- NEVER write "(SJK(T))" with outer brackets. Write "SJK(T)" on its own.
- No preamble, padding, or filler. Substance only.

Return as plain markdown. No code fences.

--- MENTION DATA ---
{mentions_data}
--- END DATA ---
"""


def _format_date(d, fmt_long=True):
    """Format a date object cross-platform (no leading zero on day).

    Args:
        d: date or str (YYYY-MM-DD). Handles SQLite returning strings.
        fmt_long: True for "26 January 2026", False for "26 Jan 2026".
    """
    if isinstance(d, str):
        d = date.fromisoformat(d)
    month_fmt = "%B" if fmt_long else "%b"
    return f"{d.day} {d.strftime(month_fmt)} {d.year}"


def generate_all_pending_briefs() -> dict:
    """Generate briefs for all sittings that have analysed mentions but no brief.

    Returns dict with count: generated.
    """
    sittings = (
        HansardSitting.objects.filter(
            status="COMPLETED",
            mentions__ai_summary__gt="",
        )
        .exclude(brief__isnull=False)
        .distinct()
    )

    generated = 0
    for sitting in sittings:
        result = generate_brief(sitting)
        if result is not None:
            generated += 1

    logger.info("generate_all_pending_briefs: %d briefs generated", generated)
    return {"generated": generated}


def generate_brief(sitting):
    """Generate a SittingBrief for a HansardSitting.

    Uses approved mentions (review_status=APPROVED) that have been
    analysed (mp_name is set). Falls back to all analysed mentions
    if none are approved yet.

    Args:
        sitting: HansardSitting instance.

    Returns:
        SittingBrief instance (created or updated), or None if no mentions.
    """
    # Prefer approved mentions, fall back to all analysed
    # A mention is "analysed" if it has an AI summary (mp_name may be
    # empty when the speaker couldn't be identified from the quote).
    mentions = sitting.mentions.filter(
        review_status="APPROVED",
    ).exclude(ai_summary="")

    if not mentions.exists():
        mentions = sitting.mentions.exclude(ai_summary="")

    if not mentions.exists():
        logger.warning(
            "No analysed mentions for sitting %s, skipping brief",
            sitting.sitting_date,
        )
        return None

    md_text = _generate_brief_prose(sitting, mentions)
    html = markdown.markdown(md_text, extensions=["tables"])
    social_text = _build_social_post(sitting, mentions)
    title = _build_title(sitting, mentions)

    brief, _ = SittingBrief.objects.update_or_create(
        sitting=sitting,
        defaults={
            "title": title,
            "summary_html": html,
            "social_post_text": social_text,
        },
    )

    # Quality evaluation loop
    _run_brief_quality_loop(brief, mentions)

    logger.info(
        "Brief generated for sitting %s: %s mentions",
        sitting.sitting_date, mentions.count(),
    )
    return brief


def _build_title(sitting, mentions):
    """Build a brief title."""
    count = mentions.count()
    date_str = _format_date(sitting.sitting_date)
    if count == 1:
        return f"Tamil School Mention in Parliament — {date_str}"
    return f"{count} Tamil School Mentions in Parliament — {date_str}"


def _generate_brief_prose(sitting, mentions):
    """Generate a prose brief via Gemini, with fallback to template."""
    from parliament.services.context_builder import build_context, format_context_for_prompt

    # Build mention data for the prompt
    mentions_data = _build_mentions_data(mentions)
    date_str = _format_date(sitting.sitting_date)

    # Domain context
    try:
        ctx = build_context()
        domain_context = format_context_for_prompt(ctx)
    except Exception:
        logger.warning("Could not load domain context for brief")
        domain_context = ""

    # Try Gemini
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        logger.info("No GEMINI_API_KEY, using template fallback for brief")
        return _build_markdown_fallback(sitting, mentions)

    prompt = BRIEF_PROMPT.format(
        date=date_str,
        mention_count=mentions.count(),
        domain_context=domain_context,
        mentions_data=mentions_data,
    )

    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.3,
                max_output_tokens=2048,
            ),
        )
        md_text = response.text.strip()
        # Post-process: fix "(SJK(T))" → "SJK(T)"
        import re
        md_text = re.sub(r"\(SJK\(T\)\)", "SJK(T)", md_text)
        return md_text
    except Exception:
        logger.exception("Gemini brief generation failed, using fallback")
        return _build_markdown_fallback(sitting, mentions)


def _build_mentions_data(mentions):
    """Format mentions as structured text for the brief prompt."""
    parts = []
    for i, mention in enumerate(mentions.order_by("page_number"), 1):
        mp = mention.mp_name or "Unknown MP"
        constituency = mention.mp_constituency or ""
        party = mention.mp_party or ""
        lines = [
            f"Mention {i}:",
            f"  Speaker: {mp}",
        ]
        if constituency:
            lines.append(f"  Constituency: {constituency}")
        if party:
            lines.append(f"  Party: {party}")
        lines.append(f"  Type: {mention.mention_type or 'OTHER'}")
        lines.append(f"  Significance: {mention.significance or 1}/5")
        lines.append(f"  Sentiment: {mention.sentiment or 'NEUTRAL'}")
        if mention.ai_summary:
            lines.append(f"  Summary: {mention.ai_summary}")
        if mention.verbatim_quote:
            quote = mention.verbatim_quote[:500]
            lines.append(f"  Hansard excerpt: {quote}")
        if mention.page_number:
            lines.append(f"  Page: {mention.page_number}")
        parts.append("\n".join(lines))
    return "\n\n".join(parts)


def _build_markdown_fallback(sitting, mentions):
    """Build a template-based markdown summary (fallback when Gemini unavailable)."""
    date_str = _format_date(sitting.sitting_date)
    lines = [
        f"# Parliament Watch: {date_str}",
        "",
        f"**{mentions.count()}** mention(s) of Tamil schools found in the "
        f"Hansard for {date_str}.",
        "",
    ]

    for i, mention in enumerate(mentions.order_by("page_number"), 1):
        mp = mention.mp_name or "Unknown MP"
        constituency = mention.mp_constituency or ""
        party = mention.mp_party or ""

        mp_line = mp
        if constituency:
            mp_line += f" ({constituency}"
            if party:
                mp_line += f", {party}"
            mp_line += ")"
        elif party:
            mp_line += f" ({party})"

        mention_type = mention.mention_type or "OTHER"
        significance = mention.significance or 1
        stars = _significance_stars(significance)

        lines.append(f"## {i}. {mp_line}")
        lines.append("")
        lines.append(f"**Type**: {mention_type} | **Significance**: {stars}")
        lines.append("")

        if mention.ai_summary:
            lines.append(mention.ai_summary)
            lines.append("")

        if mention.page_number:
            lines.append(f"*Page {mention.page_number}*")
            lines.append("")

    return "\n".join(lines)


def _significance_stars(level):
    """Convert significance 1-5 to a star display."""
    filled = min(max(level, 1), 5)
    return filled * "*"


def _build_social_post(sitting, mentions):
    """Build a social media post text, max 280 chars.

    Format: "[emoji] N Tamil school mention(s) in Parliament on DD Mon YYYY.
    [Top MP summary]. Full brief: [url placeholder]"
    """
    count = mentions.count()
    date_str = _format_date(sitting.sitting_date, fmt_long=False)

    noun = "mention" if count == 1 else "mentions"
    opening = f"{count} Tamil school {noun} in Parliament on {date_str}."

    # Add top MP info if available
    top_mention = mentions.order_by("-significance").first()
    mp_bit = ""
    if top_mention and top_mention.mp_name:
        mp_bit = f" {top_mention.mp_name}"
        if top_mention.ai_summary:
            summary = top_mention.ai_summary
            # Trim summary to fit
            available = 280 - len(opening) - len(mp_bit) - 5  # padding
            if len(summary) > available:
                summary = summary[:available - 3] + "..."
            mp_bit += f": {summary}"

    post = opening + mp_bit

    # Final truncation safety
    if len(post) > 280:
        post = post[:277] + "..."

    return post


def _run_brief_quality_loop(brief, mentions):
    """Run evaluate/correct loop on a sitting brief using the unified framework."""
    from parliament.models import QualityLog, MP
    from parliament.services.quality_loop import run_quality_loop
    from schools.models import School

    school_names = list(School.objects.values_list("name", flat=True)[:100])
    mp_names = list(MP.objects.values_list("name", flat=True)[:50])
    source_summaries = "\n".join(
        m.ai_summary for m in mentions if m.ai_summary
    )

    # Apply code fixes first
    cleaned_html = apply_code_fixes(brief.summary_html)
    if cleaned_html != brief.summary_html:
        brief.summary_html = cleaned_html
        brief.save(update_fields=["summary_html", "updated_at"])

    def evaluate_fn(html):
        return _evaluate_brief(
            brief_html=html,
            source_summaries=source_summaries,
            school_names=school_names,
            mp_names=mp_names,
        )

    def correct_fn(html, eval_result):
        corrected_md = correct_brief(
            current_html=html,
            eval_result=eval_result,
            source_summaries=source_summaries,
        )
        if corrected_md:
            new_html = markdown.markdown(corrected_md, extensions=["tables"])
            return apply_code_fixes(new_html)
        return None

    def log_fn(attempt, eval_result):
        if eval_result.verdict == "PASS":
            qf = "GREEN"
        elif eval_result.verdict == "REJECT":
            qf = "RED"
        else:
            qf = "AMBER"
        QualityLog.objects.create(
            content_type="brief",
            sitting_brief=brief,
            prompt_version="v1",
            model_used="gemini-2.5-flash",
            attempt_number=attempt,
            verdict=eval_result.verdict,
            tier1_results=eval_result.tier1_results,
            tier2_scores=eval_result.tier2_scores,
            tier3_flags=eval_result.tier3_flags,
            corrections_applied=[],
            quality_flag=qf,
        )

    final_html, quality_flag = run_quality_loop(
        content=brief.summary_html,
        evaluate_fn=evaluate_fn,
        correct_fn=correct_fn,
        max_attempts=3,
        log_entry_fn=log_fn,
    )

    brief.pipeline_version = get_pipeline_version()
    brief.summary_html = final_html
    brief.quality_flag = quality_flag
    brief.is_published = (quality_flag == "GREEN")
    brief.save(update_fields=["summary_html", "quality_flag", "is_published", "pipeline_version", "updated_at"])
