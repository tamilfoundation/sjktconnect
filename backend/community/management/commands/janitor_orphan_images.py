"""Sweep orphaned pending-image files out of Supabase Storage.

Audit 2026-07-01 finding: `reject_suggestion` and `_apply_photo_upload`
delete the staged file with `try/except: pass`. When Storage returns
transient errors, the Suggestion row still advances (REJECTED / APPROVED)
but the bytes stay in `pending/<uuid>.jpg`. There was no janitor —
storage grew monotonically. This command IS the janitor.

Two sweeps:

1. **DB-tracked orphans** — Suggestion rows in REJECTED or APPROVED state
   whose `pending_image` field still resolves to a live Storage key.
   These are the "Storage delete failed" cases the logger.exception
   calls in community/services.py now flag. Safe to delete: the row
   already moved on and the bytes serve no purpose.

2. **Untracked orphans** (--sweep-untracked) — Storage keys under
   `pending/` with no Suggestion row referencing them. Happens if:
   - A Suggestion was hard-deleted (e.g. admin cleanup).
   - The upload endpoint wrote the file but the DB txn rolled back.
   This sweep is slower (lists Storage) and off by default.

Idempotent. `--dry-run` reports counts without deleting.

Wire as a weekly Cloud Run Job — see backend/scripts/update_jobs.sh
(sjktconnect-janitor-orphan-images, Sun 03:00 MYT).
"""

import logging

from django.core.management.base import BaseCommand

from community.models import Suggestion

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Delete orphaned pending-image files from Storage. Sweeps DB-tracked "
        "orphans by default; --sweep-untracked also lists Storage for keys "
        "with no Suggestion row."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Report counts without deleting.",
        )
        parser.add_argument(
            "--sweep-untracked", action="store_true",
            help=(
                "Also list Supabase Storage for pending/ keys with no "
                "Suggestion row. Slower — off by default."
            ),
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        sweep_untracked = options["sweep_untracked"]

        deleted, kept, failed = self._sweep_db_tracked(dry_run)
        self.stdout.write(
            self.style.SUCCESS(
                f"DB-tracked orphans: {deleted} deleted, {kept} kept, "
                f"{failed} failed{' (dry-run)' if dry_run else ''}"
            )
        )

        if sweep_untracked:
            u_deleted, u_kept, u_failed = self._sweep_untracked(dry_run)
            self.stdout.write(
                self.style.SUCCESS(
                    f"Untracked orphans: {u_deleted} deleted, {u_kept} kept, "
                    f"{u_failed} failed{' (dry-run)' if dry_run else ''}"
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

    def _sweep_untracked(self, dry_run):
        """List Storage's pending/ prefix and delete keys with no DB row.

        Uses django-storages boto3-compatible S3 client to enumerate
        Supabase Storage. Skips silently if the storage backend isn't
        configured (dev with local filesystem storage).
        """
        from django.core.files.storage import default_storage

        deleted = kept = failed = 0
        try:
            _, files = default_storage.listdir("pending/")
        except (NotImplementedError, AttributeError):
            self.stdout.write(
                self.style.WARNING(
                    "  untracked sweep: default_storage.listdir not supported "
                    "on this backend — skipping."
                )
            )
            return 0, 0, 0

        db_keys = set(
            Suggestion.objects
            .exclude(pending_image="").exclude(pending_image=None)
            .values_list("pending_image", flat=True)
        )
        # Storage keys are stored full-path in DB; strip the "pending/"
        # prefix on both sides for comparison.
        db_leafs = {k.split("pending/", 1)[-1] for k in db_keys if k}

        for leaf in files:
            if leaf in db_leafs:
                kept += 1
                continue

            key = f"pending/{leaf}"
            self.stdout.write(f"  untracked: {key}")
            if dry_run:
                deleted += 1
                continue

            try:
                default_storage.delete(key)
                deleted += 1
            except Exception:  # noqa: BLE001
                logger.exception("janitor: failed to delete untracked %s", key)
                failed += 1

        return deleted, kept, failed
