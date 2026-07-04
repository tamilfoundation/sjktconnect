"""
Management command to compose a Monthly Intelligence Blast.

Aggregates the top approved Parliament Watch mentions, News Watch articles,
and MP Scorecards for a given month, renders them into an HTML email, and
creates a DRAFT Broadcast for admin review.

Usage:
    python manage.py compose_monthly_blast                # Previous month
    python manage.py compose_monthly_blast --month 2026-02
    python manage.py compose_monthly_blast --month 2026-02 --dry-run
"""

import base64
import calendar
import os
from datetime import date, datetime

from django.core.management.base import BaseCommand, CommandError
from django.template.loader import render_to_string
from broadcasts.services.text_alternative import html_to_text_alternative

from broadcasts.models import Broadcast
from broadcasts.services.blast_aggregator import aggregate_month
from broadcasts.services.duplicate_guard import (
    check_duplicate,
    format_block_message,
)
from broadcasts.services.image_generator import generate_hero_image
from broadcasts.services.monthly_analyst import generate_monthly_analysis
from broadcasts.services.sender import send_broadcast
from broadcasts.services.topic_clusterer import (
    cluster_news_articles,
    rank_and_cap_clusters,
)

NEWS_TOP_N = 10


def _promote_top_story(news_clusters, all_clusters, top_story_cluster_index):
    """Promote the analyst's picked cluster to position #1 in shown news.

    Audit 2026-07-05: fixes the coherence gap where the subject line +
    executive summary named a story that never appeared in the "In The
    News" section. `top_story_cluster_index` is a 0-based index into the
    NON-OTHER clusters as they were presented to the analyst.

    Behaviour:
      - Missing / invalid / -1 index → return news_clusters unchanged
        (backward compat, or "genuinely quiet month" signal).
      - Picked cluster already at position #1 → return unchanged.
      - Picked cluster elsewhere in the top-N → move to position #1.
      - Picked cluster NOT in the top-N (ranked lower by hybrid score) →
        insert at position #1 and drop the last one from the top-N so
        the section size doesn't grow.
    """
    if top_story_cluster_index is None or top_story_cluster_index < 0:
        return news_clusters

    # Rebuild the non-Other cluster list in the order the analyst saw
    # (matches _format_clusters ordering: preserved input order, skip Other).
    ordered_non_other = [c for c in all_clusters if not c.get("is_other")]
    if top_story_cluster_index >= len(ordered_non_other):
        return news_clusters  # invalid index, leave the list alone
    picked = ordered_non_other[top_story_cluster_index]

    # Where is `picked` in the currently-shown news_clusters?
    picked_lead_pk = getattr(picked.get("lead_article"), "pk", None)

    def _same(c):
        return (
            c.get("lead_article") is picked.get("lead_article")
            or (
                picked_lead_pk is not None
                and getattr(c.get("lead_article"), "pk", None) == picked_lead_pk
            )
        )

    for i, c in enumerate(news_clusters):
        if _same(c):
            if i == 0:
                return news_clusters  # already at top
            reordered = [news_clusters[i]] + news_clusters[:i] + news_clusters[i+1:]
            return reordered

    # Not currently shown — insert at top, drop the tail to keep the size.
    return [picked] + news_clusters[:-1] if news_clusters else [picked]


