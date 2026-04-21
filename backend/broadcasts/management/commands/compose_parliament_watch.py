"""
Management command to compose a Parliament Watch email broadcast.

Takes a ParliamentaryMeeting, generates an action-oriented digest via Gemini,
renders it into an HTML email, and creates a DRAFT Broadcast for admin review.

Usage:
    python manage.py compose_parliament_watch --meeting-id 1
    python manage.py compose_parliament_watch --meeting-id 1 --dry-run
"""

import os

from django.core.management.base import BaseCommand
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from broadcasts.models import Broadcast
from broadcasts.services.image_generator import generate_hero_image
from broadcasts.services.parliament_digest import generate_parliament_digest
from parliament.models import ParliamentaryMeeting


class Command(BaseCommand):
    help = "Compose a Parliament Watch email as a DRAFT broadcast."

    def add_arguments(self, parser):
        parser.add_argument(
            "--meeting-id",
            type=int,
            required=True,
            help="Primary key of the ParliamentaryMeeting to digest",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print what would be generated without creating a broadcast",
        )

    def handle(self, *args, **options):
        meeting_id = options["meeting_id"]
        dry_run = options["dry_run"]

        try:
            meeting = ParliamentaryMeeting.objects.get(pk=meeting_id)
        except ParliamentaryMeeting.DoesNotExist:
            self.stderr.write(
                self.style.ERROR(
                    f"ParliamentaryMeeting with ID {meeting_id} not found."
                )
            )
            return

        digest = generate_parliament_digest(meeting)
        if digest is None:
            self.stderr.write(
                self.style.ERROR(
                    "Digest generation failed — check report_html and GEMINI_API_KEY."
                )
            )
            return

        if dry_run:
            dev_count = len(digest.get("developments", []))
            self.stdout.write(
                f"DRY RUN — {meeting.short_name}\n"
                f"  Headlines: {digest['headlines'][:80]}...\n"
                f"  Developments: {dev_count}\n"
                f"  One thing: {digest['one_thing'][:80]}"
            )
            return

        # Generate optional hero image
        hero_image_bytes = generate_hero_image(
            content_summary=digest["headlines"],
            style="parliament",
        )
        if hero_image_bytes:
            self.stdout.write("Hero image generated")

        template_context = {
            "meeting_name": meeting.name,
            "start_date": meeting.start_date,
            "end_date": meeting.end_date,
            "headlines": digest["headlines"],
            "developments": digest.get("developments", []),
            "scorecard_summary": digest.get("scorecard_summary", ""),
            "one_thing": digest.get("one_thing", ""),
            "hero_image_url": None,
        }
        html_content = render_to_string(
            "broadcasts/parliament_watch.html", template_context
        )
        text_content = strip_tags(html_content)

        broadcast = Broadcast.objects.create(
            subject=f"Parliament Watch \u2014 {meeting.short_name}",
            html_content=html_content,
            text_content=text_content,
            audience_filter={"category": "PARLIAMENT_WATCH"},
            kind=Broadcast.Kind.PARLIAMENT_WATCH,
            status=Broadcast.Status.DRAFT,
            hero_image=hero_image_bytes or b"",
        )

        # Re-render with hero image URL now that we have the broadcast PK
        if hero_image_bytes:
            backend_url = os.environ.get(
                "BACKEND_URL",
                "https://sjktconnect-api-748286712183.asia-southeast1.run.app",
            )
            hero_url = f"{backend_url}/api/v1/broadcasts/{broadcast.pk}/hero-image/"
            template_context["hero_image_url"] = hero_url
            html_content = render_to_string(
                "broadcasts/parliament_watch.html", template_context
            )
            broadcast.html_content = html_content
            broadcast.text_content = strip_tags(html_content)
            broadcast.save(update_fields=["html_content", "text_content"])

        self.stdout.write(
            self.style.SUCCESS(
                f"Draft broadcast created (ID: {broadcast.pk}) for "
                f"{meeting.short_name}"
            )
        )
