"""
Management command to compose a Parliament Watch email broadcast.

Takes a ParliamentaryMeeting, generates an action-oriented digest via Gemini,
renders it into an HTML email, and creates a DRAFT Broadcast for admin review.

Usage:
    python manage.py compose_parliament_watch --meeting-id 1
    python manage.py compose_parliament_watch --meeting-id 1 --dry-run
    python manage.py compose_parliament_watch --auto         # all unsent published meetings
    python manage.py compose_parliament_watch --auto --dry-run
"""

import os
from datetime import date

from django.core.management.base import BaseCommand
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from broadcasts.models import Broadcast
from broadcasts.services.image_generator import generate_hero_image
from broadcasts.services.parliament_digest import generate_parliament_digest
from parliament.models import ParliamentaryMeeting


# --auto only picks up meetings that ended on or after this date.
# Set to 2026-04-30 (the day this digest launched) so the existing 11
# historical published meetings (going back to 2023) are NOT auto-
# backfilled. The first Parliament Watch digest will be sent for the
# next meeting that ends after this date — expected ~June/July 2026.
# To digest an older meeting, run with explicit --meeting-id N.
AUTO_COMPOSE_START_DATE = date(2026, 4, 30)


class Command(BaseCommand):
    help = "Compose a Parliament Watch email as a DRAFT broadcast."

    def add_arguments(self, parser):
        parser.add_argument(
            "--meeting-id",
            type=int,
            help="Primary key of the ParliamentaryMeeting to digest. Mutually exclusive with --auto.",
        )
        parser.add_argument(
            "--auto",
            action="store_true",
            help=(
                "Scan for all published ParliamentaryMeeting reports that don't "
                "yet have a PARLIAMENT_WATCH Broadcast. Compose one DRAFT per "
                "meeting. Idempotent — safe to re-run from cron / pipeline."
            ),
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print what would be generated without creating a broadcast",
        )

    def handle(self, *args, **options):
        meeting_id = options.get("meeting_id")
        auto = options["auto"]
        dry_run = options["dry_run"]

        if not meeting_id and not auto:
            self.stderr.write(
                self.style.ERROR("Pass either --meeting-id <N> or --auto.")
            )
            return
        if meeting_id and auto:
            self.stderr.write(
                self.style.ERROR("--meeting-id and --auto are mutually exclusive.")
            )
            return

        if auto:
            meetings = self._discover_unsent_meetings()
            if not meetings:
                self.stdout.write("No unsent published meetings — nothing to do.")
                return
            self.stdout.write(
                f"Found {len(meetings)} unsent meeting(s): "
                f"{', '.join(m.short_name for m in meetings)}"
            )
            for meeting in meetings:
                self._compose_for_meeting(meeting, dry_run=dry_run)
            return

        try:
            meeting = ParliamentaryMeeting.objects.get(pk=meeting_id)
        except ParliamentaryMeeting.DoesNotExist:
            self.stderr.write(
                self.style.ERROR(
                    f"ParliamentaryMeeting with ID {meeting_id} not found."
                )
            )
            return
        self._compose_for_meeting(meeting, dry_run=dry_run)

    def _discover_unsent_meetings(self):
        """Return published meetings without an existing PARLIAMENT_WATCH broadcast.

        Dedupe key: matching coverage_start_date + coverage_end_date on the
        Broadcast row. compose_parliament_watch sets these from the meeting's
        own start/end dates, so the check is exact and self-healing — if the
        DRAFT was deleted, the next run recomposes it.
        """
        sent_pairs = set(
            Broadcast.objects.filter(kind=Broadcast.Kind.PARLIAMENT_WATCH)
            .exclude(coverage_start_date__isnull=True)
            .values_list("coverage_start_date", "coverage_end_date")
        )
        candidates = (
            ParliamentaryMeeting.objects
            .filter(is_published=True, end_date__gte=AUTO_COMPOSE_START_DATE)
            .exclude(report_html="")
            .order_by("start_date")
        )
        return [
            m for m in candidates
            if (m.start_date, m.end_date) not in sent_pairs
        ]

    def _compose_for_meeting(self, meeting, *, dry_run: bool) -> None:
        digest = generate_parliament_digest(meeting)
        if digest is None:
            self.stderr.write(
                self.style.ERROR(
                    f"[{meeting.short_name}] Digest generation failed — "
                    "check report_html and GEMINI_API_KEY."
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

        hero_image_bytes = generate_hero_image(
            content_summary=digest["headlines"],
            style="parliament",
        )
        if hero_image_bytes:
            self.stdout.write(f"[{meeting.short_name}] Hero image generated")

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
            coverage_start_date=meeting.start_date,
            coverage_end_date=meeting.end_date,
            status=Broadcast.Status.DRAFT,
            hero_image=hero_image_bytes or b"",
        )

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
                f"[{meeting.short_name}] Draft broadcast created (ID: {broadcast.pk})"
            )
        )
