from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import UserProfile
from outreach.models import SchoolImage
from schools.models import Constituency, School


class ImageManagementAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.constituency = Constituency.objects.create(code="P001", name="Test", state="Selangor")
        self.school = School.objects.create(
            moe_code="ABC1234", name="SJK(T) Test", short_name="SJK(T) Test",
            constituency=self.constituency, state="Selangor",
        )
        self.admin_user = User.objects.create_user("admin")
        self.admin_profile = UserProfile.objects.create(
            user=self.admin_user, google_id="google-admin", display_name="Admin",
            admin_school=self.school,
        )
        self.regular_user = User.objects.create_user("regular")
        self.regular_profile = UserProfile.objects.create(
            user=self.regular_user, google_id="google-reg", display_name="Regular",
        )

    def _auth(self, profile):
        session = self.client.session
        session["user_profile_id"] = profile.pk
        session.save()

    def test_list_images(self):
        SchoolImage.objects.create(
            school=self.school, image_url="https://example.com/1.jpg",
            source="SATELLITE", position=0,
        )
        resp = self.client.get("/api/v1/schools/ABC1234/images/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 1)

    def test_reorder_images(self):
        self._auth(self.admin_profile)
        img1 = SchoolImage.objects.create(
            school=self.school, image_url="https://example.com/1.jpg",
            source="MANUAL", position=0,
        )
        img2 = SchoolImage.objects.create(
            school=self.school, image_url="https://example.com/2.jpg",
            source="MANUAL", position=1,
        )
        resp = self.client.put(
            "/api/v1/schools/ABC1234/images/reorder/",
            {"order": [img2.pk, img1.pk]},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        img1.refresh_from_db()
        img2.refresh_from_db()
        self.assertEqual(img2.position, 0)
        self.assertEqual(img1.position, 1)

    def test_delete_image(self):
        self._auth(self.admin_profile)
        img = SchoolImage.objects.create(
            school=self.school, image_url="https://example.com/1.jpg",
            source="MANUAL",
        )
        resp = self.client.delete(f"/api/v1/schools/ABC1234/images/{img.pk}/")
        self.assertEqual(resp.status_code, 204)
        self.assertEqual(SchoolImage.objects.count(), 0)

    def test_reorder_forbidden_for_non_admin(self):
        self._auth(self.regular_profile)
        resp = self.client.put(
            "/api/v1/schools/ABC1234/images/reorder/",
            {"order": []},
            format="json",
        )
        self.assertEqual(resp.status_code, 403)

    def test_delete_forbidden_for_non_admin(self):
        self._auth(self.regular_profile)
        img = SchoolImage.objects.create(
            school=self.school, image_url="https://example.com/1.jpg",
            source="MANUAL",
        )
        resp = self.client.delete(f"/api/v1/schools/ABC1234/images/{img.pk}/")
        self.assertEqual(resp.status_code, 403)

    def test_superadmin_can_manage_any_school(self):
        su_user = User.objects.create_user("super")
        su_profile = UserProfile.objects.create(
            user=su_user, google_id="google-su", display_name="Super", role="SUPERADMIN",
        )
        self._auth(su_profile)
        img = SchoolImage.objects.create(
            school=self.school, image_url="https://example.com/1.jpg", source="MANUAL",
        )
        resp = self.client.delete(f"/api/v1/schools/ABC1234/images/{img.pk}/")
        self.assertEqual(resp.status_code, 204)
