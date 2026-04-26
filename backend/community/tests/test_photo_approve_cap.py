"""Sprint 14 — 20-photo cap on PHOTO_UPLOAD approval + permission gate."""

from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.files.base import ContentFile
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import UserProfile
from community.models import Suggestion
from community.tests.fixtures import valid_png_bytes
from outreach.models import SchoolImage
from schools.models import Constituency, School


class PhotoApproveCapTest(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.constituency = Constituency.objects.create(
            code="P001", name="Test", state="Selangor",
        )
        self.school = School.objects.create(
            moe_code="ABC1234",
            name="SJK(T) Test",
            short_name="SJK(T) Test",
            constituency=self.constituency,
            state="Selangor",
        )
        self.uploader_user = User.objects.create_user("uploader")
        self.uploader = UserProfile.objects.create(
            user=self.uploader_user,
            google_id="google-up",
            display_name="Uploader",
        )
        self.super_user = User.objects.create_user("super")
        self.superadmin = UserProfile.objects.create(
            user=self.super_user,
            google_id="google-super",
            display_name="Super",
            role="SUPERADMIN",
        )

    def _auth(self, profile):
        session = self.client.session
        session["user_profile_id"] = profile.pk
        session.save()

    def _make_pending_photo_suggestion(self):
        s = Suggestion.objects.create(
            school=self.school,
            user=self.uploader,
            type="PHOTO_UPLOAD",
        )
        s.pending_image.save("p.png", ContentFile(valid_png_bytes()), save=True)
        return s

    def test_approve_under_cap_succeeds(self):
        for i in range(5):
            SchoolImage.objects.create(
                school=self.school, source="PLACES", position=i,
                image_url=f"https://example.com/{i}.jpg",
            )
        s = self._make_pending_photo_suggestion()
        self._auth(self.superadmin)
        resp = self.client.post(f"/api/v1/suggestions/{s.pk}/approve/")
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertEqual(SchoolImage.objects.filter(school=self.school).count(), 6)

    def test_approve_at_cap_returns_409(self):
        for i in range(20):
            SchoolImage.objects.create(
                school=self.school, source="PLACES", position=i,
                image_url=f"https://example.com/{i}.jpg",
            )
        s = self._make_pending_photo_suggestion()
        self._auth(self.superadmin)
        resp = self.client.post(f"/api/v1/suggestions/{s.pk}/approve/")
        self.assertEqual(resp.status_code, 409, resp.data)
        self.assertEqual(resp.data["code"], "slot_full")
        s.refresh_from_db()
        self.assertEqual(s.status, "PENDING")
        self.assertEqual(SchoolImage.objects.filter(school=self.school).count(), 20)

    def test_reject_deletes_pending_file(self):
        s = self._make_pending_photo_suggestion()
        original_path = s.pending_image.name
        self.assertTrue(original_path)

        self._auth(self.superadmin)
        resp = self.client.post(
            f"/api/v1/suggestions/{s.pk}/reject/",
            {"reason": "bad photo"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.data)
        s.refresh_from_db()
        self.assertEqual(s.status, "REJECTED")
        self.assertFalse(s.pending_image)  # cleared
