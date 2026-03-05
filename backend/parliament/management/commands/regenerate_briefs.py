"""Regenerate sitting briefs as comprehensive Gemini-written reports.

Instead of concatenating individual mention summaries, this sends ALL
mention contexts from a sitting to Gemini in one call and asks for a
proper narrative report.
"""

import json
import logging
import os
import time

import markdown
from django.core.management.base import BaseCommand

from google import genai
from google.genai import types

from hansard.models import HansardMention, HansardSitting
from parliament.models import SittingBrief

logger = logging.getLogger(__name__)

BRIEF_PROMPT = """\
You are a policy analyst writing a concise but comprehensive sitting report about
Tamil school (SJK(T)) mentions in the Malaysian Parliament.

Below are excerpts from the Hansard of {date}. Each excerpt contains a mention
of Tamil schools by an MP during this parliamentary sitting.

Write a report in English (500-800 words) with this structure:

## Summary
One paragraph overview: how many mentions, what the main topics were, and the
overall tone (supportive, critical, routine).

## Key Discussions

For each distinct topic raised (group related mentions together, do NOT repeat
the same point), write a subsection:

### [Topic Title]
- **Who spoke**: MP name (constituency, party) — if the speaker cannot be
  identified from the text, write "Unidentified MP"
- **What they said**: 2-3 sentences summarising the substance. Be specific —
  include numbers, school names, policy details mentioned.
- **Key quote**: One short, impactful verbatim quote in the original Malay,
  with your English translation in parentheses.
- **Assessment**: Was this substantive advocacy, a routine reference, or a
  deflection? Was the argument well-made? Did the Minister respond?

## Implications for Tamil Schools
2-3 sentences: What does this sitting mean practically for Tamil schools?
Any new commitments, policy shifts, or concerns raised?

Writing style:
- Factual and analytical, like The Economist or ProPublica
- Engaging — assume the reader is a Tamil school parent or community leader
- Group duplicate/overlapping mentions into one discussion (do NOT list the
  same speech point multiple times)
- If an MP's name cannot be identified, say so honestly rather than guessing

Return the report as plain text with markdown headings (##, ###). Do NOT
wrap in code fences.

--- HANSARD EXCERPTS ---
{excerpts}
--- END EXCERPTS ---
"""


class Command(BaseCommand):
    help = "Regenerate sitting briefs as comprehensive Gemini-written reports."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be processed without calling API.",
        )
        parser.add_argument(
            "--sitting-date",
            type=str,
            default="",
            help="Process only one sitting (YYYY-MM-DD).",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        sitting_date = options["sitting_date"]

        api_key = os.environ.get("GEMINI_API_KEY", "")
        if not api_key and not dry_run:
            self.stderr.write(self.style.ERROR("GEMINI_API_KEY not set."))
            return

        # Find sittings with mentions
        qs = HansardSitting.objects.filter(mention_count__gt=0).order_by("-sitting_date")
        if sitting_date:
            qs = qs.filter(sitting_date=sitting_date)

        sittings = list(qs)
        self.stdout.write(f"Found {len(sittings)} sittings with mentions.")

        if dry_run:
            for s in sittings:
                mentions = s.mentions.exclude(ai_summary="").count()
                self.stdout.write(
                    f"  {s.sitting_date}: {mentions} analysed mentions"
                )
            return

        client = genai.Client(api_key=api_key)
        generated = 0

        for sitting in sittings:
            mentions = list(
                sitting.mentions
                .exclude(ai_summary="")
                .exclude(review_status="REJECTED")
                .order_by("page_number")
            )

            if not mentions:
                self.stdout.write(f"  {sitting.sitting_date}: no analysed mentions, skipping")
                continue

            # Build combined excerpts
            excerpts_parts = []
            for i, m in enumerate(mentions, 1):
                parts = []
                mp_label = m.mp_name or "Unidentified MP"
                parts.append(f"--- Mention {i} (Page {m.page_number}, {mp_label}) ---")
                if m.context_before:
                    parts.append(m.context_before.strip())
                parts.append(m.verbatim_quote.strip())
                if m.context_after:
                    parts.append(m.context_after.strip())
                excerpts_parts.append("\n".join(parts))

            all_excerpts = "\n\n".join(excerpts_parts)

            # Truncate if too long (Gemini Flash has 1M token limit, but
            # keep it reasonable — ~15K chars covers most sittings)
            if len(all_excerpts) > 15000:
                all_excerpts = all_excerpts[:15000] + "\n\n[... truncated]"

            try:
                date_str = sitting.sitting_date.strftime("%-d %B %Y")
            except (ValueError, AttributeError):
                date_str = sitting.sitting_date.strftime("%d %B %Y").lstrip("0")

            prompt = BRIEF_PROMPT.format(date=date_str, excerpts=all_excerpts)

            self.stdout.write(
                f"  {sitting.sitting_date}: generating report "
                f"({len(mentions)} mentions, {len(all_excerpts)} chars)..."
            )

            try:
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.4,  # Slightly creative for engaging writing
                    ),
                )
                report_md = response.text.strip()
            except Exception as e:
                if "429" in str(e):
                    self.stdout.write("  Rate limited, waiting 30s...")
                    time.sleep(30)
                    continue
                logger.exception("Gemini call failed for sitting %s", sitting.sitting_date)
                time.sleep(2)
                continue

            # Convert markdown to HTML
            report_html = markdown.markdown(
                report_md,
                extensions=["tables", "smarty"],
            )

            # Build title from first line or generate one
            count = len(mentions)
            title = (
                f"Tamil School Mention in Parliament — {date_str}"
                if count == 1
                else f"{count} Tamil School Mentions in Parliament — {date_str}"
            )

            # Build social post
            # Extract first sentence of summary for social
            first_line = report_md.split("\n")[0].replace("## ", "").replace("# ", "")
            social = f"{count} Tamil school mention{'s' if count > 1 else ''} in Parliament on {date_str}."
            if len(social) + len(first_line) + 2 <= 280:
                social += " " + first_line

            brief, created = SittingBrief.objects.update_or_create(
                sitting=sitting,
                defaults={
                    "title": title,
                    "summary_html": report_html,
                    "social_post_text": social[:280],
                },
            )

            action = "Created" if created else "Updated"
            self.stdout.write(
                self.style.SUCCESS(
                    f"  {action} brief for {sitting.sitting_date} "
                    f"({len(report_html)} chars HTML)"
                )
            )
            generated += 1

            time.sleep(1)

            from django.db import connection
            connection.close()

        self.stdout.write(
            self.style.SUCCESS(f"\nGenerated {generated} sitting reports.")
        )
