"""
Management command to compose a News Watch fortnightly digest email broadcast.

Fetches recent approved news articles, generates an Economist-style editorial
digest via Gemini, renders it into an HTML email, and creates a DRAFT Broadcast
for admin review.

Automatically picks up where the last digest left off — no gaps, no overlaps.

Usage:
    python manage.py compose_news_digest
    python manage.py compose_news_digest --dry-run
    python manage.py compose_news_digest --auto-send --batch-size 250
"""

import os
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import strip_tags

from broadcasts.models import Broadcast
from broadcasts.services.image_generator import generate_hero_image
from broadcasts.services.news_digest import generate_news_digest
from broadcasts.services.sender import send_broadcast


class Command(BaseCommand):
    help = "Compose a News Watch fortnightly digest email as a DRAFT broadcast."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print what would be generated without creating a broadcast",
        )
        parser.add_argument(
            "--auto-send",
            action="store_true",
            help="Automatically send the broadcast after composing (for cron jobs)",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=0,
            help="Max emails per batch (0 = send all). Use resume_sending to continue.",
        )

    def _get_since_date(self):
        """Find when the last news digest was created, or fall back to 14 days."""
        last_digest = (
            Broadcast.objects.filter(
                audience_filter__category="NEWS_WATCH",
            )
            .exclude(status=Broadcast.Status.FAILED)
            .order_by("-created_at")
            .values_list("created_at", flat=True)
            .first()
        )
        if last_digest:
            return last_digest
        return timezone.now() - timedelta(days=14)

    def _should_skip(self):
        """Skip if a digest was already sent in the last 7 days (safety net)."""
        recent = (
            Broadcast.objects.filter(
                audience_filter__category="NEWS_WATCH",
                status__in=[Broadcast.Status.SENT, Broadcast.Status.DRAFT],
                created_at__gte=timezone.now() - timedelta(days=7),
            )
            .exists()
        )
        return recent

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        if not dry_run and self._should_skip():
            self.stdout.write(
                self.style.WARNING(
                    "Skipping — a news digest was already created in the last 7 days."
                )
            )
            return

        since = self._get_since_date()
        days_back = (timezone.now() - since).days or 1

        digest = generate_news_digest(since=since)
        if digest is None:
            self.stdout.write(
                self.style.WARNING(
                    "No digest generated — either no approved articles since "
                    f"{since.strftime('%d %b %Y')}, or GEMINI_API_KEY is not set."
                )
            )
            return

        # Compute period label from actual date range
        start_date = since.date()
        end_date = timezone.now().date()
        period_label = (
            f"{start_date.day} {start_date.strftime('%b %Y')} \u2013 "
            f"{end_date.day} {end_date.strftime('%b %Y')}"
        )
        self.stdout.write(
            f"Coverage: {start_date} to {end_date} ({days_back} days)"
        )

        if dry_run:
            in_brief_count = len(digest.get("in_brief", []))
            self.stdout.write(
                f"DRY RUN \u2014 News Watch ({period_label})\n"
                f"  Editor's note: {digest['editors_note'][:80]}...\n"
                f"  Big story: {digest['big_story']['title']}\n"
                f"  In brief: {in_brief_count} items\n"
                f"  The number: {digest['the_number']['number']}"
            )
            return

        # Generate optional hero image
        big_story = digest.get("big_story", {})
        image_summary = (
            f"{big_story.get('title', '')}: {big_story.get('summary', '')}"
        )
        hero_image_bytes = generate_hero_image(
            content_summary=image_summary,
            style="news",
        )
        if hero_image_bytes:
            self.stdout.write("Hero image generated")

        # Render template without hero image URL first (needs broadcast PK)
        template_context = {
            "period_label": period_label,
            "editors_note": digest["editors_note"],
            "big_story": big_story,
            "in_brief": digest.get("in_brief", []),
            "the_number": digest.get("the_number"),
            "worth_knowing": digest.get("worth_knowing"),
            "hero_image_url": None,
        }
        html_content = render_to_string(
            "broadcasts/news_watch_digest.html", template_context
        )
        text_content = strip_tags(html_content)

        broadcast = Broadcast.objects.create(
            subject=f"News Watch \u2014 {period_label}",
            html_content=html_content,
            text_content=text_content,
            audience_filter={"category": "NEWS_WATCH"},
            status=Broadcast.Status.DRAFT,
        )

        # Re-render with hero image URL now that we have the broadcast PK
        if hero_image_bytes:
            broadcast.hero_image = hero_image_bytes
            backend_url = os.environ.get(
                "BACKEND_URL",
                "https://sjktconnect-api-748286712183.asia-southeast1.run.app",
            )
            hero_url = f"{backend_url}/api/v1/broadcasts/{broadcast.pk}/hero-image/"
            template_context["hero_image_url"] = hero_url
            html_content = render_to_string(
                "broadcasts/news_watch_digest.html", template_context
            )
            broadcast.html_content = html_content
            broadcast.text_content = strip_tags(html_content)
            broadcast.save(update_fields=[
                "hero_image", "html_content", "text_content", "updated_at",
            ])

        self.stdout.write(
            self.style.SUCCESS(
                f"Draft broadcast created (ID: {broadcast.pk}) for "
                f"News Watch ({period_label})"
            )
        )

        if options["auto_send"]:
            send_broadcast(broadcast.pk, batch_size=options["batch_size"])
            pending = broadcast.recipients.filter(
                status="PENDING"
            ).count()
            if pending > 0:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Broadcast {broadcast.pk}: first batch sent, "
                        f"{pending} pending. Run resume_sending to continue."
                    )
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(f"Broadcast {broadcast.pk} sent.")
                )
