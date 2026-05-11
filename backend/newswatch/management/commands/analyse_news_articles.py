"""
Management command to analyse extracted news articles using Gemini AI.

Usage:
    python manage.py analyse_news_articles
    python manage.py analyse_news_articles --batch-size 20
    python manage.py analyse_news_articles --dry-run --url <URL>
"""

from django.core.management.base import BaseCommand

from newswatch.services.news_analyser import (
    analyse_article,
    analyse_pending_articles,
    is_blocklisted_url,
)


class Command(BaseCommand):
    help = "Analyse EXTRACTED news articles using Gemini Flash AI."

    def add_arguments(self, parser):
        parser.add_argument(
            "--batch-size",
            type=int,
            default=10,
            help="Maximum number of articles to analyse (default: 10).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help=(
                "Diagnose mode (Sprint 24 #1a): analyse without saving. "
                "Use with --url to test specific article URLs against the "
                "blocklist + Gemini relevance prompt; prints the score and "
                "decision without writing to the database."
            ),
        )
        parser.add_argument(
            "--url",
            action="append",
            default=[],
            help=(
                "URL to analyse in dry-run mode. Pass multiple times for "
                "multiple URLs. Requires --dry-run."
            ),
        )

    def handle(self, *args, **options):
        if options["dry_run"]:
            self._handle_dry_run(options["url"])
            return

        batch_size = options["batch_size"]
        self.stdout.write(f"Analysing up to {batch_size} extracted articles...")

        result = analyse_pending_articles(batch_size=batch_size)

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. Analysed: {result['analysed']}, "
                f"Failed: {result['failed']}, "
                f"Skipped: {result['skipped']}, "
                f"Blocklisted: {result['blocklisted']}"
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

    def _handle_dry_run(self, urls):
        """Diagnose-mode helper for Sprint 24 task #1a.

        Looks up each URL in NewsArticle, reports blocklist verdict, runs
        Gemini analysis if not blocklisted, and prints the would-be
        decision without persisting anything.
        """
        from newswatch.models import NewsArticle

        if not urls:
            self.stdout.write(self.style.ERROR(
                "--dry-run requires at least one --url <URL> argument."
            ))
            return

        for url in urls:
            self.stdout.write(self.style.MIGRATE_HEADING(f"\n=== {url} ==="))
            if is_blocklisted_url(url):
                self.stdout.write(self.style.WARNING(
                    "VERDICT: BLOCKLISTED — auto-REJECT (no Gemini call)."
                ))
                continue

            try:
                article = NewsArticle.objects.get(url=url)
            except NewsArticle.DoesNotExist:
                self.stdout.write(self.style.ERROR(
                    "Not found in NewsArticle table; cannot dry-run without "
                    "body text. Skipping."
                ))
                continue

            if not article.body_text.strip():
                self.stdout.write(self.style.WARNING(
                    "No body text extracted yet; cannot run Gemini. Skipping."
                ))
                continue

            analysis = analyse_article(article)
            if analysis is None:
                self.stdout.write(self.style.ERROR(
                    "Gemini analysis failed (returned None)."
                ))
                continue

            score = analysis["relevance_score"]
            decision = "APPROVE" if score and score >= 3 else "REJECT"
            self.stdout.write(
                f"Relevance: {score}/5 — would {decision}"
            )
            self.stdout.write(f"Sentiment: {analysis['sentiment']}")
            self.stdout.write(f"Summary: {analysis['summary']}")
            if analysis["is_urgent"]:
                self.stdout.write(self.style.WARNING(
                    f"URGENT: {analysis['urgent_reason']}"
                ))
