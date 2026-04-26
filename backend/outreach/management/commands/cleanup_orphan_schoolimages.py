"""Delete orphan SchoolImage rows whose bytes were lost in the Sprint 14 cutover.

The Sprint 8.2 community-photo flow stored bytes in `Suggestion.image`
(BinaryField) and pointed `SchoolImage.image_url` at
`<BACKEND>/api/v1/suggestions/<pk>/image/`. Sprint 14 dropped both the
BinaryField AND the endpoint, so any SchoolImage rows from the old flow
that weren't migrated by Sprint 13's COMMUNITY pass now point at a 404
URL with no `image_file` to fall back to. Their bytes are unrecoverable
(BinaryField column was dropped).

This command finds those orphans and deletes the rows so the gallery
stops rendering broken images. The user can re-upload any photos they
want preserved via the new Sprint 14 multipart endpoint.

Usage:
    python manage.py cleanup_orphan_schoolimages --dry-run
    python manage.py cleanup_orphan_schoolimages --apply
"""

from django.core.management.base import BaseCommand
from django.db.models import Q

from outreach.models import SchoolImage


class Command(BaseCommand):
    help = "Delete SchoolImage rows orphaned by the Sprint 14 cutover."

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply", action="store_true",
            help="Actually delete the orphan rows. Default is dry-run.",
        )
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Print what would be deleted without changing anything (default).",
        )

    def handle(self, *args, **options):
        apply_changes = options["apply"]

        # An "orphan" has no image_file AND its image_url either points at the
        # dead /api/v1/suggestions/<pk>/image/ endpoint or is empty (so there's
        # nothing the frontend could render).
        orphans = SchoolImage.objects.filter(
            Q(image_file__isnull=True) | Q(image_file=""),
        ).filter(
            Q(image_url__contains="/api/v1/suggestions/") | Q(image_url=""),
        )

        total = orphans.count()
        self.stdout.write(f"Found {total} orphan SchoolImage row(s).")

        for img in orphans.values("pk", "school_id", "source", "image_url")[:100]:
            self.stdout.write(
                f"  pk={img['pk']} school={img['school_id']} "
                f"source={img['source']} url={img['image_url'][:80]!r}"
            )

        if total == 0:
            return

        if not apply_changes:
            self.stdout.write(self.style.WARNING(
                "Dry run — pass --apply to actually delete these rows."
            ))
            return

        deleted, _ = orphans.delete()
        self.stdout.write(self.style.SUCCESS(
            f"Deleted {deleted} orphan SchoolImage row(s)."
        ))
