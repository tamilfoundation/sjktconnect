"""
Management command to compose an urgent News Watch alert broadcast.

Takes a NewsArticle flagged as urgent, generates action-focused content
via Gemini, renders it into an HTML email, and creates a DRAFT Broadcast
for admin review before sending.

Usage:
    python manage.py compose_urgent_alert --article-id 42
    python manage.py compose_urgent_alert --article-id 42 --dry-run
"""

from django.core.management.base import BaseCommand
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from broadcasts.models import Broadcast
from broadcasts.services.urgent_alert import generate_urgent_alert
from newswatch.models import NewsArticle


class Command(BaseCommand):
    help = "Compose an urgent News Watch alert as a DRAFT broadcast."

    def add_arguments(self, parser):
        parser.add_argument(
            "--article-id",
            type=int,
            required=True,
            help="Primary key of the urgent NewsArticle",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print what would be generated without creating a broadcast",
        )

    def handle(self, *args, **options):
        article_id = options["article_id"]
        dry_run = options["dry_run"]

        try:
            article = NewsArticle.objects.get(pk=article_id)
        except NewsArticle.DoesNotExist:
            self.stderr.write(
                self.style.ERROR(
                    f"NewsArticle with ID {article_id} not found."
                )
            )
            return

        if not article.is_urgent:
            self.stderr.write(
                self.style.ERROR(
                    f"Article {article_id} is not flagged as urgent."
                )
            )
            return

        alert = generate_urgent_alert(article)
        if alert is None:
            self.stderr.write(
                self.style.ERROR(
                    "Alert generation failed — check article status and GEMINI_API_KEY."
                )
            )
            return

        if dry_run:
            self.stdout.write(
                f"DRY RUN — Urgent Alert\n"
                f"  Article: {article.title}\n"
                f"  What happened: {alert['what_happened'][:80]}...\n"
                f"  Action: {alert['what_you_can_do'][:80]}...\n"
                f"  Deadline: {alert.get('deadline') or 'None'}"
            )
            return

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

        text_content = strip_tags(html_content)

        broadcast = Broadcast.objects.create(
            subject=f"URGENT: {article.title}",
            html_content=html_content,
            text_content=text_content,
            audience_filter={"category": "NEWS_WATCH"},
            status=Broadcast.Status.DRAFT,
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Draft urgent alert created (ID: {broadcast.pk}) for "
                f'"{article.title}"'
            )
        )
