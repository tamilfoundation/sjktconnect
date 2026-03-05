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
You are a senior policy analyst writing an executive-grade parliamentary meeting
report about Tamil school (SJK(T)) discussions in the Malaysian Parliament.

Below are the sitting summaries from {meeting_name} ({start_date} to {end_date}).
This meeting had {sitting_count} sittings with Tamil school mentions and
{total_mentions} individual mentions across those sittings.

Produce a comprehensive meeting report in English (1500-2500 words) following
this 7-point framework:

## 1. Executive Summary
Sittings count, total mentions, overall tone, and the big takeaways from this
meeting period. 2-3 paragraphs.

## 2. Key Policy Developments
Concrete commitments, budget allocations, policy changes, or ministerial
statements affecting Tamil schools. Be specific with numbers and details.

## 3. Most Active MPs
A table of MPs who spoke about Tamil schools, with columns:
| MP Name | Constituency | Party | Mentions | Assessment |

The Assessment column should be one line: was their advocacy substantive,
routine, or performative?

## 4. Issue Tracker
Group all discussions by policy theme. Standard buckets include:
- **Funding & Allocations** (maintenance, development, per-capita grants)
- **Infrastructure** (buildings, facilities, land)
- **Teacher Supply** (vacancies, transfers, Tamil-qualified teachers)
- **Enrolment & Access** (declining numbers, transport, catchment)
- **Special Education** (OKU provisions, inclusion)
- **Curriculum & Quality** (standards, UPSR/PT3 results, co-curriculum)
- **Other** (anything that doesn't fit above)

For each theme, summarise what was raised and by whom.

## 5. Government Response Assessment
Did ministers engage substantively or deflect? Were questions answered? Were
commitments made? Rate the overall government responsiveness.

## 6. Comparison with Previous Meeting
{previous_context}

## 7. Implications & Recommendations
What should school leaders, PTA committees, and community stakeholders watch
for? What actions can they take based on this meeting's outcomes?

Writing style:
- Factual, analytical, authoritative — like The Economist or a policy think-tank
- Engaging — the audience is Tamil school parents, board members, and community leaders
- Prioritise "substantive advocacy" over routine or procedural references
- Use specific names, numbers, and dates wherever available
- Tables should use markdown format

Return the report as plain text with markdown headings (##, ###) and tables.
Do NOT wrap in code fences.

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
                extensions=["tables", "smarty"],
            )

            # Extract executive summary (first section up to ## 2)
            exec_summary = ""
            lines = report_md.split("\n")
            in_exec = False
            exec_lines = []
            for line in lines:
                if line.startswith("## 1."):
                    in_exec = True
                    continue
                if line.startswith("## 2."):
                    break
                if in_exec:
                    exec_lines.append(line)
            if exec_lines:
                exec_md = "\n".join(exec_lines).strip()
                exec_summary = markdown.markdown(exec_md, extensions=["smarty"])

            # Build social post
            social = (
                f"{meeting.short_name}: {len(briefs)} sittings, "
                f"{total_mentions} Tamil school mentions in Parliament."
            )
            if len(social) < 250:
                # Add first sentence of executive summary
                plain = exec_md.split(".")[0] if exec_lines else ""
                if plain and len(social) + len(plain) + 2 <= 280:
                    social += " " + plain + "."

            meeting.report_html = report_html
            meeting.executive_summary = exec_summary
            meeting.social_post_text = social[:280]
            meeting.save(update_fields=[
                "report_html", "executive_summary", "social_post_text",
                "updated_at",
            ])

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
