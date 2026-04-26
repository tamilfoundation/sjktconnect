"""Sprint 15 — caption edit endpoint."""

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import UserProfile
from outreach.models import SchoolImage
from schools.models import Constituency, School


class ImageCaptionTest(TestCase):
    def setUp(self):
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
        self.image = SchoolImage.objects.create(
            school=self.school, source="PLACES",
            image_url="https://example.com/1.jpg", position=0,
        )
        self.regular = UserProfile.objects.create(
            user=User.objects.create_user("reg"),
            google_id="g-reg", display_name="Reg",
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
        self.url = f"/api/v1/schools/{self.school.moe_code}/images/{self.image.pk}/caption/"

    def _auth(self, profile):
        session = self.client.session
        session["user_profile_id"] = profile.pk
        session.save()

    def test_superadmin_can_set_caption(self):
        self._auth(self.superadmin)
        resp = self.client.patch(self.url, {"caption": "  Front gate at sunset  "}, format="json")
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertEqual(resp.data["caption"], "Front gate at sunset")
        self.image.refresh_from_db()
        self.assertEqual(self.image.caption, "Front gate at sunset")

    def test_bound_school_admin_can_set_caption(self):
        self._auth(self.bound_admin)
        resp = self.client.patch(self.url, {"caption": "Hari Sukan"}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.image.refresh_from_db()
        self.assertEqual(self.image.caption, "Hari Sukan")

    def test_other_school_admin_cannot_edit_caption(self):
        self._auth(self.other_admin)
        resp = self.client.patch(self.url, {"caption": "nope"}, format="json")
        self.assertEqual(resp.status_code, 403)
        self.image.refresh_from_db()
        self.assertEqual(self.image.caption, "")

    def test_regular_user_cannot_edit_caption(self):
        self._auth(self.regular)
        resp = self.client.patch(self.url, {"caption": "nope"}, format="json")
        self.assertEqual(resp.status_code, 403)

    def test_anonymous_cannot_edit_caption(self):
        resp = self.client.patch(self.url, {"caption": "nope"}, format="json")
        self.assertEqual(resp.status_code, 403)

    def test_caption_too_long_rejected(self):
        self._auth(self.superadmin)
        resp = self.client.patch(self.url, {"caption": "x" * 201}, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data["code"], "too_long")

    def test_caption_must_be_string(self):
        self._auth(self.superadmin)
        resp = self.client.patch(self.url, {"caption": 12345}, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_clearing_caption_with_empty_string(self):
        self.image.caption = "old"
        self.image.save()
        self._auth(self.superadmin)
        resp = self.client.patch(self.url, {"caption": ""}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.image.refresh_from_db()
        self.assertEqual(self.image.caption, "")
