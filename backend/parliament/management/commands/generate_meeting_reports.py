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
from difflib import SequenceMatcher

import markdown
from django.core.management.base import BaseCommand

from google import genai
from google.genai import types

from parliament.services.pipeline_registry import get_pipeline_version

from parliament.models import ParliamentaryMeeting, QualityLog, SittingBrief
from parliament.services.evaluator import evaluate_report
from parliament.services.corrector import apply_code_fixes, correct_report

logger = logging.getLogger(__name__)


def html_to_plain(text: str) -> str:
    """Strip HTML tags and decode entities to plain text."""
    text = html.unescape(text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


MEETING_REPORT_PROMPT = """\
You are a parliamentary reporter writing about Tamil school SJK(T) \
discussions in the Malaysian Parliament.

Meeting: {meeting_name} ({start_date} to {end_date}).
{sitting_count} sittings had Tamil school mentions, {total_mentions} total mentions.

{domain_context}

Word guide based on sittings:
- 1-3 sittings: 400-600 words
- 4-7 sittings: 600-900 words
- 8+ sittings: 900-1,200 words (minimum 900)

Return the report in this exact structure:

## [Headline]
A journalistic headline (max 15 words) capturing the most important story \
from this meeting. NOT "Meeting Report" or "Tamil School Discussions".
Example: "PM Pledges Aid for Dilapidated Tamil Schools as MPs Challenge \
Funding Inequity"

[Plain language opening — ONE paragraph, max 80 words, addressed directly to \
a Tamil school parent. Use NO acronyms. Explain in simple terms what happened \
and what it means for their child's school. This paragraph is MANDATORY. \
IMPORTANT: Vary the opening — do NOT start with "If your child attends a \
Tamil school" every time. Lead with the news: what the government did, what \
MPs demanded, what changed. Make it specific to THIS meeting's content.]

[Lead paragraph — 2-3 sentences summarising the big picture for policy readers. \
What happened, why it matters, what changed. Do NOT start with "This report \
covers..." or any procedural preamble. Lead with the story. Use past tense \
throughout.]

## Key Findings
3-5 bullet points. The most important takeaways, with specific amounts, \
names, and dates. Lead with the biggest news.
When a school's infrastructure or enrolment is mentioned, contextualise it \
against the national baseline (e.g. "one of 154 under-enrolled SJK(T)s").

## MP Scorecard
This table tracks ONLY backbench and opposition MPs who raised Tamil school \
issues. Do NOT include Ministers or Deputy Ministers answering on behalf of \
the government — their responses belong in the Executive Responses section.

Markdown table with these exact columns:
| MP Name | Constituency | Topic | Stance | Impact |

Column definitions (use ONLY these values from the taxonomy):
- Topic: max 8 words describing what was raised.
- Stance: Advocacy / Inquiry / Critical (pick one). See taxonomy for definitions.
- Impact: Policy Shift / Budget Allocation / Localised Issue / General Rhetoric \
(pick one). See taxonomy for definitions. Use "General Rhetoric" ONLY when the \
MP's statement is genuinely non-specific — most mentions should fall into a \
more specific category.

One row per MP. If an MP raised multiple topics, use the most significant one.
Do NOT include a Party column.

## Executive Responses
Track how the government responded to issues raised. Use the CABINET REFERENCE \
to verify minister names — do NOT guess or hallucinate minister names. Markdown table:
| Minister/Deputy | Portfolio | Response To | Verdict | Date |

Column definitions:
- Minister/Deputy: Use the exact name from the Cabinet Reference or Hansard excerpt. \
If a minister's name cannot be confirmed from either source, write "Government \
representative" instead.
- Portfolio: Use the exact portfolio title from Cabinet Reference. \
IMPORTANT: MITRA (Malaysian Indian Transformation Unit) sits under the \
Prime Minister's Department, NOT any line ministry. If a minister responds \
about MITRA funding, use "Prime Minister's Department" as portfolio.
- Response To: max 8 words summarising the issue addressed.
- Verdict: Commitment Made / Resolved / Deflected / Unanswered (pick one). \
See taxonomy for definitions.
- Date: the sitting date of the response.

IMPORTANT: If a Minister's response occurs in a different sitting than the \
original inquiry, explicitly note the time-lag. For example, write \
"Written reply on 27 Mar to question raised 4 Feb (51-day lag)" in the \
Response To column. This delay is a key metric of government responsiveness.

When a verdict is "Deflected", add a brief note below the table explaining \
what was deflected and suggesting a follow-up action (e.g. "Wong Kah Woh \
deflected on Tamil education sustainability — stakeholders should request a \
written answer via their MP").

Skip this section if no ministerial responses were recorded.

## Policy Signals
Link parliamentary actions to the national education plan where relevant. \
For each signal:
- What was committed (specific amounts, dates, actions)
- Which RPM commitment it addresses (if applicable)
- Whether this is new or a follow-up to a prior commitment

Report what was said, not what it might mean.
Skip this section entirely if nothing concrete was committed.

## What to Watch
2-3 bullet points written as DIRECT INSTRUCTIONS to school boards and PTA \
leaders. Each bullet must tell the reader what to DO, not what to observe. \
Bad: "Watch for the Ministry's response." \
Good: "If MOE does not provide the RM2 billion breakdown by the next session, \
submit a written question through your MP." \
Include specific deadlines, responsible parties, and concrete next steps.

{previous_context}

Style rules:
- Report, do not analyse. What was said, by whom, in what context.
- Past tense throughout (these sittings have already occurred).
- No editorial commentary ("This was substantive..." or "This demonstrates...").
- Short paragraphs. Simple, clear language. British English.
- No filler, no preamble. Lead with substance.
- Expand acronyms on first use, abbreviation only thereafter. Example: \
"Malaysian Indian Transformation Unit (MITRA)", then just "MITRA". \
Use the glossary provided.
- EXCEPTION: Never expand SJK(T) or SJK(C) — our audience knows these. \
Just use the short form throughout.
- NEVER write "(SJK(T))" with outer brackets. Write "SJK(T)" on its own.
  If needed in parentheses, write "(SJKT)" or "Tamil schools".
- Write "SJK(T)s" (with lowercase s) or "Tamil schools" when referring to \
  multiple schools. NEVER write "SJK(T) schools" — that is redundant because \
  the S already stands for Sekolah (school).
- SJK(T) and SJK(C) are correct on their own. But when placed inside \
  brackets, drop the inner brackets: write "(SJKT)" not "(SJK(T))", \
  and "(SJKC)" not "(SJK(C))".
- Never write the full Malay prefix before the abbreviation. \
  WRONG: "Sekolah Jenis Kebangsaan (Tamil) SJK(T) Ladang Jeram". \
  RIGHT: "SJK(T) Ladang Jeram". The abbreviation IS the school name format.
- Policy Signals bullet points must use proper markdown list syntax: \
  start each item with "- " on its own line. Do NOT use "* " inside a paragraph.

Return as plain text with markdown headings and tables. No code fences.

--- SITTING SUMMARIES ---
{summaries}
--- END SUMMARIES ---
"""

PREVIOUS_CONTEXT_WITH_REPORT = """\
The previous meeting was {prev_name}. Here is its report for delta analysis:

{prev_report}

In the Policy Signals or Key Findings section, include at least one comparison \
to the previous meeting. Example: "The RM22 million for Ladang Jeram compares \
to the RM50 million system-wide allocation announced in the previous session." \
Identify recurring issues, progress on prior concerns, and any new topics."""

PREVIOUS_CONTEXT_NO_REPORT = """\
This is the first meeting being analysed, so no previous report is available.
Focus on reporting what happened — do not mention that this is a first report
or talk about "establishing baselines"."""

SCENE_BRIEF_PROMPT = """\
You are an art director for a parliamentary news publication covering Tamil \
schools in Malaysia.

Given this report headline and key findings, write a 2-3 sentence VISUAL SCENE \
DESCRIPTION for an editorial cartoon. The scene must:
- Capture the SPECIFIC story (not a generic school scene)
- Use a concrete visual metaphor that a viewer would instantly understand
- Include specific physical details (objects, actions, settings) from the findings
- Feature Tamil Indian characters (dark skin, South Asian features)

Do NOT describe abstract concepts. Describe what the viewer SEES.

## Headline
{headline}

## Key Findings
{findings}

Write ONLY the scene description, nothing else."""

ILLUSTRATION_PROMPT = """\
A single-panel editorial cartoon in the style of The Economist or The New Yorker.
Black ink line drawing with minimal colour wash.

Scene: {scene}

Visual requirements:
- Clean line art, crosshatching for shadows, slightly satirical, understated
- The Malaysian Parliament building (Bangunan Parlimen) visible in the background
- Tamil Indian characters (dark skin, South Asian features)
- You may include a short caption or label if it enhances the story
- The school building (if present) should have "SJK(T)" painted on it
"""


def _linkify_briefs(html: str, meeting) -> str:
    """Link sitting dates in report HTML to frontend brief detail pages."""
    frontend_url = os.environ.get("FRONTEND_URL", "https://tamilschool.org")
    briefs = SittingBrief.objects.filter(
        sitting__meeting=meeting,
    ).select_related("sitting")

    for brief in briefs:
        d = brief.sitting.sitting_date
        date_str = d.strftime("%d %B %Y")
        # Cross-platform no-leading-zero (%-d is Linux-only)
        date_str_no_zero = f"{d.day} {d.strftime('%B %Y')}"
        url = f"{frontend_url}/parliament-watch/sittings/{brief.pk}"

        # Process longer string first so "01 December 2025" is matched
        # before "1 December 2025" can match a substring of it.
        date_variants = sorted({date_str, date_str_no_zero}, key=len, reverse=True)
        for ds in date_variants:
            if ds not in html:
                continue
            # Don't linkify if already inside a link.
            # Negative lookbehind for a digit prevents "1 Dec 2025"
            # from matching inside "01 Dec 2025" and creating nested <a> tags.
            pattern = re.compile(r"(?<!\d)" + re.escape(ds))
            def _replace(m, _url=url, _ds=ds):
                start = m.start()
                preceding = html[max(0, start - 50):start]
                if "<a " in preceding and "</a>" not in preceding:
                    return m.group(0)
                return f'<a href="{_url}">{_ds}</a>'
            html = pattern.sub(_replace, html, count=1)

    return html


def _linkify_schools(html: str) -> str:
    """Replace SJK(T) school names in report HTML with links to school pages."""
    from schools.models import School

    # Common abbreviations used in school DB names
    _ABBREV_MAP = {
        "ldg": "ladang", "sg": "sungai", "bkt": "bukit",
        "kg": "kampung", "bt": "bukit",
    }

    frontend_url = os.environ.get("FRONTEND_URL", "https://tamilschool.org")
    # Build lookup: lowercase short name → moe_code
    # Include both abbreviated and expanded forms
    lookup = {}
    for s in School.objects.all():
        short = re.sub(
            r"^Sekolah Jenis Kebangsaan \(Tamil\)\s*",
            "", s.name, flags=re.IGNORECASE,
        ).strip()
        if short and len(short) > 2:
            lookup[short.lower()] = s.moe_code
            # Add expanded variant (e.g. "Ldg Mentakab" → "Ladang Mentakab")
            expanded = short
            for abbr, full in _ABBREV_MAP.items():
                expanded = re.sub(
                    rf"\b{re.escape(abbr)}\b",
                    full.title(),
                    expanded,
                    flags=re.IGNORECASE,
                )
            if expanded.lower() != short.lower():
                lookup[expanded.lower()] = s.moe_code

    # Sort by length descending so longer names match first
    sorted_names = sorted(lookup.keys(), key=len, reverse=True)
    for name in sorted_names:
        code = lookup[name]
        url = f"{frontend_url}/school/{code}"
        pattern = re.compile(
            r"(SJK\(T\)\s+" + re.escape(name) + r")",
            re.IGNORECASE,
        )

        def _replace(m, _url=url):
            # Skip if already inside a link
            start = m.start()
            preceding = html[max(0, start - 50):start]
            if "<a " in preceding and "</a>" not in preceding:
                return m.group(0)
            return f'<a href="{_url}">{m.group(1)}</a>'

        html = pattern.sub(_replace, html)

    # Fuzzy pass: find unlinked SJK(T) names and try fuzzy matching
    # Match SJK(T) followed by word tokens (greedy, up to 6 words)
    unlinked_pattern = re.compile(
        r'SJK\(T\)\s+((?:[A-Za-z]+(?:\s+|$)){1,6})'
    )
    all_short_names = list(
        School.objects.filter(is_active=True).values_list("short_name", flat=True)
    )

    replacements = []  # collect (old_text, new_text) to apply after iteration
    for match in unlinked_pattern.finditer(html):
        full_capture = match.group(0).strip()
        # Skip if already inside a link
        preceding = html[:match.start()]
        if preceding.rfind("<a ") > preceding.rfind("</a>"):
            continue
        # Skip if this exact text is already linked (from exact pass)
        if f">{full_capture}</a>" in html:
            continue

        # Try progressively shorter candidates (drop trailing words)
        words_after = match.group(1).strip().split()
        best_ratio = 0.0
        best_code = None
        best_candidate = None
        for length in range(len(words_after), 0, -1):
            candidate = "SJK(T) " + " ".join(words_after[:length])
            for short_name in all_short_names:
                ratio = SequenceMatcher(
                    None, candidate.lower(), short_name.lower()
                ).ratio()
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_candidate = candidate
                    # Look up code from short_name
                    sn_stripped = re.sub(
                        r"^SJK\(T\)\s*", "", short_name,
                        flags=re.IGNORECASE,
                    ).strip()
                    best_code = lookup.get(sn_stripped.lower())
                    if not best_code:
                        try:
                            best_code = School.objects.get(
                                short_name=short_name
                            ).moe_code
                        except School.DoesNotExist:
                            best_code = None

        if best_ratio >= 0.85 and best_code and best_candidate:
            replacements.append((best_candidate, best_code))
            logger.info(
                "Fuzzy-linked '%s' -> %s (ratio=%.2f)",
                best_candidate, best_code, best_ratio,
            )

    # Apply replacements (longest first to avoid partial overlap)
    replacements.sort(key=lambda r: len(r[0]), reverse=True)
    for text, code in replacements:
        url = f"{frontend_url}/school/{code}"
        link = f'<a href="{url}">{text}</a>'
        html = html.replace(text, link, 1)

    return html


def _normalise_place_name(name: str) -> str:
    """Normalise common Malay romanisation variants for fuzzy matching."""
    s = name.lower()
    for old, new in (
        ("tanjong", "tanjung"), ("sungei", "sungai"), ("bahru", "baharu"),
        ("pulau pinang", "penang"), ("melaka", "malacca"),
        ("negri", "negeri"), ("johor bahru", "johor baharu"),
    ):
        s = s.replace(old, new)
    return s


def _linkify_constituencies(html: str) -> str:
    """Replace constituency names in MP Scorecard table cells with links.

    Finds <td> cells that match a known constituency name and wraps
    the text in a link to /constituency/<code>.
    """
    from schools.models import Constituency

    frontend_url = os.environ.get("FRONTEND_URL", "https://tamilschool.org")
    # Build lookup: normalised name → (display_name, code)
    lookup = {}
    for name, code in Constituency.objects.values_list("name", "code"):
        lookup[_normalise_place_name(name)] = (name, code)

    def _replace_td(match):
        name = match.group(1).strip()
        entry = lookup.get(_normalise_place_name(name))
        if entry:
            _, code = entry
            url = f"{frontend_url}/constituency/{code}"
            return f'<td style="text-align: left;"><a href="{url}">{name}</a></td>'
        return match.group(0)

    # Match <td> cells — the constituency column is the 2nd column in each row
    # We target cells containing known constituency names
    return re.sub(
        r'<td style="text-align: left;">([^<]+)</td>',
        _replace_td,
        html,
    )


def _generate_illustration(client, key_findings: str, headline: str = "") -> bytes | None:
    """Generate an editorial cartoon via Gemini scene brief → Nano Banana Pro."""
    # Step 1: Gemini distils findings into a visual scene description
    try:
        scene_response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=SCENE_BRIEF_PROMPT.format(
                headline=headline,
                findings=key_findings[:2000],
            ),
        )
        scene = scene_response.text.strip()
        logger.info("Illustration scene brief: %s", scene[:200])
    except Exception:
        logger.exception("Scene brief generation failed, using fallback")
        scene = f"A Tamil school building marked SJK(T) with {headline or 'parliamentary debate'}"

    # Step 2: Nano Banana Pro draws the scene
    prompt = ILLUSTRATION_PROMPT.format(scene=scene)
    try:
        response = client.models.generate_content(
            model="gemini-3-pro-image-preview",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE", "TEXT"],
            ),
        )
        for part in response.candidates[0].content.parts:
            if part.inline_data and part.inline_data.mime_type.startswith("image/"):
                img_bytes = part.inline_data.data
                if isinstance(img_bytes, str):
                    import base64
                    img_bytes = base64.b64decode(img_bytes)
                return img_bytes
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

        # Load domain context once for all meetings
        from parliament.services.context_builder import build_context, format_context_for_prompt
        try:
            ctx = build_context()
            domain_context = format_context_for_prompt(ctx)
        except Exception:
            logger.warning("Could not load domain context for reports")
            domain_context = ""

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
                domain_context=domain_context,
                previous_context=previous_context,
                summaries=all_summaries,
            )

            self.stdout.write(
                f"  {meeting.short_name}: generating report "
                f"({len(briefs)} briefs, {len(all_summaries)} chars)..."
            )

            try:
                response = client.models.generate_content(
                    model="gemini-3-pro-preview",
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.4,
                        max_output_tokens=16384,
                        thinking_config=types.ThinkingConfig(
                            thinking_level="HIGH",
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

            # Post-process: fix common Gemini output issues
            # Nested brackets: "(SJK(T))" → "(SJKT)", "(SJK(C))" → "(SJKC)"
            report_md = re.sub(r"\(SJK\(T\)\)", "(SJKT)", report_md)
            report_md = re.sub(r"\(SJK\(C\)\)", "(SJKC)", report_md)
            # Strip redundant full prefix before abbreviation:
            # "Sekolah Jenis Kebangsaan (Tamil) SJK(T)" → "SJK(T)"
            report_md = re.sub(
                r"Sekolah Jenis Kebangsaan \(Tamil\)\s*SJK\(T\)",
                "SJK(T)",
                report_md,
            )
            # "SJK(T) schools" → "SJK(T)s" (avoid redundancy)
            report_md = re.sub(r"SJK\(T\) schools", "SJK(T)s", report_md)

            # Clamp Markdown table separator rows to prevent bloated HTML
            # e.g. | :--- ... (500 dashes) ... | → | :--- |
            def _clamp_separator(match: re.Match) -> str:
                row = match.group(0)
                cells = row.split("|")
                clamped = []
                for cell in cells:
                    stripped = cell.strip()
                    if re.fullmatch(r":?-{3,}:?", stripped):
                        # Keep alignment markers, clamp dashes to 3
                        left = ":" if stripped.startswith(":") else ""
                        right = ":" if stripped.endswith(":") else ""
                        clamped.append(f" {left}---{right} ")
                    else:
                        clamped.append(cell)
                return "|".join(clamped)

            report_md = re.sub(
                r"^\|[\s:|-]+\|$",
                _clamp_separator,
                report_md,
                flags=re.MULTILINE,
            )

            # Convert to HTML
            report_html = markdown.markdown(
                report_md,
                extensions=["tables"],
            )

            # Fix stray markdown bullets that ended up inside <p> tags.
            # Gemini sometimes outputs "* **Bold:**" or "- **Bold:**" inside
            # a paragraph instead of using proper list syntax.
            def _fix_inline_bullets(m):
                content = m.group(1)
                # Split on markdown bullet patterns: "* " or "- " with optional newline
                items = re.split(r"\n?[-*]\s{1,}", content)
                intro = items[0].strip()
                bullets = items[1:]
                if not bullets:
                    return m.group(0)
                parts = []
                if intro:
                    parts.append(f"<p>{intro}</p>")
                li_items = "".join(
                    f"<li>{b.strip()}</li>" for b in bullets if b.strip()
                )
                parts.append(f"<ul>{li_items}</ul>")
                return "\n".join(parts)

            report_html = re.sub(
                r"<p>(.*?[-*]\s+<strong>.*?)</p>",
                _fix_inline_bullets,
                report_html,
                flags=re.DOTALL,
            )

            # Linkify constituency names, school names, and brief dates
            report_html = _linkify_constituencies(report_html)
            report_html = _linkify_schools(report_html)
            report_html = _linkify_briefs(report_html, meeting)

            # Extract headline from first ## heading
            headline = ""
            lines = report_md.split("\n")
            for line in lines:
                if line.startswith("## ") and "Key Findings" not in line and "MP Scorecard" not in line and "Executive Responses" not in line and "Policy Signals" not in line and "What to Watch" not in line:
                    headline = line.lstrip("#").strip()
                    break

            # Extract lead paragraph (text between headline and ## Key Findings)
            exec_summary = ""
            lead_lines = []
            past_headline = False
            for line in lines:
                if line.startswith("## ") and not past_headline:
                    past_headline = True
                    continue
                if past_headline and line.startswith("## "):
                    break
                if past_headline:
                    clean = line.strip()
                    if clean:
                        lead_lines.append(clean)
            if lead_lines:
                exec_summary = " ".join(lead_lines)
                if len(exec_summary) > 500:
                    exec_summary = exec_summary[:497] + "..."

            # Extract Key Findings for social post and illustration
            exec_lines = []
            in_findings = False
            for line in lines:
                if line.startswith("## Key Findings"):
                    in_findings = True
                    continue
                if in_findings and line.startswith("## "):
                    break
                if in_findings:
                    clean = line.strip().lstrip("*-").strip()
                    clean = re.sub(r"\*\*(.+?)\*\*", r"\1", clean)
                    if clean:
                        exec_lines.append(clean)

            # Build social post
            social = (
                f"{meeting.short_name}: {len(briefs)} sittings, "
                f"{total_mentions} Tamil school mentions in Parliament."
            )
            if lead_lines and len(social) < 250:
                first = lead_lines[0].split(".")[0]
                if first and len(social) + len(first) + 2 <= 280:
                    social += " " + first + "."

            meeting.report_html = report_html
            meeting.executive_summary = exec_summary
            meeting.social_post_text = social[:280]

            # --- Quality evaluation loop ---
            from schools.models import School
            from parliament.models import MP
            from parliament.services.quality_loop import run_quality_loop

            school_names = list(
                School.objects.values_list("name", flat=True)[:100]
            )
            mp_names = list(
                MP.objects.values_list("name", flat=True)[:50]
            )

            # Apply code fixes
            report_html = apply_code_fixes(report_html)
            meeting.report_html = report_html

            current_md = report_md

            def evaluate_fn(html):
                return evaluate_report(
                    report_html=html,
                    source_briefs=all_summaries,
                    school_names=school_names,
                    mp_names=mp_names,
                    previous_report=prev_report_text,
                )

            def correct_fn(html, eval_result):
                nonlocal current_md
                corrected_md = correct_report(
                    current_draft=current_md,
                    eval_result=eval_result,
                    source_briefs=all_summaries,
                )
                if corrected_md:
                    current_md = corrected_md
                    new_html = markdown.markdown(
                        current_md, extensions=["tables"],
                    )
                    new_html = _linkify_constituencies(new_html)
                    new_html = _linkify_schools(new_html)
                    new_html = apply_code_fixes(new_html)
                    return new_html
                return None

            def log_fn(attempt, eval_result):
                if eval_result.verdict == "PASS":
                    qf = "GREEN"
                elif eval_result.verdict == "REJECT":
                    qf = "RED"
                else:
                    qf = "AMBER"
                QualityLog.objects.create(
                    content_type="report",
                    meeting=meeting,
                    prompt_version="v3",
                    model_used="gemini-3-pro-preview",
                    attempt_number=attempt,
                    verdict=eval_result.verdict,
                    tier1_results=eval_result.tier1_results,
                    tier2_scores=eval_result.tier2_scores,
                    tier3_flags=eval_result.tier3_flags,
                    corrections_applied=[],
                    quality_flag=qf,
                )

            report_html, quality_flag = run_quality_loop(
                content=report_html,
                evaluate_fn=evaluate_fn,
                correct_fn=correct_fn,
                max_attempts=3,
                log_entry_fn=log_fn,
            )
            meeting.report_html = report_html

            if quality_flag != "GREEN":
                self.stdout.write(
                    self.style.WARNING(
                        f"  {meeting.short_name}: circuit breaker — "
                        f"publishing with {quality_flag} flag"
                    )
                )

            meeting.quality_flag = quality_flag
            meeting.is_published = (quality_flag == "GREEN")

            # Generate editorial cartoon illustration
            findings_text = " ".join(exec_lines) if exec_lines else ""
            if findings_text:
                self.stdout.write(
                    f"  Generating illustration for {meeting.short_name}..."
                )
                img_bytes = _generate_illustration(client, findings_text, headline)
                if img_bytes:
                    meeting.illustration = img_bytes
                    self.stdout.write(
                        f"  Illustration: {len(img_bytes)} bytes"
                    )

            meeting.pipeline_version = get_pipeline_version()
            update_fields = [
                "report_html", "executive_summary", "social_post_text",
                "quality_flag", "is_published", "pipeline_version", "updated_at",
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
