"""Tests for the orphan-image janitor (Sprint 33 audit follow-up).

Covers the DB-tracked sweep; the untracked-Storage sweep is a thin
wrapper around `default_storage.listdir()` and is exercised
end-to-end in prod via the weekly cron.
"""

from io import StringIO

from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.core.management import call_command
from django.test import TestCase

from accounts.models import UserProfile
from community.models import Suggestion
from schools.models import Constituency, School


class JanitorOrphanImagesTest(TestCase):
    def setUp(self):
        self.constituency = Constituency.objects.create(
            code="P140", name="Segamat", state="Johor",
        )
        self.school = School.objects.create(
            moe_code="JBD0050",
            name="SJK(T) LADANG BIKAM",
            short_name="SJK(T) Ladang Bikam",
            state="Johor",
            constituency=self.constituency,
        )
        u = User.objects.create_user("uploader", "u@example.com", "x")
        self.user = UserProfile.objects.create(user=u)

    def _make_suggestion(self, status, attach_pending=True):
        s = Suggestion.objects.create(
            school=self.school,
            user=self.user,
            type=Suggestion.Type.PHOTO_UPLOAD,
            status=status,
        )
        if attach_pending:
            s.pending_image.save("test.jpg", ContentFile(b"fake bytes"), save=True)
        return s

    def test_sweeps_rejected_row_with_stuck_pending(self):
        s = self._make_suggestion(Suggestion.Status.REJECTED)
        self.assertTrue(s.pending_image)

        out = StringIO()
        call_command("janitor_orphan_images", stdout=out)

        s.refresh_from_db()
        self.assertFalse(s.pending_image)
        self.assertIn("1 deleted", out.getvalue())

    def test_sweeps_approved_row_with_stuck_pending(self):
        s = self._make_suggestion(Suggestion.Status.APPROVED)
        call_command("janitor_orphan_images", stdout=StringIO())
        s.refresh_from_db()
        self.assertFalse(s.pending_image)

    def test_pending_status_row_is_kept(self):
        """PENDING suggestions are in-flight — janitor must not touch them."""
        s = self._make_suggestion(Suggestion.Status.PENDING)
        call_command("janitor_orphan_images", stdout=StringIO())
        s.refresh_from_db()
        self.assertTrue(s.pending_image)

    def test_dry_run_deletes_nothing(self):
        s = self._make_suggestion(Suggestion.Status.REJECTED)
        out = StringIO()
        call_command("janitor_orphan_images", "--dry-run", stdout=out)
        s.refresh_from_db()
        self.assertTrue(s.pending_image)
        self.assertIn("dry-run", out.getvalue())

    def test_idempotent_second_run(self):
        s = self._make_suggestion(Suggestion.Status.REJECTED)
        call_command("janitor_orphan_images", stdout=StringIO())
        # Second run: nothing left to delete
        out = StringIO()
        call_command("janitor_orphan_images", stdout=out)
        self.assertIn("0 deleted", out.getvalue())

    def test_rejected_row_without_pending_is_ignored(self):
        s = self._make_suggestion(Suggestion.Status.REJECTED, attach_pending=False)
        out = StringIO()
        call_command("janitor_orphan_images", stdout=out)
        self.assertIn("0 deleted", out.getvalue())


class JanitorSchoolsUntrackedSweepTest(TestCase):
    """2026-07-04 follow-up: sweep `schools/` for keys with no SchoolImage
    row. Covers the delete_image_view Storage-blip case (silent-except
    fix landed in the same commit)."""

    def setUp(self):
        from schools.models import Constituency, School
        from outreach.models import SchoolImage
        self.constituency = Constituency.objects.create(
            code="P140", name="Segamat", state="Johor",
        )
        self.school = School.objects.create(
            moe_code="JBD0050", name="SJK(T) Test",
            short_name="SJK(T) Test", state="Johor",
            constituency=self.constituency,
        )
        # One live SchoolImage (its key MUST NOT be deleted).
        SchoolImage.objects.create(
            school=self.school,
            image_file="schools/JBD0050/live.jpg",
            source="COMMUNITY",
        )
        # Test uses a mock S3 client — real bucket isn't touched.
        self.deleted_keys = []

    def _mock_s3(self, keys_in_storage):
        """Return a mock S3 client that filters keys by the Prefix arg.

        The janitor calls list_objects_v2 twice — once for pending/, once
        for schools/. Each invocation must only see keys under its prefix.
        """
        from unittest.mock import MagicMock
        client = MagicMock()

        def paginator_paginate(**kwargs):
            prefix = kwargs.get("Prefix", "")
            matching = [k for k in keys_in_storage if k.startswith(prefix)]
            return [{"Contents": [{"Key": k} for k in matching]}]

        paginator = MagicMock()
        paginator.paginate.side_effect = paginator_paginate
        client.get_paginator.return_value = paginator
        client.delete_object.side_effect = lambda Bucket, Key: self.deleted_keys.append(Key)
        return client

    def test_sweep_deletes_untracked_key_keeps_live(self):
        from unittest.mock import patch
        client = self._mock_s3(keys_in_storage=[
            "schools/JBD0050/live.jpg",       # DB-tracked — must keep
            "schools/JBD0050/orphan.jpg",     # untracked — must delete
        ])
        out = StringIO()
        with patch(
            "community.management.commands.janitor_orphan_images.Command._get_s3",
            return_value=(client, "test-bucket"),
        ):
            call_command(
                "janitor_orphan_images", "--sweep-untracked", stdout=out,
            )
        # Live key kept; orphan deleted.
        self.assertEqual(self.deleted_keys, ["schools/JBD0050/orphan.jpg"])
        self.assertIn("Untracked schools/ orphans: 1 deleted", out.getvalue())

    def test_dry_run_deletes_nothing_in_untracked_sweep(self):
        from unittest.mock import patch
        client = self._mock_s3(keys_in_storage=[
            "schools/JBD0050/orphan.jpg",
        ])
        out = StringIO()
        with patch(
            "community.management.commands.janitor_orphan_images.Command._get_s3",
            return_value=(client, "test-bucket"),
        ):
            call_command(
                "janitor_orphan_images", "--sweep-untracked", "--dry-run",
                stdout=out,
            )
        self.assertEqual(self.deleted_keys, [])
        self.assertIn("dry-run", out.getvalue())

    def test_missing_credentials_skips_gracefully(self):
        """No SUPABASE_STORAGE_* env → warn and skip, don't crash."""
        from unittest.mock import patch
        out = StringIO()
        with patch(
            "community.management.commands.janitor_orphan_images.Command._get_s3",
            return_value=(None, None),
        ):
            call_command(
                "janitor_orphan_images", "--sweep-untracked", stdout=out,
            )
        self.assertIn(
            "Supabase Storage credentials not configured", out.getvalue(),
        )
