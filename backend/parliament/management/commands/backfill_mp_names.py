"""Backfill missing MP names by sending fuller context to Gemini.

The original analysis only sent ~1500 chars. This command sends the full
verbatim quote + all available context to Gemini with a targeted prompt
focused on identifying the speaker.
"""

import json
import logging
import os
import time

from django.core.management.base import BaseCommand

from google import genai
from google.genai import types

from hansard.models import HansardMention

logger = logging.getLogger(__name__)

BACKFILL_PROMPT = """\
You are reading a Malaysian parliamentary Hansard excerpt. Your task is to identify
the MP (Member of Parliament) who is speaking about Tamil schools (SJK(T)).

Malaysian Hansard format: speakers are identified as
"Tuan [Name] [Constituency]: ..." or "Yang Berhormat [Name] ..." or
"Dato' [Name] ..." before their speech. Look for these patterns in the text.

Given this excerpt, return a JSON object:
- mp_name: Full name of the MP speaking (string, or "" if truly unclear)
- mp_constituency: Parliamentary constituency name (e.g. "Klang", "Jelutong") or "" if unclear
- mp_party: Political party (e.g. "DAP", "PKR", "UMNO", "PAS", "BERSATU") or "" if unclear

Common Malaysian MP name patterns:
- "Tuan Ganabatirau a/l Veraman [Klang]" → name: "Ganabatirau a/l Veraman", constituency: "Klang"
- "Dato' Sri Hajah Nancy binti Shukri" → name: "Nancy binti Shukri"
- "Tuan Sanisvara Nethaji Rayer a/l Rajaji [Jelutong]" → name: "Sanisvara Nethaji Rayer a/l Rajaji"

Return ONLY valid JSON, no markdown fences.

--- HANSARD EXCERPT ---
{excerpt}
--- END EXCERPT ---
"""


class Command(BaseCommand):
    help = "Backfill missing MP names using Gemini with fuller context."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be processed without calling API.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=0,
            help="Max mentions to process (0 = all).",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        limit = options["limit"]

        api_key = os.environ.get("GEMINI_API_KEY", "")
        if not api_key and not dry_run:
            self.stderr.write(self.style.ERROR("GEMINI_API_KEY not set."))
            return

        # Find mentions with empty mp_name
        qs = (
            HansardMention.objects
            .filter(mp_name="")
            .exclude(verbatim_quote="")
            .select_related("sitting")
            .order_by("-sitting__sitting_date")
        )

        if limit:
            qs = qs[:limit]

        mentions = list(qs)
        self.stdout.write(f"Found {len(mentions)} mentions with missing MP name.")

        if dry_run:
            for m in mentions:
                excerpt_len = len(m.context_before) + len(m.verbatim_quote) + len(m.context_after)
                self.stdout.write(
                    f"  #{m.id} {m.sitting.sitting_date} p.{m.page_number} "
                    f"({excerpt_len} chars context)"
                )
            return

        client = genai.Client(api_key=api_key)
        updated = 0
        failed = 0

        for m in mentions:
            # Build fuller excerpt — use all available context
            parts = []
            if m.context_before:
                parts.append(m.context_before.strip())
            parts.append(m.verbatim_quote.strip())
            if m.context_after:
                parts.append(m.context_after.strip())
            excerpt = "\n\n".join(parts)

            prompt = BACKFILL_PROMPT.format(excerpt=excerpt)

            try:
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.1,
                    ),
                )
                data = json.loads(response.text.strip())
            except Exception as e:
                if "429" in str(e):
                    self.stdout.write("Rate limited, waiting 30s...")
                    time.sleep(30)
                    failed += 1
                    continue
                logger.exception("Gemini call failed for mention %s", m.pk)
                failed += 1
                time.sleep(1)
                continue

            mp_name = str(data.get("mp_name", "")).strip()
            mp_constituency = str(data.get("mp_constituency", "")).strip()
            mp_party = str(data.get("mp_party", "")).strip()

            if mp_name:
                m.mp_name = mp_name
                m.mp_constituency = mp_constituency or m.mp_constituency
                m.mp_party = mp_party or m.mp_party
                m.save(update_fields=[
                    "mp_name", "mp_constituency", "mp_party", "updated_at",
                ])
                updated += 1
                self.stdout.write(
                    f"  #{m.id} {m.sitting.sitting_date}: "
                    f"{mp_name} ({mp_constituency}, {mp_party})"
                )
            else:
                self.stdout.write(
                    f"  #{m.id} {m.sitting.sitting_date}: "
                    f"still unknown"
                )

            # Polite delay
            time.sleep(0.5)

            from django.db import connection
            connection.close()

        self.stdout.write(
            self.style.SUCCESS(
                f"\nBackfill complete: {updated} updated, {failed} failed, "
                f"{len(mentions) - updated - failed} still unknown."
            )
        )
