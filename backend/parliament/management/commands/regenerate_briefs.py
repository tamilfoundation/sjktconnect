"""Regenerate sitting briefs as comprehensive Gemini-written reports.

Instead of concatenating individual mention summaries, this sends ALL
mention contexts from a sitting to Gemini in one call and asks for a
proper narrative report.
"""

import json
import logging
import os
import re
import time

import markdown
from django.core.management.base import BaseCommand

from google import genai
from google.genai import types

from hansard.models import HansardMention, HansardSitting
from parliament.models import SittingBrief

logger = logging.getLogger(__name__)

BRIEF_PROMPT = """\
You are a parliamentary reporter writing a brief about Tamil school (SJK(T))
mentions in the Malaysian Parliament on {date}.

{mention_count} mention(s) found. Length guide:
- 1 mention: 150-250 words
- 2-3 mentions: 300-450 words
- 4+ mentions: 500-700 words (minimum 300 even if mentions overlap)

Return valid JSON with this structure:
{{
  "headline": "Short descriptive headline (max 12 words). NOT 'X Tamil School
    Mentions in Parliament'. Describe what happened, e.g. 'Dilapidated
    Infrastructure Undermines High-Performing Tamil School in Segamat'.",
  "blurb": "Two-sentence summary, max 30 words total. What happened and why
    it matters. This is the first thing readers see.",
  "body_md": "The full brief as markdown (see structure below). Start with
    the blurb as a lead paragraph before the first ### heading.",
  "social": "One clean sentence for social media, max 200 characters.
    No bullet points, no markdown."
}}

Structure for body_md:

For each distinct topic (group overlapping mentions into one):

### [Short topic heading]

**[MP Name, Constituency]** — One short paragraph reporting what the MP said
or raised. Do NOT repeat the MP name in the paragraph text (it is already in
the bold label). Be specific: amounts, school names, actions. Keep it factual —
report what happened, do not analyse or editorially assess. Short sentences.
Simple language. White space between ideas.

If there was a debate or ministerial response, report that too as a separate
short paragraph.

> Verbatim Malay quote from the Hansard. Not translated. Not truncated.
> Do NOT wrap the quote in double-quotes — the blockquote prefix is sufficient.

End the entire brief with one sentence on what this means practically for
Tamil schools.

Rules:
- Do NOT include party names — constituency is sufficient.
- Do NOT add editorial assessment like "This was substantive advocacy..."
- Do NOT translate Malay quotes — readers are fluent in Malay.
- Do NOT use preamble like "The parliamentary sitting on X featured..."
- Report, do not analyse. What was said, by whom, in what context.
- Short paragraphs (2-3 sentences max). Make it inviting to read.
- Write "SJK(T)" on its own, never inside extra brackets. Wrong: "(SJK(T))".
  If you need a parenthetical abbreviation, write "Tamil schools (SJKT)".

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

            prompt = BRIEF_PROMPT.format(
                date=date_str,
                excerpts=all_excerpts,
                mention_count=len(mentions),
            )

            self.stdout.write(
                f"  {sitting.sitting_date}: generating report "
                f"({len(mentions)} mentions, {len(all_excerpts)} chars)..."
            )

            try:
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.3,
                        max_output_tokens=4096,
                        thinking_config=types.ThinkingConfig(
                            thinking_budget=1024,
                        ),
                    ),
                )
                raw = response.text.strip()
                try:
                    data = json.loads(raw)
                except json.JSONDecodeError:
                    # Retry once without JSON mode if Gemini broke JSON
                    self.stdout.write("  JSON parse failed, retrying...")
                    time.sleep(2)
                    response = client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            temperature=0.2,
                            max_output_tokens=4096,
                            thinking_config=types.ThinkingConfig(
                                thinking_budget=1024,
                            ),
                        ),
                    )
                    data = json.loads(response.text.strip())
            except Exception as e:
                if "429" in str(e):
                    self.stdout.write("  Rate limited, waiting 30s...")
                    time.sleep(30)
                    continue
                logger.exception("Gemini call failed for sitting %s", sitting.sitting_date)
                time.sleep(2)
                continue

            headline = data.get("headline", "").strip()
            blurb = data.get("blurb", "").strip()
            body_md = data.get("body_md", "").strip()
            social = data.get("social", "").strip()[:280]

            # Post-process: fix "(SJK(T))" → "SJK(T)"
            _fix = lambda s: re.sub(r"\(SJK\(T\)\)", "SJK(T)", s)
            headline, blurb, body_md, social = _fix(headline), _fix(blurb), _fix(body_md), _fix(social)

            # Convert body markdown to HTML
            report_html = markdown.markdown(
                body_md,
                extensions=["tables"],
            )

            # Linkify school names
            from parliament.management.commands.generate_meeting_reports import (
                _linkify_schools,
            )
            report_html = _linkify_schools(report_html)

            # Use headline as title, with date suffix
            title = f"{headline} — {date_str}" if headline else (
                f"Tamil School Mention in Parliament — {date_str}"
                if len(mentions) == 1
                else f"{len(mentions)} Tamil School Mentions in Parliament — {date_str}"
            )

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
