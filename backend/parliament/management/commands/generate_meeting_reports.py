"""Generate executive-grade meeting reports from sitting summaries.

For each ParliamentaryMeeting, aggregates all sitting briefs and sends
them to Gemini to produce a 7-point policy briefing suitable for school
boards, PTA leaders, and community stakeholders.
"""

import html
import logging
import os
import re
import time

import markdown
from django.core.management.base import BaseCommand

from google import genai
from google.genai import types

from parliament.models import ParliamentaryMeeting, SittingBrief

logger = logging.getLogger(__name__)


def html_to_plain(text: str) -> str:
    """Strip HTML tags and decode entities to plain text."""
    text = html.unescape(text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


MEETING_REPORT_PROMPT = """\
You are a parliamentary reporter writing a meeting report about Tamil school
(SJK(T)) discussions in the Malaysian Parliament.

Meeting: {meeting_name} ({start_date} to {end_date}).
{sitting_count} sittings had Tamil school mentions, {total_mentions} total mentions.

Word guide based on sittings:
- 1-3 sittings: 400-600 words
- 4-7 sittings: 600-900 words
- 8+ sittings: 900-1,200 words (minimum 900)

Structure (use ## headings):

## Key Findings
3-5 bullet points. The most important takeaways, with specific amounts,
names, and dates. Lead with the biggest news. Report facts, not opinions.

## MP Scorecard
Markdown table: | MP Name | Constituency | Topic | Assessment |
- Do NOT include a Party column — constituency is sufficient.
- Topic: max 8 words (e.g. "School funding allocation").
- Assessment: one word — Substantive / Routine / Performative.
- One row per MP. If an MP raised multiple topics, combine into one row.

## Policy Signals
Budget commitments, policy shifts, or ministerial promises. Report what
was said, not what it might mean. Skip this section if nothing concrete.

## What to Watch
2-3 bullet points for community stakeholders. Be specific and actionable.

{previous_context}

Style rules:
- Report, do not analyse. What was said, by whom, in what context.
- No editorial assessment ("This was substantive advocacy...").
- Short paragraphs. Simple, clear language. British English.
- No filler, no preamble. Lead with substance.
- Write "SJK(T)" on its own, never inside extra brackets. Wrong: "(SJK(T))".
  If you need a parenthetical abbreviation, write "Tamil schools (SJKT)".

Return as plain text with markdown headings and tables. No code fences.

--- SITTING SUMMARIES ---
{summaries}
--- END SUMMARIES ---
"""

PREVIOUS_CONTEXT_WITH_REPORT = """\
The previous meeting was {prev_name}. Here is its report for delta analysis:

{prev_report}

Identify recurring issues, progress on prior concerns, and any new topics
that emerged in this meeting."""

PREVIOUS_CONTEXT_NO_REPORT = """\
This is the first meeting being analysed, so no previous meeting report is
available. Note this and focus on establishing baseline themes and patterns."""

ILLUSTRATION_PROMPT = """\
A single-panel editorial cartoon in the style of The Economist or The New Yorker.
Black ink line drawing with minimal colour wash.

Scene inspired by these parliamentary findings about Tamil schools in Malaysia:
{findings}

Requirements:
- Clean line art, crosshatching for shadows, slightly satirical, understated
- The Malaysian Parliament dome should be visible in the background
- A Tamil school building with "SJK(T)" on it should be central
- Include people (MPs, parents, teachers) relevant to the themes
- No speech bubbles. No caption text. Let the image speak.
- No text in the image except "SJK(T)" on the school building
"""


def _generate_illustration(client, key_findings: str) -> bytes | None:
    """Generate an editorial cartoon based on the Key Findings."""
    prompt = ILLUSTRATION_PROMPT.format(findings=key_findings[:500])
    try:
        response = client.models.generate_images(
            model="imagen-4.0-generate-001",
            prompt=prompt,
            config=types.GenerateImagesConfig(
                number_of_images=1,
                output_mime_type="image/png",
            ),
        )
        if response.generated_images:
            return response.generated_images[0].image.image_bytes
    except Exception:
        logger.exception("Illustration generation failed")
    return None


class Command(BaseCommand):
    help = "Generate executive-grade meeting reports from sitting summaries."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be processed without calling API.",
        )
        parser.add_argument(
            "--meeting",
            type=str,
            default="",
            help='Process only one meeting by short_name (e.g. "1st Meeting 2025").',
        )
        parser.add_argument(
            "--all",
            action="store_true",
            help="Process all meetings (default: only those without reports).",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        meeting_filter = options["meeting"]
        process_all = options["all"]

        api_key = os.environ.get("GEMINI_API_KEY", "").split("#")[0].strip()
        if not api_key and not dry_run:
            self.stderr.write(self.style.ERROR("GEMINI_API_KEY not set."))
            return

        # Build queryset
        qs = ParliamentaryMeeting.objects.order_by("start_date")
        if meeting_filter:
            qs = qs.filter(short_name=meeting_filter)
        elif not process_all:
            qs = qs.filter(report_html="")

        meetings = list(qs)
        self.stdout.write(f"Found {len(meetings)} meetings to process.")

        if dry_run:
            for m in meetings:
                sitting_count = m.sittings.filter(mention_count__gt=0).count()
                brief_count = SittingBrief.objects.filter(
                    sitting__meeting=m,
                ).exclude(summary_html="").count()
                self.stdout.write(
                    f"  {m.short_name}: {sitting_count} sittings with mentions, "
                    f"{brief_count} briefs available"
                )
            return

        client = genai.Client(api_key=api_key)
        generated = 0
        prev_report_text = ""
        prev_name = ""

        for meeting in meetings:
            # Collect sitting briefs
            briefs = list(
                SittingBrief.objects.filter(
                    sitting__meeting=meeting,
                )
                .exclude(summary_html="")
                .select_related("sitting")
                .order_by("sitting__sitting_date")
            )

            if not briefs:
                self.stdout.write(
                    f"  {meeting.short_name}: no sitting briefs, skipping"
                )
                # Still track for previous context
                prev_name = meeting.short_name
                prev_report_text = ""
                continue

            # Build aggregated input
            summaries_parts = []
            total_mentions = 0
            for brief in briefs:
                date_str = brief.sitting.sitting_date.strftime("%d %B %Y")
                mention_count = brief.sitting.mention_count
                total_mentions += mention_count
                plain_text = html_to_plain(brief.summary_html)
                summaries_parts.append(
                    f"--- Sitting: {date_str} ({mention_count} mentions) ---\n"
                    f"{plain_text}"
                )

            all_summaries = "\n\n".join(summaries_parts)

            # Truncate if too long (keep it under ~30K chars)
            if len(all_summaries) > 30000:
                all_summaries = all_summaries[:30000] + "\n\n[... truncated]"

            # Build previous context
            if prev_report_text:
                previous_context = PREVIOUS_CONTEXT_WITH_REPORT.format(
                    prev_name=prev_name,
                    prev_report=prev_report_text[:5000],
                )
            else:
                previous_context = PREVIOUS_CONTEXT_NO_REPORT

            start_str = meeting.start_date.strftime("%d %B %Y")
            end_str = meeting.end_date.strftime("%d %B %Y")

            prompt = MEETING_REPORT_PROMPT.format(
                meeting_name=meeting.name,
                start_date=start_str,
                end_date=end_str,
                sitting_count=len(briefs),
                total_mentions=total_mentions,
                previous_context=previous_context,
                summaries=all_summaries,
            )

            self.stdout.write(
                f"  {meeting.short_name}: generating report "
                f"({len(briefs)} briefs, {len(all_summaries)} chars)..."
            )

            try:
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.4,
                        max_output_tokens=8192,
                        thinking_config=types.ThinkingConfig(
                            thinking_budget=1024,
                        ),
                    ),
                )
                report_md = response.text.strip()
            except Exception as e:
                if "429" in str(e):
                    self.stdout.write("  Rate limited, waiting 30s...")
                    time.sleep(30)
                    continue
                logger.exception(
                    "Gemini call failed for meeting %s", meeting.short_name
                )
                time.sleep(2)
                continue

            # Convert to HTML
            report_html = markdown.markdown(
                report_md,
                extensions=["tables"],
            )

            # Extract executive summary as plain text from Key Findings
            exec_summary = ""
            lines = report_md.split("\n")
            in_exec = False
            exec_lines = []
            for line in lines:
                if line.startswith("## Key Findings"):
                    in_exec = True
                    continue
                if in_exec and line.startswith("## "):
                    break
                if in_exec:
                    # Strip bullet markers and bold for plain text
                    clean = line.strip().lstrip("*-").strip()
                    clean = re.sub(r"\*\*(.+?)\*\*", r"\1", clean)
                    if clean:
                        exec_lines.append(clean)
            if exec_lines:
                # Take first 2-3 findings as plain text summary
                exec_summary = " ".join(exec_lines[:3])
                if len(exec_summary) > 500:
                    exec_summary = exec_summary[:497] + "..."

            # Build social post from first finding
            social = (
                f"{meeting.short_name}: {len(briefs)} sittings, "
                f"{total_mentions} Tamil school mentions in Parliament."
            )
            if exec_lines and len(social) < 250:
                first = exec_lines[0].split(".")[0]
                if first and len(social) + len(first) + 2 <= 280:
                    social += " " + first + "."

            meeting.report_html = report_html
            meeting.executive_summary = exec_summary
            meeting.social_post_text = social[:280]

            # Generate editorial cartoon illustration
            findings_text = " ".join(exec_lines) if exec_lines else ""
            if findings_text:
                self.stdout.write(
                    f"  Generating illustration for {meeting.short_name}..."
                )
                img_bytes = _generate_illustration(client, findings_text)
                if img_bytes:
                    meeting.illustration = img_bytes
                    self.stdout.write(
                        f"  Illustration: {len(img_bytes)} bytes"
                    )

            update_fields = [
                "report_html", "executive_summary", "social_post_text",
                "updated_at",
            ]
            if meeting.illustration:
                update_fields.append("illustration")
            meeting.save(update_fields=update_fields)

            self.stdout.write(
                self.style.SUCCESS(
                    f"  Generated report for {meeting.short_name} "
                    f"({len(report_html)} chars HTML)"
                )
            )
            generated += 1

            # Track for next meeting's comparison
            prev_name = meeting.short_name
            prev_report_text = report_md

            time.sleep(2)

            from django.db import connection
            connection.close()

        self.stdout.write(
            self.style.SUCCESS(f"\nGenerated {generated} meeting reports.")
        )
