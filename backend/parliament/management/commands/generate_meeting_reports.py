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
You are a parliamentary reporter writing about Tamil school SJK(T)
discussions in the Malaysian Parliament.

Meeting: {meeting_name} ({start_date} to {end_date}).
{sitting_count} sittings had Tamil school mentions, {total_mentions} total mentions.

National baseline (use to contextualise individual cases):
- 528 SJK(T) schools nationwide, 69,900 students, 5,460 teachers
- 154 schools are under-enrolled (fewer than 150 students)
- Schools span 222 parliamentary constituencies across 13 states

Word guide based on sittings:
- 1-3 sittings: 400-600 words
- 4-7 sittings: 600-900 words
- 8+ sittings: 900-1,200 words (minimum 900)

Return the report in this exact structure:

## [Headline]
A journalistic headline (max 15 words) capturing the most important story
from this meeting. NOT "Meeting Report" or "Tamil School Discussions".
Example: "PM Pledges Aid for Dilapidated Tamil Schools as MPs Challenge
Funding Inequity"

[Lead paragraph — 2-3 sentences summarising the big picture. What happened,
why it matters, what changed. This is what readers see before expanding.
Do NOT start with "This report covers..." or any procedural preamble.
Lead with the story.]

## Key Findings
3-5 bullet points. The most important takeaways, with specific amounts,
names, and dates. Lead with the biggest news.
When a school's infrastructure or enrolment is mentioned, contextualise it
against the national baseline (e.g. "one of 154 under-enrolled SJK(T)s").

## MP Scorecard
This table tracks ONLY backbench and opposition MPs who raised Tamil school
issues. Do NOT include Ministers or Deputy Ministers answering on behalf of
the government — their responses belong in the Executive Responses section.

Markdown table with these exact columns:
| MP Name | Constituency | Topic | Stance | Impact |

Column definitions (use ONLY these values):
- Topic: max 8 words describing what was raised.
- Stance: Advocacy / Inquiry / Critical (pick one).
- Impact: Policy Shift / Budget Allocation / Localised Issue / General Rhetoric (pick one).

One row per MP. If an MP raised multiple topics, use the most significant one.
Do NOT include a Party column.

## Executive Responses
Track how the government responded to issues raised. Markdown table:
| Minister/Deputy | Portfolio | Response To | Verdict | Date |

Column definitions:
- Response To: max 8 words summarising the issue addressed.
- Verdict: Commitment Made / Resolved / Deflected / Unanswered (pick one).
- Date: the sitting date of the response.

IMPORTANT: If a Minister's response occurs in a different sitting than the
original inquiry, explicitly note the time-lag. For example, write
"Written reply on 27 Mar to question raised 4 Feb (51-day lag)" in the
Response To column. This delay is a key metric of government responsiveness.

Skip this section if no ministerial responses were recorded.

## Policy Signals
Budget commitments, policy shifts, or ministerial promises with specific
figures and dates. Report what was said, not what it might mean.
Skip this section entirely if nothing concrete was committed.

## What to Watch
2-3 bullet points for community stakeholders. Be specific and actionable.
Tell school boards and PTA leaders what to do next.

{previous_context}

Style rules:
- Report, do not analyse. What was said, by whom, in what context.
- No editorial commentary ("This was substantive..." or "This demonstrates...").
- Short paragraphs. Simple, clear language. British English.
- No filler, no preamble. Lead with substance.
- NEVER write "(SJK(T))" with outer brackets. Write "SJK(T)" on its own.
  If needed in parentheses, write "(SJKT)" or "Tamil schools".

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
This is the first meeting being analysed, so no previous report is available.
Focus on reporting what happened — do not mention that this is a first report
or talk about "establishing baselines"."""

ILLUSTRATION_PROMPT = """\
A single-panel editorial cartoon in the style of The Economist or The New Yorker.
Black ink line drawing with minimal colour wash.

