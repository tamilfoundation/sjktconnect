from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from accounts.models import UserProfile, SchoolContact, MagicLinkToken
from schools.models import School
import uuid
from django.utils import timezone
from datetime import timedelta


class LinkSchoolTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = "/api/v1/auth/link-school/"
        self.school = School.objects.create(
            moe_code="ABC1234", name="Test School",
            short_name="SJK(T) Test", state="Selangor", ppd="Test",
        )
        self.user = User.objects.create_user("guser", "g@gmail.com", "pass")
        self.profile = UserProfile.objects.create(
            user=self.user, google_id="g-123", display_name="User",
        )
        # Create a valid magic link token
        self.token = MagicLinkToken.objects.create(
            token=uuid.uuid4(),
            email="abc1234@moe.edu.my",
            school=self.school,
            expires_at=timezone.now() + timedelta(hours=24),
        )

    def test_link_school_success(self):
        session = self.client.session
        session["user_profile_id"] = self.profile.id
        session.save()
        response = self.client.post(self.url, {"token": str(self.token.token)})
        self.assertEqual(response.status_code, 200)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.admin_school, self.school)

    def test_link_school_no_session_401(self):
        response = self.client.post(self.url, {"token": str(self.token.token)})
        self.assertEqual(response.status_code, 401)

    def test_link_school_invalid_token_400(self):
        session = self.client.session
        session["user_profile_id"] = self.profile.id
        session.save()
        response = self.client.post(self.url, {"token": str(uuid.uuid4())})
        self.assertEqual(response.status_code, 400)

    def test_link_school_already_claimed_409(self):
        user2 = User.objects.create_user("other", "other@gmail.com", "pass")
        UserProfile.objects.create(
            user=user2, google_id="g-other", admin_school=self.school,
        )
        session = self.client.session
        session["user_profile_id"] = self.profile.id
        session.save()
        response = self.client.post(self.url, {"token": str(self.token.token)})
        self.assertEqual(response.status_code, 409)
