from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient

from accounts.models import UserProfile
from schools.models import School


class MeEndpointTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = "/api/v1/auth/me/"

    def test_unauthenticated_returns_401(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 401)

    def test_google_session_returns_profile(self):
        user = User.objects.create_user("guser", "g@gmail.com", "pass")
        profile = UserProfile.objects.create(
            user=user, google_id="g-123", display_name="Google User",
        )
        session = self.client.session
        session["user_profile_id"] = profile.id
        session.save()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["display_name"], "Google User")
        self.assertEqual(response.data["role"], "USER")

    def test_google_session_with_admin_school(self):
        school = School.objects.create(
            moe_code="XYZ0002", name="Admin School",
            short_name="SJK(T) Admin", state="Perak", ppd="Test",
        )
        user = User.objects.create_user("admin", "admin@moe.edu.my", "pass")
        profile = UserProfile.objects.create(
            user=user, google_id="g-admin", display_name="Admin",
            admin_school=school,
        )
        session = self.client.session
        session["user_profile_id"] = profile.id
        session.save()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["admin_school"]["moe_code"], "XYZ0002")

    def test_inactive_profile_returns_401(self):
        user = User.objects.create_user("inactive", "x@x.com", "pass")
        profile = UserProfile.objects.create(
            user=user, google_id="g-inactive", display_name="X", is_active=False,
        )
        session = self.client.session
        session["user_profile_id"] = profile.id
        session.save()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 401)
