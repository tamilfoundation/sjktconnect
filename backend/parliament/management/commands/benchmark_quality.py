"""Benchmark current quality of all mentions, briefs, and reports.

Usage:
    python manage.py benchmark_quality --label pre-rebuild
    python manage.py benchmark_quality --label post-rebuild --mentions-only
"""

import json
import logging
import os
from datetime import datetime, timezone

from django.core.management.base import BaseCommand

from parliament.services.benchmark import (
    benchmark_briefs,
    benchmark_mentions,
    benchmark_reports,
    build_benchmark_report,
)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Snapshot quality of all mentions, briefs, and reports to a JSON benchmark file."

    def add_arguments(self, parser):
        parser.add_argument(
            "--label",
            required=True,
            help="Label for this benchmark run (e.g. pre-rebuild, post-rebuild-1st-2026)",
        )
        parser.add_argument(
            "--mentions-only",
            action="store_true",
            help="Only benchmark mentions (no Gemini API calls)",
        )
        parser.add_argument(
            "--output-dir",
            default="",
            help="Output directory (default: docs/quality/)",
        )

    def handle(self, **options):
        label = options["label"]
        mentions_only = options["mentions_only"]
        output_dir = options["output_dir"] or os.path.join(
            os.path.dirname(
                os.path.dirname(
                    os.path.dirname(
                        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                    )
                )
            ),
            "docs",
            "quality",
        )

        os.makedirs(output_dir, exist_ok=True)

        # 1. Mentions (deterministic — no API cost)
        self.stdout.write("Evaluating mentions (deterministic)...")
        mention_results = benchmark_mentions()
        self.stdout.write(f"  {len(mention_results)} mentions evaluated")

        # 2. Briefs and reports (Gemini API calls)
        brief_results = []
        report_results = []
        if not mentions_only:
            self.stdout.write("Evaluating briefs (Gemini API)...")
            brief_results = benchmark_briefs()
            self.stdout.write(f"  {len(brief_results)} briefs evaluated")

            self.stdout.write("Evaluating reports (Gemini API)...")
            report_results = benchmark_reports()
            self.stdout.write(f"  {len(report_results)} reports evaluated")

        # 3. Build and save
        report = build_benchmark_report(
            label=label,
            mention_results=mention_results,
            brief_results=brief_results,
            report_results=report_results,
        )

        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        filename = f"benchmark-{date_str}-{label}.json"
        filepath = os.path.join(output_dir, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        self.stdout.write(self.style.SUCCESS(f"Benchmark saved to {filepath}"))

        # Print summary
        summary = report["summary"]
        self.stdout.write("\n--- Summary ---")
        self.stdout.write(
            f"Mentions: {summary['mentions']['total']} total, "
            f"avg confidence {summary['mentions']['avg_confidence']}, "
            f"{summary['mentions']['with_warnings']} with warnings"
        )
        if brief_results:
            self.stdout.write(
                f"Briefs: {summary['briefs']['total']} total, "
                f"verdicts: {summary['briefs']['verdicts']}"
            )
        if report_results:
            self.stdout.write(
                f"Reports: {summary['reports']['total']} total, "
                f"verdicts: {summary['reports']['verdicts']}"
            )
