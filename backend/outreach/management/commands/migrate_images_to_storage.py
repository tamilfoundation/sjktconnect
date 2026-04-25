"""One-shot migration: download bytes from each SchoolImage.image_url and
upload to Supabase Storage as image_file.

Idempotent + resumable:
- Skips rows that already have image_file set.
- Skips dead URLs (logs and moves on; a separate re-harvest will replace them).
- Commits every BATCH_SIZE images and closes the DB connection in between
  to avoid Supabase pooler write drops on long-running jobs.

Usage:
    python manage.py migrate_images_to_storage [--dry-run] [--source SATELLITE|PLACES|MANUAL|COMMUNITY]
"""

import logging
import uuid

import requests
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import connection
from django.db.models import Q

from outreach.models import SchoolImage

logger = logging.getLogger(__name__)

BATCH_SIZE = 50
MAX_IMAGE_BYTES = 5 * 1024 * 1024


def _download_bytes(url: str, *, timeout: int = 30) -> bytes | None:
    try:
        resp = requests.get(url, timeout=timeout, stream=True)
        resp.raise_for_status()
        chunks = []
        total = 0
        for chunk in resp.iter_content(chunk_size=64 * 1024):
            total += len(chunk)
            if total > MAX_IMAGE_BYTES:
                return None
            chunks.append(chunk)
        return b"".join(chunks)
    except requests.RequestException:
        return None


class Command(BaseCommand):
    help = "Download SchoolImage.image_url bytes and upload to Supabase Storage."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Print what would be migrated without uploading.",
        )
        parser.add_argument(
            "--source", default=None,
            help="Limit to a specific Source (SATELLITE / PLACES / MANUAL / COMMUNITY).",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        source = options["source"]

        # FileField is nullable on this model — empty rows can be either NULL
        # or empty string depending on how they were created.
        qs = SchoolImage.objects.filter(
            Q(image_file__isnull=True) | Q(image_file=""),
        ).exclude(image_url="")
        if source:
            qs = qs.filter(source=source)

        total = qs.count()
        self.stdout.write(f"Migrating {total} images "
                          f"({source or 'all sources'}, dry_run={dry_run})")

        if total == 0:
            return

        migrated = 0
        skipped = 0
        failed = 0
        batch = []

        for img in qs.iterator(chunk_size=BATCH_SIZE):
            url = img.image_url
            if not url or not url.startswith("http"):
                skipped += 1
                continue

            if dry_run:
                self.stdout.write(f"  [DRY] would migrate {img.pk} ({img.source}): {url[:80]}")
                continue

            data = _download_bytes(url)
            if data is None:
                failed += 1
                self.stdout.write(self.style.WARNING(
                    f"  [FAIL] {img.pk} ({img.source}): {url[:80]} — dead URL or oversize"
                ))
                continue

            ext = "png" if img.source == SchoolImage.Source.SATELLITE else "jpg"
            filename = f"{img.source.lower()}-{uuid.uuid4().hex[:12]}.{ext}"
            try:
                img.image_file.save(filename, ContentFile(data), save=True)
                migrated += 1
                self.stdout.write(f"  [OK ] {img.pk} ({img.source}) -> {img.image_file.name}")
            except Exception as e:  # noqa: BLE001
                failed += 1
                self.stdout.write(self.style.WARNING(
                    f"  [FAIL] {img.pk} ({img.source}): upload error {e}"
                ))

            batch.append(img.pk)
            if len(batch) >= BATCH_SIZE:
                # Avoid Supabase pooler dropping idle writes on long jobs
                connection.close()
                batch.clear()

        self.stdout.write(self.style.SUCCESS(
            f"Done. migrated={migrated} skipped={skipped} failed={failed}"
        ))
