"""Sitting brief generator.

Creates a markdown summary of all approved mentions from a single
Hansard sitting, renders it to HTML, and generates a social media
post (<= 280 chars).
"""

import logging
from datetime import date

import markdown

from hansard.models import HansardMention, HansardSitting
from parliament.models import SittingBrief

logger = logging.getLogger(__name__)


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

    md_text = _build_markdown(sitting, mentions)
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


def _build_markdown(sitting, mentions):
    """Build a markdown summary from mentions."""
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
