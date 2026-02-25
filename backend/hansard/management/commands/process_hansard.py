"""Management command to process a Hansard PDF through the full pipeline.

Usage:
    python manage.py process_hansard <url>
    python manage.py process_hansard <url> --sitting-date 2026-02-20
    python manage.py process_hansard <url> --catalogue-variants

The pipeline:
1. Download PDF from URL
2. Extract text (page by page) with pdfplumber
3. Normalise text
4. Search for Tamil school keywords
5. Store HansardSitting + HansardMention records
6. Match mentions to schools (alias table + trigram similarity)
"""

import re
import tempfile
from collections import Counter
from datetime import date

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from hansard.models import HansardMention, HansardSitting, SchoolAlias
from hansard.pipeline.downloader import download_hansard
from hansard.pipeline.extractor import extract_text
from hansard.pipeline.keywords import get_all_keywords
from hansard.pipeline.matcher import match_mentions
from hansard.pipeline.searcher import search_keywords


class Command(BaseCommand):
    help = "Process a Hansard PDF: download, extract text, search for Tamil school mentions."

    def add_arguments(self, parser):
        parser.add_argument("url", help="URL to the Hansard PDF file")
        parser.add_argument(
            "--sitting-date",
            type=str,
            help="Sitting date (YYYY-MM-DD). If not provided, attempts to extract from filename.",
        )
        parser.add_argument(
            "--catalogue-variants",
            action="store_true",
            help="Print a catalogue of raw keyword variants found (for Sprint 0.3 matching design).",
        )
        parser.add_argument(
            "--dest-dir",
            type=str,
            default="",
            help="Directory to save downloaded PDF. Defaults to temp directory.",
        )
        parser.add_argument(
            "--skip-matching",
            action="store_true",
            help="Skip school name matching (useful if no aliases seeded yet).",
        )

    def handle(self, *args, **options):
        url = options["url"]
        catalogue = options["catalogue_variants"]

        # Step 1: Determine sitting date
        sitting_date = self._resolve_sitting_date(options["sitting_date"], url)
        self.stdout.write(f"Sitting date: {sitting_date}")

        # Check if already processed
        existing = HansardSitting.objects.filter(sitting_date=sitting_date).first()
        if existing and existing.status == HansardSitting.Status.COMPLETED:
            self.stdout.write(self.style.WARNING(
                f"Sitting {sitting_date} already processed ({existing.mention_count} mentions). "
                "Delete the record to reprocess."
            ))
            return

        # Step 2: Create or update sitting record
        sitting, _ = HansardSitting.objects.update_or_create(
            sitting_date=sitting_date,
            defaults={
                "pdf_url": url,
                "pdf_filename": url.split("/")[-1],
                "status": HansardSitting.Status.PROCESSING,
            },
        )

        try:
            # Step 3: Download PDF
            dest_dir = options["dest_dir"] or tempfile.mkdtemp(prefix="hansard_")
            self.stdout.write(f"Downloading to {dest_dir}...")
            pdf_path = download_hansard(url, dest_dir)
            self.stdout.write(self.style.SUCCESS(f"Downloaded: {pdf_path.name}"))

            # Step 4: Extract text
            self.stdout.write("Extracting text...")
            pages = extract_text(pdf_path)
            sitting.total_pages = len(pages)
            sitting.save(update_fields=["total_pages"])
            self.stdout.write(f"Extracted {len(pages)} pages")

            # Step 5: Search keywords
            keywords = get_all_keywords()
            self.stdout.write(f"Searching {len(keywords)} keywords...")
            matches = search_keywords(pages, keywords)
            self.stdout.write(f"Found {len(matches)} matches")

            # Step 6: Store mentions
            # Delete any previous mentions for this sitting (in case of reprocess)
            sitting.mentions.all().delete()

            mentions = []
            for match in matches:
                mentions.append(HansardMention(
                    sitting=sitting,
                    page_number=match["page_number"],
                    verbatim_quote=match["verbatim_quote"],
                    context_before=match["context_before"],
                    context_after=match["context_after"],
                    keyword_matched=match["keyword_matched"],
                ))
            HansardMention.objects.bulk_create(mentions)

            # Update sitting record
            sitting.mention_count = len(mentions)
            sitting.processed_at = timezone.now()
            sitting.status = HansardSitting.Status.COMPLETED
            sitting.save(update_fields=["mention_count", "processed_at", "status"])

            self.stdout.write(self.style.SUCCESS(
                f"Done! {len(mentions)} mentions stored for sitting {sitting_date}."
            ))

            # Step 7: Match mentions to schools
            if not options["skip_matching"] and SchoolAlias.objects.exists():
                self.stdout.write("Matching mentions to schools...")
                mention_qs = HansardMention.objects.filter(sitting=sitting)
                result = match_mentions(mention_qs)
                self.stdout.write(
                    f"  Matched: {result['matched']}/{result['total']}, "
                    f"needs review: {result['needs_review']}"
                )
            elif not options["skip_matching"]:
                self.stdout.write(self.style.WARNING(
                    "No school aliases found. Run 'seed_aliases' first, "
                    "or use --skip-matching."
                ))

            # Step 8: Catalogue variants (optional)
            if catalogue:
                self._print_variant_catalogue(matches)

        except Exception as e:
            sitting.status = HansardSitting.Status.FAILED
            sitting.error_message = str(e)
            sitting.save(update_fields=["status", "error_message"])
            raise CommandError(f"Pipeline failed: {e}") from e

    def _resolve_sitting_date(self, date_str: str | None, url: str) -> date:
        """Resolve sitting date from argument or URL filename."""
        if date_str:
            try:
                return date.fromisoformat(date_str)
            except ValueError as e:
                raise CommandError(f"Invalid date format: {date_str}. Use YYYY-MM-DD.") from e

        # Try to extract date from URL filename
        # Common patterns: DR-20022026.pdf, DR20022026.pdf, 2026-02-20.pdf
        filename = url.split("/")[-1]

        # Pattern: DDMMYYYY
        match = re.search(r"(\d{2})(\d{2})(\d{4})", filename)
        if match:
            day, month, year = match.groups()
            try:
                return date(int(year), int(month), int(day))
            except ValueError:
                pass

        # Pattern: YYYY-MM-DD
        match = re.search(r"(\d{4})-(\d{2})-(\d{2})", filename)
        if match:
            year, month, day = match.groups()
            try:
                return date(int(year), int(month), int(day))
            except ValueError:
                pass

        raise CommandError(
            f"Cannot extract date from filename '{filename}'. "
            "Please provide --sitting-date YYYY-MM-DD."
        )

    def _print_variant_catalogue(self, matches: list[dict]):
        """Print a catalogue of raw keyword variants found in the text."""
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("VARIANT CATALOGUE (raw forms found in Hansard)")
        self.stdout.write("=" * 60)

        variant_counts = Counter()
        for match in matches:
            # Get the raw text around the keyword match
            quote = match["verbatim_quote"]
            variant_counts[match["keyword_matched"]] += 1

        for variant, count in variant_counts.most_common():
            self.stdout.write(f"  {variant}: {count} occurrences")

        self.stdout.write(f"\nTotal unique keywords matched: {len(variant_counts)}")
        self.stdout.write(f"Total mentions: {sum(variant_counts.values())}")
        self.stdout.write("=" * 60)
