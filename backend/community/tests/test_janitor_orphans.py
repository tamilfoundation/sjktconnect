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
