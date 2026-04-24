from django.contrib.auth.models import User
from django.test import TestCase

from accounts.models import UserProfile
from schools.models import Constituency, School


class UserProfileModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="test", email="test@gmail.com")
        self.constituency = Constituency.objects.create(
            code="P140", name="Segamat", state="Johor",
        )
        self.school = School.objects.create(
            moe_code="JBD0050",
            name="SJK(T) Test",
            short_name="SJK(T) Test",
            constituency=self.constituency,
            state="Johor",
        )

    def test_create_minimal_profile(self):
        profile = UserProfile.objects.create(
            user=self.user, google_id="abc", display_name="Test",
        )
        self.assertEqual(profile.role, UserProfile.Role.USER)
        self.assertFalse(profile.is_school_admin)
        self.assertEqual(profile.points, 0)
        self.assertTrue(profile.is_active)

    def test_profile_with_admin_school(self):
        profile = UserProfile.objects.create(
            user=self.user,
            google_id="abc",
            display_name="Test",
            admin_school=self.school,
        )
        self.assertTrue(profile.is_school_admin)
        self.assertEqual(profile.admin_school, self.school)

    def test_role_choices(self):
        self.assertEqual(UserProfile.Role.SUPERADMIN, "SUPERADMIN")
        self.assertEqual(UserProfile.Role.MODERATOR, "MODERATOR")
        self.assertEqual(UserProfile.Role.USER, "USER")

    def test_str_representation(self):
        profile = UserProfile.objects.create(
            user=self.user, google_id="abc", display_name="Alice", role="MODERATOR",
        )
        self.assertEqual(str(profile), "Alice (MODERATOR)")
