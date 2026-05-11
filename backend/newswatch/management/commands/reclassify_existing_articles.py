"""
Reclassify previously-analysed news articles under the Sprint 24 #1a
tightened triage rules (blocklist + stricter Gemini prompt).

Use case: after Sprint 24 deploys the new prompt + DOMAIN_BLOCKLIST,
run this once over April 2026's approved articles to bulk-reject the
off-topic real-estate listings that slipped through under the old
score-≥3 auto-approve rule.

Usage:
    # Preview what would change for April 2026 approved articles
    python manage.py reclassify_existing_articles \\
        --since 2026-04-01 --status APPROVED --dry-run

    # Apply (re-runs Gemini on each article; ~$0.001/article)
    python manage.py reclassify_existing_articles \\
        --since 2026-04-01 --status APPROVED
"""

from datetime import datetime, timezone

from django.core.management.base import BaseCommand, CommandError

from newswatch.services.news_analyser import (
    analyse_article,
    apply_analysis,
    is_blocklisted_url,
    reject_blocklisted,
)


class Command(BaseCommand):
    help = (
        "Re-run news triage (blocklist + tightened relevance prompt) over "
        "previously-analysed articles to bulk-reject the off-topic ones."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--since",
            type=str,
            required=True,
            help="ISO date (YYYY-MM-DD); only articles created on or after this date are processed.",
        )
        parser.add_argument(
            "--status",
            type=str,
            default="APPROVED",
            choices=["APPROVED", "REJECTED", "PENDING", "ALL"],
            help="Filter by current review_status (default: APPROVED).",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=200,
            help="Max articles to process in one run (default: 200).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview changes without writing to the database.",
        )

    def handle(self, *args, **options):
        from newswatch.models import NewsArticle

        try:
            since = datetime.strptime(options["since"], "%Y-%m-%d").replace(
                tzinfo=timezone.utc,
            )
        except ValueError as exc:
            raise CommandError(f"Invalid --since date: {exc}")

        qs = NewsArticle.objects.filter(
            created_at__gte=since,
            status=NewsArticle.ANALYSED,
        )
        if options["status"] != "ALL":
            qs = qs.filter(review_status=options["status"])
        qs = qs.order_by("created_at")[:options["batch_size"]]

        total = qs.count()
        self.stdout.write(self.style.MIGRATE_HEADING(
            f"Reclassifying {total} article(s) with status={options['status']} "
            f"since {options['since']}{' [DRY RUN]' if options['dry_run'] else ''}"
        ))

        counts = {
            "blocklisted": 0,
            "downgraded": 0,
            "kept_approved": 0,
            "still_rejected": 0,
            "failed": 0,
        }

        for article in qs:
            prev_status = article.review_status
            prev_score = article.relevance_score

            if is_blocklisted_url(article.url):
                counts["blocklisted"] += 1
                self.stdout.write(
                    f"  BLOCKLIST: {article.url[:80]} "
                    f"(was {prev_status}, score={prev_score})"
                )
                if not options["dry_run"]:
                    reject_blocklisted(article)
                continue

            if not article.body_text.strip():
                counts["failed"] += 1
                self.stdout.write(self.style.WARNING(
                    f"  NO BODY: {article.url[:80]} (skipped)"
                ))
                continue

            analysis = analyse_article(article)
            if analysis is None:
                counts["failed"] += 1
                self.stdout.write(self.style.ERROR(
                    f"  GEMINI FAIL: {article.url[:80]}"
                ))
                continue

            new_score = analysis["relevance_score"]
            new_status = "APPROVED" if new_score and new_score >= 3 else "REJECTED"

            if new_status == "APPROVED":
                counts["kept_approved"] += 1
                msg_style = self.style.SUCCESS
                tag = "KEEP"
            elif prev_status == "APPROVED":
                counts["downgraded"] += 1
                msg_style = self.style.WARNING
                tag = "DOWNGRADE"
            else:
                counts["still_rejected"] += 1
                msg_style = self.style.HTTP_INFO
                tag = "STILL REJ"

            self.stdout.write(msg_style(
                f"  {tag}: {article.title[:60]} "
                f"({prev_score}→{new_score})"
            ))

            if not options["dry_run"]:
                apply_analysis(article, analysis)

        self.stdout.write(self.style.MIGRATE_HEADING("\n=== Summary ==="))
        self.stdout.write(f"Blocklisted (auto-rejected): {counts['blocklisted']}")
        self.stdout.write(f"Downgraded to REJECTED: {counts['downgraded']}")
        self.stdout.write(f"Kept APPROVED: {counts['kept_approved']}")
        self.stdout.write(f"Still REJECTED (no change): {counts['still_rejected']}")
        self.stdout.write(f"Failed: {counts['failed']}")
        if options["dry_run"]:
            self.stdout.write(self.style.WARNING(
                "\nDry run — no database changes were made."
            ))