Scene inspired by these parliamentary findings about Tamil schools in Malaysia:
{findings}

Visual requirements:
- Clean line art, crosshatching for shadows, slightly satirical, understated
- The Malaysian Parliament dome visible in the background
- A Tamil school building with the letters SJK(T) painted on it, central
- Tamil Indian parents and teachers (dark skin, South Asian features) interacting
  with Malaysian MPs in the scene
- The image must contain ONLY the text "SJK(T)" on the school building.
  No other words, labels, captions, signs, banners, or speech bubbles anywhere.
"""


def _linkify_schools(html: str) -> str:
    """Replace SJK(T) school names in report HTML with links to school pages."""
    from schools.models import School

    frontend_url = os.environ.get("FRONTEND_URL", "https://tamilschool.org")
    # Build lookup: lowercase short name → moe_code
    lookup = {}
    for s in School.objects.all():
        short = re.sub(
            r"^Sekolah Jenis Kebangsaan \(Tamil\)\s*",
            "", s.name, flags=re.IGNORECASE,
        ).strip()
        if short and len(short) > 2:
            lookup[short.lower()] = s.moe_code

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
    return html


def _linkify_constituencies(html: str) -> str:
    """Replace constituency names in MP Scorecard table cells with links.

    Finds <td> cells that match a known constituency name and wraps
    the text in a link to /constituency/<code>.
    """
    from schools.models import Constituency

    frontend_url = os.environ.get("FRONTEND_URL", "https://tamilschool.org")
    # Build lookup: lowercase name → code
    lookup = {}
    for c in Constituency.objects.values_list("name", "code"):
        lookup[c[0].lower()] = c[1]

    def _replace_td(match):
        name = match.group(1).strip()
        code = lookup.get(name.lower())
        if code:
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
                    model="gemini-3-pro-preview",
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.4,
                        max_output_tokens=8192,
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

            # Post-process: fix "(SJK(T))" → "SJK(T)"
            report_md = re.sub(r"\(SJK\(T\)\)", "SJK(T)", report_md)

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

            # Linkify constituency and school names
            report_html = _linkify_constituencies(report_html)
            report_html = _linkify_schools(report_html)

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
            school_names = list(
                School.objects.values_list("name", flat=True)[:100]
            )
            mp_names = list(
                MP.objects.values_list("name", flat=True)[:50]
            )

            # Apply code fixes
            report_html = apply_code_fixes(report_html)
            meeting.report_html = report_html

            quality_flag = "GREEN"
            attempt = 1
            current_md = report_md

            while attempt <= 3:
                eval_result = evaluate_report(
                    report_html=report_html,
                    source_briefs=all_summaries,
                    school_names=school_names,
                    mp_names=mp_names,
                    previous_report=prev_report_text,
                )

                if eval_result.verdict == "PASS":
                    quality_flag = "GREEN"
                elif eval_result.verdict == "REJECT":
                    quality_flag = "RED"
                else:
                    quality_flag = "AMBER"

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
                    quality_flag=quality_flag,
                )

                if eval_result.verdict == "PASS":
                    break

                if attempt >= 3:
                    self.stdout.write(
                        self.style.WARNING(
                            f"  {meeting.short_name}: circuit breaker — "
                            f"publishing with {quality_flag} flag"
                        )
                    )
                    break

                # Attempt correction
                corrected_md = correct_report(
                    current_draft=current_md,
                    eval_result=eval_result,
                    source_briefs=all_summaries,
                )
                if corrected_md:
                    current_md = corrected_md
                    report_html = markdown.markdown(
                        current_md, extensions=["tables"],
                    )
                    report_html = _linkify_constituencies(report_html)
                    report_html = _linkify_schools(report_html)
                    report_html = apply_code_fixes(report_html)
                    meeting.report_html = report_html
                else:
                    break

                attempt += 1

            meeting.quality_flag = quality_flag

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
                "quality_flag", "updated_at",
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
