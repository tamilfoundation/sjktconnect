"""
Management command to find and send urgent news alerts automatically.

Finds approved urgent NewsArticles that haven't been broadcast yet,
composes an alert for each, and sends immediately.

Usage:
    python manage.py send_urgent_alerts
    python manage.py send_urgent_alerts --dry-run
"""

from django.core.management.base import BaseCommand
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from broadcasts.models import Broadcast
from broadcasts.services.sender import send_broadcast
from broadcasts.services.urgent_alert import generate_urgent_alert
from newswatch.models import NewsArticle


class Command(BaseCommand):
    help = "Find unsent urgent articles, compose alerts, and send them."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be sent without actually sending",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        # Find urgent approved articles not yet broadcast
        sent_subjects = set(
            Broadcast.objects.filter(
                subject__startswith="URGENT:",
            ).values_list("subject", flat=True)
        )

        urgent_articles = NewsArticle.objects.filter(
            is_urgent=True,
            review_status=NewsArticle.APPROVED,
        ).order_by("-created_at")

        unsent = [
            a for a in urgent_articles
            if f"URGENT: {a.title}" not in sent_subjects
        ]

        if not unsent:
            self.stdout.write("No unsent urgent articles found.")
            return

        self.stdout.write(f"Found {len(unsent)} unsent urgent article(s).")

        for article in unsent:
            self.stdout.write(f"  Processing: {article.title[:60]}...")

            alert = generate_urgent_alert(article)
            if alert is None:
                self.stderr.write(
                    self.style.ERROR(
                        f"  Failed to generate alert for article {article.pk}"
                    )
                )
                continue

            if dry_run:
                self.stdout.write(
                    f"  DRY RUN — would send: URGENT: {article.title[:60]}"
                )
                continue

            html_content = render_to_string(
                "broadcasts/news_watch_urgent.html",
                {
                    "article_title": article.title,
                    "source_name": article.source_name,
                    "published_date": article.published_date,
                    "what_happened": alert["what_happened"],
                    "who_affected": alert["who_affected"],
                    "what_you_can_do": alert["what_you_can_do"],
                    "deadline": alert.get("deadline"),
                },
            )

            broadcast = Broadcast.objects.create(
                subject=f"URGENT: {article.title}",
                html_content=html_content,
                text_content=strip_tags(html_content),
                audience_filter={"category": "NEWS_WATCH"},
                status=Broadcast.Status.DRAFT,
            )

            send_broadcast(broadcast.pk)
            self.stdout.write(
                self.style.SUCCESS(
                    f"  Sent broadcast {broadcast.pk}: URGENT: {article.title[:60]}"
                )
            )

        self.stdout.write(self.style.SUCCESS("Done."))
