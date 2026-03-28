"""
Management command to compose a News Watch fortnightly digest email broadcast.

Fetches recent approved news articles, generates an Economist-style editorial
digest via Gemini, renders it into an HTML email, and creates a DRAFT Broadcast
for admin review.

Usage:
    python manage.py compose_news_digest
    python manage.py compose_news_digest --days 7
    python manage.py compose_news_digest --dry-run
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
            "--days",
            type=int,
            default=14,
            help="Number of days to look back for articles (default: 14)",
        )
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

    def handle(self, *args, **options):
        days = options["days"]
        dry_run = options["dry_run"]

        digest = generate_news_digest(days=days)
        if digest is None:
            self.stdout.write(
                self.style.WARNING(
                    "No digest generated — either no approved articles in the "
                    f"past {days} days, or GEMINI_API_KEY is not set."
                )
            )
            return

        # Compute period label
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        period_label = (
            f"{start_date.day} {start_date.strftime('%b %Y')} \u2013 "
            f"{end_date.day} {end_date.strftime('%b %Y')}"
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
            send_broadcast(broadcast.pk)
            self.stdout.write(
                self.style.SUCCESS(f"Broadcast {broadcast.pk} sent.")
            )
