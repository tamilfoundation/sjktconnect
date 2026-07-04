"""Sweep orphaned image files out of Supabase Storage.

Audit 2026-07-01 finding: `reject_suggestion` and `_apply_photo_upload`
delete the staged file with `try/except: pass`. When Storage returns
transient errors, the Suggestion row still advances (REJECTED / APPROVED)
but the bytes stay in `pending/<uuid>.jpg`. Sprint 33 shipped this
janitor for `pending/`; a 2026-07-04 follow-up extended it to also
sweep `schools/` after the same silent-except pattern was found in
`delete_image_view` (community/api/views.py).

Three sweeps:

1. **DB-tracked pending orphans** — Suggestion rows in REJECTED or
   APPROVED state whose `pending_image` field still resolves to a live
   Storage key. Safe to delete: the row already moved on.

2. **Untracked pending orphans** (--sweep-untracked) — Storage keys
   under `pending/` with no Suggestion row referencing them.

3. **Untracked schools orphans** (--sweep-untracked) — Storage keys
   under `schools/<moe>/` with no SchoolImage row. Covers the
   delete_image_view Storage-blip case.

Uses boto3 directly for the untracked sweeps because
`default_storage.listdir()` on Supabase Storage does NOT paginate — a
2026-07-04 diagnostic against prod showed listdir returning only ~3 of
528 subdirs. boto3's `list_objects_v2` paginator handles it correctly.

Idempotent. `--dry-run` reports counts without deleting.

Wire as a weekly Cloud Run Job — see backend/scripts/update_jobs.sh
(sjktconnect-janitor-orphan-images, Sun 03:00 MYT).
"""

import logging
import os

from django.core.management.base import BaseCommand

from community.models import Suggestion
from outreach.models import SchoolImage

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Delete orphaned image files from Storage. Sweeps DB-tracked "
        "pending/ orphans by default; --sweep-untracked also lists Storage "
        "for pending/ and schools/ keys with no DB row."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Report counts without deleting.",
        )
        parser.add_argument(
            "--sweep-untracked", action="store_true",
            help=(
                "Also list Supabase Storage for pending/ and schools/ keys "
                "with no DB row. Slower — off by default."
            ),
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        sweep_untracked = options["sweep_untracked"]

        deleted, kept, failed = self._sweep_db_tracked(dry_run)
        self.stdout.write(
            self.style.SUCCESS(
                f"DB-tracked pending orphans: {deleted} deleted, {kept} kept, "
                f"{failed} failed{' (dry-run)' if dry_run else ''}"
            )
        )

        if sweep_untracked:
            client, bucket = self._get_s3()
            if client is None:
                self.stdout.write(
                    self.style.WARNING(
                        "  untracked sweep: Supabase Storage credentials not "
                        "configured — skipping."
                    )
                )
                return

            u_deleted, u_kept, u_failed = self._sweep_untracked_prefix(
                client, bucket, "pending/", _pending_db_keys(), dry_run,
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"Untracked pending/ orphans: {u_deleted} deleted, "
                    f"{u_kept} kept, {u_failed} failed"
                    f"{' (dry-run)' if dry_run else ''}"
                )
            )

            s_deleted, s_kept, s_failed = self._sweep_untracked_prefix(
                client, bucket, "schools/", _schools_db_keys(), dry_run,
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"Untracked schools/ orphans: {s_deleted} deleted, "
                    f"{s_kept} kept, {s_failed} failed"
                    f"{' (dry-run)' if dry_run else ''}"
                )
            )

    def _sweep_db_tracked(self, dry_run):
        """Delete pending_image files still attached to non-PENDING rows."""
        deleted = kept = failed = 0
        qs = Suggestion.objects.filter(
            status__in=[Suggestion.Status.APPROVED, Suggestion.Status.REJECTED],
        ).exclude(pending_image="").exclude(pending_image=None)

        for suggestion in qs.iterator(chunk_size=200):
            name = suggestion.pending_image.name if suggestion.pending_image else ""
            if not name:
                kept += 1
                continue

            self.stdout.write(f"  orphan: suggestion {suggestion.pk} -> {name}")
            if dry_run:
                deleted += 1
                continue

            try:
                suggestion.pending_image.delete(save=False)
                # Clear the field explicitly so the row no longer references
                # the deleted key on re-runs.
                suggestion.pending_image = None
                suggestion.save(update_fields=["pending_image", "updated_at"])
                deleted += 1
            except Exception:  # noqa: BLE001
                logger.exception(
                    "janitor: failed to delete %s (suggestion %s)",
                    name, suggestion.pk,
                )
                failed += 1

        return deleted, kept, failed

    def _get_s3(self):
        """Return a boto3 S3 client + bucket name, or (None, None) if the
        Supabase Storage env vars aren't configured (dev with local FS).
        """
        endpoint = os.environ.get("SUPABASE_STORAGE_ENDPOINT")
        access = os.environ.get("SUPABASE_STORAGE_ACCESS_KEY")
        secret = os.environ.get("SUPABASE_STORAGE_SECRET_KEY")
        bucket = os.environ.get("SUPABASE_STORAGE_BUCKET")
        if not all((endpoint, access, secret, bucket)):
            return None, None

        import boto3
        from botocore.client import Config
        client = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=access,
            aws_secret_access_key=secret,
            region_name=os.environ.get("SUPABASE_STORAGE_REGION", "ap-southeast-1"),
            config=Config(signature_version="s3v4"),
        )
        return client, bucket

    def _sweep_untracked_prefix(self, client, bucket, prefix, db_keys, dry_run):
        """List `prefix` fully-paginated and delete keys not in `db_keys`.

        Diagnostic 2026-07-04: on Supabase Storage's S3-compat layer,
        `default_storage.listdir()` returned only 3 subdirs when the
        bucket held 528 (all real schools). boto3's paginator handles
        pagination correctly, so untracked sweeps go via this path.
        """
        deleted = kept = failed = 0
        paginator = client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                key = obj["Key"]
                if key in db_keys:
                    kept += 1
                    continue

                self.stdout.write(f"  untracked: {key}")
                if dry_run:
                    deleted += 1
                    continue

                try:
                    client.delete_object(Bucket=bucket, Key=key)
                    deleted += 1
                except Exception:  # noqa: BLE001
                    logger.exception("janitor: failed to delete untracked %s", key)
                    failed += 1

        return deleted, kept, failed


def _pending_db_keys():
    return set(
        Suggestion.objects
        .exclude(pending_image="").exclude(pending_image=None)
        .values_list("pending_image", flat=True)
    )


def _schools_db_keys():
    return set(
        SchoolImage.objects
        .exclude(image_file="").exclude(image_file=None)
        .values_list("image_file", flat=True)
    )