class Command(BaseCommand):
    help = "Compose a Monthly Intelligence Blast as a DRAFT broadcast."

    def add_arguments(self, parser):
        parser.add_argument(
            "--month",
            type=str,
            default="",
            help="Target month in YYYY-MM format (default: previous month)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print what would be included without creating a broadcast",
        )
        parser.add_argument(
            "--auto-send",
            action="store_true",
            help="Automatically send the broadcast after composing (for cron jobs)",
        )
        parser.add_argument(
            "--backfill-since",
            type=str,
            default="",
            help=(
                "YYYY-MM-DD. When set, sitting briefs and meeting reports "
                "ALSO include any item with sitting_date or published_at >= "
                "this date that isn't already in the target-month set. Used "
                "once to fill a gap when a prior digest missed content "
                "(e.g. a meeting report published just before the month "
                "boundary). Has no effect on mentions, news, or scorecards."
            ),
        )
        parser.add_argument(
            "--force-duplicate",
            action="store_true",
            help=(
                "Bypass the duplicate-broadcast guard. Only use when "
                "intentionally re-sending after a recipient-list correction "
                "or spam-flag fix."
            ),
        )
        parser.add_argument(
            "--preview-html",
            type=str,
            default="",
            help=(
                "Sprint 24 #10: render the full v2 template (incl. Gemini "
                "analysis + topic clustering) and write the HTML to the "
                "given local path. Does NOT create a Broadcast row, does "
                "NOT send to Brevo. Open the file in a browser to preview "
                "before deploy. Costs ~$0.001 in Gemini tokens per call. "
                "Mutually exclusive with --dry-run / --auto-send."
            ),
        )

    def handle(self, *args, **options):
        year, month = self._parse_month(options["month"])
        month_label = f"{calendar.month_name[month]} {year}"
        dry_run = options["dry_run"]
        preview_path = options.get("preview_html", "") or ""
        backfill_since = self._parse_backfill_since(options["backfill_since"])

        if preview_path and (dry_run or options.get("auto_send")):
            raise CommandError(
                "--preview-html is mutually exclusive with --dry-run and "
                "--auto-send. Pick one mode."
            )

        coverage_start = date(year, month, 1)
        coverage_end = date(year, month, calendar.monthrange(year, month)[1])

        # Skip the duplicate-broadcast guard for preview too — preview
        # creates no Broadcast row, so a same-month "duplicate" is not
        # actually a duplicate.
        if not dry_run and not preview_path and not options["force_duplicate"]:
            existing = check_duplicate(
                kind=Broadcast.Kind.MONTHLY_BLAST,
                coverage_start=coverage_start,
                coverage_end=coverage_end,
            )
            if existing is not None:
                raise CommandError(format_block_message(existing))

        data = aggregate_month(year, month, backfill_since=backfill_since)

        parliament_count = len(list(data["parliament"]))
        news_count = len(list(data["news"]))
        brief_count = len(list(data["briefs"]))
        meeting_count = len(list(data["meeting_reports"]))
        scorecard_count = len(list(data["scorecards"]))
        scorecards_fallback = data["scorecards_are_lifetime_fallback"]

        if dry_run:
            self.stdout.write(f"DRY RUN \u2014 {month_label}")
            if backfill_since:
                self.stdout.write(f"  backfill window: items >= {backfill_since}")
            session_state = (
                f"in session ({data['parliament_sitting_count']} sittings)"
                if data.get("parliament_was_in_session")
                else "NOT in session"
            )
            self.stdout.write(
                f"  Parliament: {session_state}; "
                f"{data.get('parliament_total', 0)} mentions total "
                f"(showing top {parliament_count})"
            )
            sb = data.get("news_sentiment_breakdown") or {}
            self.stdout.write(
                f"  News: {data.get('news_total', 0)} approved "
                f"({sb.get('positive', 0)} pos, {sb.get('negative', 0)} neg, "
                f"{sb.get('neutral', 0)} neu) — showing top {news_count}"
            )
            self.stdout.write(
                f"  Schools mentioned (news + Hansard): "
                f"{data.get('schools_mentioned_total', 0)}"
            )
            self.stdout.write(
                f"  {brief_count} sitting briefs, "
                f"{meeting_count} meeting reports, "
                f"{scorecard_count} scorecard items"
                f"{' (lifetime fallback)' if scorecards_fallback else ''}"
            )
            for m in data["meeting_reports"]:
                self.stdout.write(
                    f"    meeting: {m.short_name} ({m.start_date} \u2192 {m.end_date})"
                )
            for b in data["briefs"]:
                self.stdout.write(
                    f"    brief: {b.sitting.sitting_date} \u2014 {b.title[:60]}"
                )
            return

        # 2026-07-05: cluster news FIRST so the analyst has the actual
        # story-list as context. Was: analyst ran independently and
        # picked a top story that sometimes wasn't in the news section
        # (June 2026: subject named "RM4.3M Ladang Rini" but that
        # cluster ranked #8 and dropped out of the top-10 shown).
        #
        # Sprint 24 task #2: cluster the approved news articles into
        # topic groups so a 46-article month reads as a small set of
        # named stories rather than a flat list. Fail-open inside the
        # service — never raises.
        all_clusters = cluster_news_articles(list(data.get("news_all", [])))
        # Sprint 24 task #10b: rank by hybrid score, cap at top N
        # stories shown as cards. Everything else (Other bucket +
        # dropped clusters past the cap) becomes the footer remainder
        # count so a reader can still see all news on the website.
        news_clusters, news_remainder_count = rank_and_cap_clusters(
            all_clusters, top_n=NEWS_TOP_N,
        )
        self.stdout.write(
            f"News: {len(all_clusters)} cluster(s) from "
            f"{data.get('news_total', 0)} approved articles -- "
            f"showing top {len(news_clusters)} as cards, "
            f"{news_remainder_count} article(s) rolled into footer"
        )

        # Try v2 analytical blast via Gemini.
        # Sprint 24 #6 (LOCKED 2026-05-11): there is no v1 fallback. If
        # Gemini fails, the compose aborts with a CommandError so the
        # admin sees a clear failure instead of a half-quality digest.
        # Pass all_clusters so the analyst picks its top story from a
        # story the reader will actually see below.
        analysis = generate_monthly_analysis(
            year, month,
            backfill_since=backfill_since,
            news_clusters=all_clusters,
        )
        if analysis is None:
            raise CommandError(
                "Monthly blast compose aborted: monthly_analyst returned None "
                "(GEMINI_API_KEY missing, API failure, or invalid response). "
                "Fix the underlying issue and rerun — Sprint 24 removed the "
                "v1 fallback because a half-quality digest is worse than a "
                "clean error."
            )

        # 2026-07-05: honour top_story_cluster_index — promote the
        # analyst's picked cluster to position #1 in the shown news
        # cards. This guarantees the reader sees the same story in
        # the subject line, executive summary, and top news card.
        news_clusters = _promote_top_story(
            news_clusters, all_clusters, analysis.get("top_story_cluster_index"),
        )

        # Sprint 23 + 24: extra context for v2 render. Surfaces the
        # deterministic counts, the full news list, the schools-mentioned
        # set, the recess flag, and (Sprint 24 #2) the news clusters.
        v2_context_extras = {
            "news_all": list(data.get("news_all", [])),
            "news_clusters": news_clusters,
            "news_remainder_count": news_remainder_count,
            "schools_mentioned": data.get("schools_mentioned", []),
            "schools_mentioned_total": data.get("schools_mentioned_total", 0),
            "news_total": data.get("news_total", 0),
            "parliament_total": data.get("parliament_total", 0),
            "news_sentiment_breakdown": data.get("news_sentiment_breakdown", {}),
            "parliament_was_in_session": data.get("parliament_was_in_session", False),
            "parliament_sitting_count": data.get("parliament_sitting_count", 0),
            "donate_url": "https://tamilschool.org/donate",
            "share_url": (
                "mailto:?subject=Tamil%20Schools%20Intelligence%20Blast"
                "&body=Have%20a%20look%20at%20this%20month%27s%20digest"
                "%20from%20tamilschool.org"
            ),
            "mp_activity_url": "https://tamilschool.org/parliament-watch",
        }

        # Generate optional hero image for the analytical blast.
        hero_image_bytes = generate_hero_image(
            content_summary=analysis.get("executive_summary", "")[:200],
            style="monthly",
        )
        if hero_image_bytes:
            self.stdout.write("Hero image generated")

        # Render template without hero_image_url — it will be patched in
        # after the broadcast is saved (needs the PK). Exception: in
        # --preview-html mode there is no broadcast row, so inline the
        # hero bytes as a base64 data: URL so the preview file is fully
        # self-contained when opened from the filesystem.
        if preview_path and hero_image_bytes:
            hero_b64 = base64.b64encode(hero_image_bytes).decode("ascii")
            preview_hero_url = f"data:image/png;base64,{hero_b64}"
        else:
            preview_hero_url = None
        html_content = render_to_string(
            "broadcasts/monthly_blast.html",
            {
                "month_label": month_label,
                "analysis": analysis,
                "hero_image_url": preview_hero_url,
                "briefs": data["briefs"],
                "meeting_reports": data["meeting_reports"],
                "scorecards": data["scorecards"],
                "scorecards_are_lifetime_fallback": data[
                    "scorecards_are_lifetime_fallback"
                ],
                "schools_by_state": data.get("schools_by_state", {}),
                **v2_context_extras,
            },
        )
        self.stdout.write("Using v2 analytical template (Gemini)")

        # Sprint 24 #10: preview-only path. Writes the rendered HTML to
        # a local file and returns BEFORE any Broadcast row is created.
        # No DB write, no send, no Brevo call. Safe by construction —
        # the only code that touches Brevo is send_broadcast, which is
        # downstream of this early return.
        if preview_path:
            # Wrap the bare-div email body in an HTML5 shell so the
            # browser knows it's UTF-8. Without this, Windows browsers
            # default to cp1252 and Tamil renders as mojibake. Also
            # nudges the font stack toward Tamil-capable fallbacks so
            # the preview matches what most email clients pick.
            preview_html = (
                "<!DOCTYPE html>\n"
                '<html lang="en">\n<head>\n'
                '<meta charset="UTF-8">\n'
                '<meta name="viewport" content="width=device-width,initial-scale=1">\n'
                "<title>Monthly Intelligence Blast — preview</title>\n"
                "<style>"
                "body{margin:0;padding:24px;background:#f9fafb;"
                "font-family:Georgia,'Noto Serif Tamil','Latha',serif;}"
                "</style>\n"
                "</head>\n<body>\n"
                f"{html_content}\n"
                "</body>\n</html>\n"
            )
            with open(preview_path, "w", encoding="utf-8") as f:
                f.write(preview_html)
            self.stdout.write(self.style.SUCCESS(
                f"Preview written to {preview_path} "
                f"({len(preview_html):,} bytes). "
                f"No Broadcast row created, no email sent."
            ))
            return

        text_content = html_to_text_alternative(html_content)

        # Sprint 23: dynamic subject line from the LLM-generated
        # headline, falling back to the generic month label.
        subject = self._build_subject(month_label, analysis)

        broadcast = Broadcast.objects.create(
            subject=subject,
            html_content=html_content,
            text_content=text_content,
            audience_filter={"category": "MONTHLY_BLAST"},
            kind=Broadcast.Kind.MONTHLY_BLAST,
            coverage_start_date=coverage_start,
            coverage_end_date=coverage_end,
            status=Broadcast.Status.DRAFT,
            hero_image=hero_image_bytes or b"",
        )

        # Patch hero image URL into HTML now that we have the PK
        if hero_image_bytes:
            backend_url = os.environ.get(
                "BACKEND_URL",
                "https://sjktconnect-api-748286712183.asia-southeast1.run.app",
            )
            hero_url = f"{backend_url}/api/v1/broadcasts/{broadcast.pk}/hero-image/"
            html_content = render_to_string(
                "broadcasts/monthly_blast.html",
                {
                    "month_label": month_label,
                    "analysis": analysis,
                    "hero_image_url": hero_url,
                    "briefs": data["briefs"],
                    "meeting_reports": data["meeting_reports"],
                    "scorecards": data["scorecards"],
                    "scorecards_are_lifetime_fallback": data[
                        "scorecards_are_lifetime_fallback"
                    ],
                    "schools_by_state": data.get("schools_by_state", {}),
                    **v2_context_extras,
                },
            )
            broadcast.html_content = html_content
            broadcast.text_content = html_to_text_alternative(html_content)
            broadcast.save(update_fields=["html_content", "text_content"])

        self.stdout.write(
            self.style.SUCCESS(
                f"Draft broadcast created (ID: {broadcast.pk}) with "
                f"{parliament_count} parliament, {news_count} news, "
                f"{scorecard_count} scorecard items"
            )
        )

        if options["auto_send"]:
            send_broadcast(broadcast.pk)
            self.stdout.write(
                self.style.SUCCESS(f"Broadcast {broadcast.pk} sent.")
            )

    def _build_subject(self, month_label: str, analysis: dict | None) -> str:
        """Sprint 23: build a punchy subject from the LLM headline.

        Falls back to the generic month label when the LLM output is
        absent or the headline field is missing/empty. The headline
        prefix `{month_label}: ` keeps the cadence visible in inboxes.

        Defensive single-story collapse: the prompt asks Gemini for ONE
        story only, but the May 2026 send shipped a two-story headline
        joined by a semicolon ("Private Sector Boosts SJK(T) Ladang
        Labu; Sedenak Gets Piped Water After 67 Years"). If a separator
        slips through, take only the first clause so the subject reads
        as a single story.
        """
        generic = f"Monthly Intelligence Blast \u2014 {month_label}"
        if not analysis:
            return generic
        headline = (analysis.get("headline") or "").strip()
        if not headline:
            return generic
        # Single-story collapse: split on semicolon or " and " (with surrounding
        # spaces to avoid splitting words like "Sungai Sandhanam"). Take the
        # first non-empty clause and strip trailing punctuation/whitespace.
        for sep in (";", " and ", " & ", " + "):
            if sep in headline:
                first = headline.split(sep, 1)[0].strip()
                if first:
                    headline = first
                    break
        headline = headline.rstrip(",.;:&+ ").strip()
        # Cap length to avoid Gmail truncation in list view.
        max_len = 90
        candidate = f"{month_label}: {headline}"
        if len(candidate) > max_len:
            candidate = candidate[: max_len - 1].rstrip() + "\u2026"
        return candidate

    def _parse_backfill_since(self, value: str) -> date | None:
        """Parse the optional --backfill-since YYYY-MM-DD argument."""
        if not value:
            return None
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError:
            raise CommandError(
                f"Invalid --backfill-since date '{value}'. Use YYYY-MM-DD."
            )

    def _parse_month(self, month_str: str) -> tuple[int, int]:
        """Parse YYYY-MM string or default to previous month."""
        if not month_str:
            today = date.today()
            if today.month == 1:
                return today.year - 1, 12
            return today.year, today.month - 1

        try:
            parts = month_str.split("-")
            return int(parts[0]), int(parts[1])
        except (ValueError, IndexError):
            raise CommandError(
                f"Invalid month format: '{month_str}'. Use YYYY-MM (e.g. 2026-02)."
            )
