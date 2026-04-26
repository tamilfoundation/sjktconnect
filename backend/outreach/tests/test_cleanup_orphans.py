"""Sprint 14 hotfix — cleanup_orphan_schoolimages command."""

from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from outreach.models import SchoolImage
from schools.models import Constituency, School


class CleanupOrphanSchoolImagesTest(TestCase):
    def setUp(self):
        self.constituency = Constituency.objects.create(
            code="P001", name="Test", state="Selangor",
        )
        self.school = School.objects.create(
            moe_code="ABC1234",
            name="SJK(T) Test", short_name="SJK(T) Test",
            constituency=self.constituency, state="Selangor",
        )
        # Three orphans (Sprint 8.2 era — image_url points at the now-dead
        # /api/v1/suggestions/<pk>/image/ endpoint, no image_file backup).
        for i in range(3):
            SchoolImage.objects.create(
                school=self.school,
                source="COMMUNITY",
                image_url=f"https://api.example.com/api/v1/suggestions/{i+1}/image/",
                image_file="",
                position=i,
            )
        # One orphan with empty URL too.
        SchoolImage.objects.create(
            school=self.school, source="COMMUNITY",
            image_url="", image_file="", position=3,
        )
        # A healthy PLACES row — image_file is empty but image_url is a real
        # external URL that still works. Cleanup must NOT touch this.
        SchoolImage.objects.create(
            school=self.school, source="PLACES",
            image_url="https://example.com/places/photo.jpg",
            image_file="", position=4,
        )
        # A healthy migrated row — image_file set. Cleanup must NOT touch this.
        SchoolImage.objects.create(
            school=self.school, source="COMMUNITY",
            image_url="",
            image_file="schools/ABC1234/migrated.jpg",
            position=5,
        )

    def test_dry_run_does_not_delete(self):
        out = StringIO()
        call_command("cleanup_orphan_schoolimages", "--dry-run", stdout=out)
        self.assertIn("Found 4 orphan", out.getvalue())
        self.assertIn("Dry run", out.getvalue())
        self.assertEqual(SchoolImage.objects.count(), 6)

    def test_apply_deletes_only_orphans(self):
        out = StringIO()
        call_command("cleanup_orphan_schoolimages", "--apply", stdout=out)
        self.assertIn("Deleted 4", out.getvalue())
        # The PLACES row + the migrated COMMUNITY row remain.
        remaining = list(SchoolImage.objects.values_list("source", "image_file"))
        self.assertEqual(len(remaining), 2)
        self.assertIn(("PLACES", ""), remaining)
        self.assertIn(("COMMUNITY", "schools/ABC1234/migrated.jpg"), remaining)

    def test_idempotent(self):
        call_command("cleanup_orphan_schoolimages", "--apply", stdout=StringIO())
        out = StringIO()
        call_command("cleanup_orphan_schoolimages", "--apply", stdout=out)
        self.assertIn("Found 0 orphan", out.getvalue())
