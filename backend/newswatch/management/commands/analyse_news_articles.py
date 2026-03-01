"""
Management command to analyse extracted news articles using Gemini AI.

Usage:
    python manage.py analyse_news_articles
    python manage.py analyse_news_articles --batch-size 20
"""

from django.core.management.base import BaseCommand

from newswatch.services.news_analyser import analyse_pending_articles


class Command(BaseCommand):
    help = "Analyse EXTRACTED news articles using Gemini Flash AI."

    def add_arguments(self, parser):
        parser.add_argument(
            "--batch-size",
            type=int,
            default=10,
            help="Maximum number of articles to analyse (default: 10).",
        )

    def handle(self, *args, **options):
        batch_size = options["batch_size"]
        self.stdout.write(f"Analysing up to {batch_size} extracted articles...")

        result = analyse_pending_articles(batch_size=batch_size)

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. Analysed: {result['analysed']}, "
                f"Failed: {result['failed']}, "
                f"Skipped: {result['skipped']}"
            )
        )

        # Flag urgent articles
        if result["analysed"] > 0:
            from newswatch.models import NewsArticle

            urgent_count = NewsArticle.objects.filter(
                is_urgent=True, review_status=NewsArticle.PENDING,
            ).count()
            if urgent_count:
                self.stdout.write(
                    self.style.WARNING(
                        f"URGENT: {urgent_count} article(s) flagged for rapid response!"
                    )
                )
