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

import calendar
import os
from datetime import date

from django.core.management.base import BaseCommand, CommandError
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from broadcasts.models import Broadcast
from broadcasts.services.blast_aggregator import aggregate_month
from broadcasts.services.image_generator import generate_hero_image
from broadcasts.services.monthly_analyst import generate_monthly_analysis
from broadcasts.services.sender import send_broadcast


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

    def handle(self, *args, **options):
        year, month = self._parse_month(options["month"])
        month_label = f"{calendar.month_name[month]} {year}"
        dry_run = options["dry_run"]

        data = aggregate_month(year, month)

        parliament_count = len(list(data["parliament"]))
        news_count = len(list(data["news"]))
        scorecard_count = len(list(data["scorecards"]))

        if dry_run:
            self.stdout.write(f"DRY RUN \u2014 {month_label}")
            self.stdout.write(
                f"  {parliament_count} parliament, "
                f"{news_count} news, "
                f"{scorecard_count} scorecard items"
            )
            return

        # Try v2 analytical blast via Gemini
        analysis = generate_monthly_analysis(year, month)

        hero_image_bytes = None
        if analysis:
            # Generate optional hero image for v2 analytical blast
            hero_image_bytes = generate_hero_image(
                content_summary=analysis.get(
                    "executive_summary", ""
                )[:200],
                style="monthly",
            )
            if hero_image_bytes:
                self.stdout.write("Hero image generated")

            # Render template without hero_image_url — it will be
            # patched in after the broadcast is saved (needs the PK)
            html_content = render_to_string(
                "broadcasts/monthly_blast_v2.html",
                {
                    "month_label": month_label,
                    "analysis": analysis,
                    "hero_image_url": None,
                },
            )
            self.stdout.write("Using v2 analytical template (Gemini)")
        else:
            # Fallback to v1 template (no Gemini key or error)
            data = aggregate_month(year, month)
            html_content = render_to_string(
                "broadcasts/monthly_blast.html",
                {
                    "month_label": month_label,
                    "parliament": data["parliament"],
                    "news": data["news"],
                    "scorecards": data["scorecards"],
                },
            )
            self.stdout.write("Using v1 template (Gemini unavailable)")

        text_content = strip_tags(html_content)

        broadcast = Broadcast.objects.create(
            subject=f"Monthly Intelligence Blast \u2014 {month_label}",
            html_content=html_content,
            text_content=text_content,
            audience_filter={"category": "MONTHLY_BLAST"},
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
                "broadcasts/monthly_blast_v2.html",
                {
                    "month_label": month_label,
                    "analysis": analysis,
                    "hero_image_url": hero_url,
                },
            )
            broadcast.html_content = html_content
            broadcast.text_content = strip_tags(html_content)
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
