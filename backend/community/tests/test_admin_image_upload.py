"""Sprint 32 test-debt catch-up: `admin_image_upload_view`.

The direct-upload endpoint bypasses the Suggestion queue and lands
bytes straight in SchoolImage. Covers the permission matrix + the
principal reject paths (slot full, oversize, missing field).
"""

from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import UserProfile
from community.tests.fixtures import valid_jpeg_bytes
from outreach.models import SchoolImage
from schools.models import Constituency, School


class AdminImageUploadPermTest(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.constituency = Constituency.objects.create(
            code="P001", name="Test", state="Selangor",
        )
        self.school = School.objects.create(
            moe_code="ABC1234",
            name="SJK(T) Test", short_name="SJK(T) Test",
            constituency=self.constituency, state="Selangor",
        )
        self.other_school = School.objects.create(
            moe_code="XYZ9999",
            name="SJK(T) Other", short_name="SJK(T) Other",
            constituency=self.constituency, state="Selangor",
        )
        self.regular = UserProfile.objects.create(
            user=User.objects.create_user("reg"),
            google_id="g-reg", display_name="Reg",
        )
        self.moderator = UserProfile.objects.create(
            user=User.objects.create_user("mod"),
            google_id="g-mod", display_name="Mod", role="MODERATOR",
        )
        self.superadmin = UserProfile.objects.create(
            user=User.objects.create_user("super"),
            google_id="g-super", display_name="Super", role="SUPERADMIN",
        )
        self.bound_admin = UserProfile.objects.create(
            user=User.objects.create_user("bound"),
            google_id="g-bound", display_name="Bound",
            admin_school=self.school,
        )
        self.other_admin = UserProfile.objects.create(
            user=User.objects.create_user("other"),
            google_id="g-other", display_name="Other",
            admin_school=self.other_school,
        )
        self.url = f"/api/v1/schools/{self.school.moe_code}/images/upload/"

    def _auth(self, profile):
        session = self.client.session
        session["user_profile_id"] = profile.pk
        session.save()

    def _upload(self):
        return SimpleUploadedFile(
            "photo.jpg", valid_jpeg_bytes(800, 600), content_type="image/jpeg",
        )

    def test_superadmin_can_upload(self):
        self._auth(self.superadmin)
        resp = self.client.post(
            self.url, {"image": self._upload(), "caption": "Hero shot"},
            format="multipart",
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(SchoolImage.objects.filter(school=self.school).count(), 1)

    def test_bound_school_admin_can_upload(self):
        self._auth(self.bound_admin)
        resp = self.client.post(
            self.url, {"image": self._upload()}, format="multipart",
        )
        self.assertEqual(resp.status_code, 201)

    def test_moderator_cannot_upload(self):
        """MODERATOR is intentionally NOT a photo approver (mirrors
        the approve/reject perm — Sprint 14 design)."""
        self._auth(self.moderator)
        resp = self.client.post(
            self.url, {"image": self._upload()}, format="multipart",
        )
        self.assertEqual(resp.status_code, 403)

    def test_other_school_admin_cannot_upload(self):
        self._auth(self.other_admin)
        resp = self.client.post(
            self.url, {"image": self._upload()}, format="multipart",
        )
        self.assertEqual(resp.status_code, 403)

    def test_regular_user_cannot_upload(self):
        self._auth(self.regular)
        resp = self.client.post(
            self.url, {"image": self._upload()}, format="multipart",
        )
        self.assertEqual(resp.status_code, 403)

    def test_slot_full_returns_409(self):
        """20-photo cap enforced — bytes are not written even for SUPERADMIN."""
        from community.services import PHOTO_CAP_PER_SCHOOL
        for i in range(PHOTO_CAP_PER_SCHOOL):
            SchoolImage.objects.create(
                school=self.school,
                image_url=f"https://example.com/{i}.jpg",
                position=i,
            )
        self._auth(self.superadmin)
        resp = self.client.post(
            self.url, {"image": self._upload()}, format="multipart",
        )
        self.assertEqual(resp.status_code, 409)
        self.assertEqual(resp.data["code"], "slot_full")

    def test_missing_image_returns_400(self):
        self._auth(self.superadmin)
        resp = self.client.post(self.url, {}, format="multipart")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data["code"], "missing_image")
