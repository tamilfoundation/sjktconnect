"""Tests for migrate_images_to_storage management command."""

from io import StringIO
from unittest.mock import patch, MagicMock

from django.core.management import call_command
from django.test import TestCase

from outreach.models import SchoolImage
from schools.models import School


def _ok_response(payload: bytes = b"\x89PNG\r\n\x1a\n" + b"x" * 100):
    resp = MagicMock()
    resp.status_code = 200
    resp.raise_for_status = lambda: None
    resp.iter_content = lambda chunk_size=64 * 1024: [payload]
    return resp


def _bad_response():
    import requests
    raise requests.RequestException("dead")


class MigrateImagesCommandTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.school = School.objects.create(
            moe_code="JBD0050", name="SJK(T) Bikam", short_name="SJK(T) Bikam",
            state="Johor",
        )

    def setUp(self):
        # Two unmigrated images (image_url set, image_file empty)
        self.legacy = SchoolImage.objects.create(
            school=self.school, source="PLACES",
            image_url="https://places.googleapis.com/v1/places/X/photos/A/media?key=K",
        )
        self.legacy2 = SchoolImage.objects.create(
            school=self.school, source="SATELLITE",
            image_url="https://maps.googleapis.com/maps/api/staticmap?center=1,1&key=K",
        )

    def test_dry_run_does_not_upload(self):
        out = StringIO()
        with patch("outreach.management.commands.migrate_images_to_storage.requests.get") as mock_get:
            call_command("migrate_images_to_storage", "--dry-run", stdout=out)
            mock_get.assert_not_called()
        self.legacy.refresh_from_db()
        assert not self.legacy.image_file
        assert "would migrate" in out.getvalue().lower()

    def test_migrates_unmigrated_images(self):
        out = StringIO()
        with patch(
            "outreach.management.commands.migrate_images_to_storage.requests.get",
            return_value=_ok_response(),
        ):
            call_command("migrate_images_to_storage", stdout=out)

        self.legacy.refresh_from_db()
        self.legacy2.refresh_from_db()
        assert self.legacy.image_file
        assert self.legacy2.image_file
        assert "migrated=2" in out.getvalue()

    def test_skips_already_migrated(self):
        from django.core.files.base import ContentFile
        # Pre-migrate legacy
        self.legacy.image_file.save("existing.jpg", ContentFile(b"existing"), save=True)
        existing_name = self.legacy.image_file.name

        out = StringIO()
        with patch(
            "outreach.management.commands.migrate_images_to_storage.requests.get",
            return_value=_ok_response(),
        ) as mock_get:
            call_command("migrate_images_to_storage", stdout=out)
            # Only legacy2 should be downloaded
            assert mock_get.call_count == 1

        self.legacy.refresh_from_db()
        # Existing image_file unchanged
        assert self.legacy.image_file.name == existing_name

    def test_handles_dead_url(self):
        import requests
        out = StringIO()
        with patch(
            "outreach.management.commands.migrate_images_to_storage.requests.get",
            side_effect=requests.RequestException("404"),
        ):
            call_command("migrate_images_to_storage", stdout=out)

        self.legacy.refresh_from_db()
        assert not self.legacy.image_file
        assert "failed=2" in out.getvalue()

    def test_source_filter(self):
        out = StringIO()
        with patch(
            "outreach.management.commands.migrate_images_to_storage.requests.get",
            return_value=_ok_response(),
        ):
            call_command("migrate_images_to_storage", "--source", "PLACES", stdout=out)

        self.legacy.refresh_from_db()
        self.legacy2.refresh_from_db()
        assert self.legacy.image_file  # PLACES — migrated
        assert not self.legacy2.image_file  # SATELLITE — skipped
        assert "migrated=1" in out.getvalue()

    def test_no_unmigrated_images(self):
        SchoolImage.objects.all().delete()
        out = StringIO()
        call_command("migrate_images_to_storage", stdout=out)
        assert "Migrating 0 images" in out.getvalue()
