"""
Management command to extract body text from pending news articles.

Usage:
    python manage.py extract_articles
    python manage.py extract_articles --batch-size 50
"""

from django.core.management.base import BaseCommand

from newswatch.services.article_extractor import extract_pending_articles


class Command(BaseCommand):
    help = "Extract body text from pending (NEW) news articles using trafilatura."

    def add_arguments(self, parser):
        parser.add_argument(
            "--batch-size",
            type=int,
            default=20,
            help="Maximum number of articles to process (default: 20).",
        )

    def handle(self, *args, **options):
        batch_size = options["batch_size"]
        self.stdout.write(f"Extracting up to {batch_size} pending articles...")

        result = extract_pending_articles(batch_size=batch_size)

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. Extracted: {result['extracted']}, "
                f"Failed: {result['failed']}, "
                f"Total processed: {result['total']}"
            )
        )
