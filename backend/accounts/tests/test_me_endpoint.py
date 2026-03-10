from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from accounts.models import UserProfile, SchoolContact
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

    def test_magic_link_session_still_works(self):
        """Backward compatibility: existing magic link sessions still return data."""
        school = School.objects.create(
            moe_code="XYZ0001", name="Test School",
            short_name="SJK(T) Test", state="Selangor", ppd="Test",
        )
        contact = SchoolContact.objects.create(
            school=school, email="test@moe.edu.my", is_active=True,
        )
        session = self.client.session
        session["school_contact_id"] = contact.id
        session["school_moe_code"] = school.moe_code
        session.save()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["school_moe_code"], "XYZ0001")

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
