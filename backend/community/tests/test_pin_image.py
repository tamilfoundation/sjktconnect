"""Sprint 14 — pin/hero endpoint."""

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import UserProfile
from outreach.models import SchoolImage
from schools.models import Constituency, School


class PinImageTest(TestCase):
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

        self.img1 = SchoolImage.objects.create(
            school=self.school, source="PLACES", position=0, is_primary=True,
            image_url="https://example.com/1.jpg",
        )
        self.img2 = SchoolImage.objects.create(
            school=self.school, source="PLACES", position=1, is_primary=False,
            image_url="https://example.com/2.jpg",
        )
        self.img3 = SchoolImage.objects.create(
            school=self.school, source="PLACES", position=2, is_primary=False,
            image_url="https://example.com/3.jpg",
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

    def _auth(self, profile):
        session = self.client.session
        session["user_profile_id"] = profile.pk
        session.save()

    def _pin(self, image):
        return self.client.post(
            f"/api/v1/schools/{self.school.moe_code}/images/{image.pk}/pin/"
        )

    def test_superadmin_can_pin(self):
        self._auth(self.superadmin)
        resp = self._pin(self.img2)
        self.assertEqual(resp.status_code, 200, resp.data)
        self.img1.refresh_from_db()
        self.img2.refresh_from_db()
        self.img3.refresh_from_db()
        self.assertFalse(self.img1.is_primary)
        self.assertTrue(self.img2.is_primary)
        self.assertFalse(self.img3.is_primary)

    def test_bound_school_admin_can_pin(self):
        self._auth(self.bound_admin)
        resp = self._pin(self.img3)
        self.assertEqual(resp.status_code, 200, resp.data)
        self.img1.refresh_from_db()
        self.img3.refresh_from_db()
        self.assertFalse(self.img1.is_primary)
        self.assertTrue(self.img3.is_primary)

    def test_other_school_admin_cannot_pin(self):
        self._auth(self.other_admin)
        resp = self._pin(self.img2)
        self.assertEqual(resp.status_code, 403)

    def test_regular_user_cannot_pin(self):
        self._auth(self.regular)
        resp = self._pin(self.img2)
        self.assertEqual(resp.status_code, 403)

    def test_anonymous_cannot_pin(self):
        resp = self._pin(self.img2)
        self.assertEqual(resp.status_code, 403)

    def test_pinning_clears_other_primaries(self):
        # Hand-set img2 also as primary to test the unset path
        SchoolImage.objects.filter(pk=self.img2.pk).update(is_primary=True)
        self._auth(self.superadmin)
        self._pin(self.img3)
        primaries = SchoolImage.objects.filter(school=self.school, is_primary=True)
        self.assertEqual(primaries.count(), 1)
        self.assertEqual(primaries.first().pk, self.img3.pk)

    def test_image_not_in_school_returns_404(self):
        # Image attached to a different school; pin URL targets self.school
        foreign = SchoolImage.objects.create(
            school=self.other_school, source="PLACES", position=0,
            image_url="https://example.com/foreign.jpg",
        )
        self._auth(self.superadmin)
        resp = self.client.post(
            f"/api/v1/schools/{self.school.moe_code}/images/{foreign.pk}/pin/"
        )
        self.assertEqual(resp.status_code, 404)
