from datetime import timedelta

from django.contrib.auth.models import User
from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone

from accounts.models import MagicLinkToken, SchoolContact, UserProfile
from schools.models import Constituency, School


class SchoolContactModelTest(TestCase):
    def setUp(self):
        self.constituency = Constituency.objects.create(
            code="P140", name="Segamat", state="Johor"
        )
        self.school = School.objects.create(
            moe_code="JBD0050",
            name="SJK(T) Ladang Bikam",
            short_name="SJK(T) Ladang Bikam",
            state="Johor",
            constituency=self.constituency,
            email="jbd0050@moe.edu.my",
        )

    def test_create_contact(self):
        contact = SchoolContact.objects.create(
            school=self.school,
            email="jbd0050@moe.edu.my",
            name="Mr. Test",
            role="Headmaster",
        )
        self.assertEqual(contact.email, "jbd0050@moe.edu.my")
        self.assertTrue(contact.is_active)
        self.assertIsNotNone(contact.verified_at)

    def test_str_representation(self):
        contact = SchoolContact.objects.create(
            school=self.school, email="jbd0050@moe.edu.my"
        )
        self.assertIn("jbd0050@moe.edu.my", str(contact))
        self.assertIn("SJK(T) Ladang Bikam", str(contact))

    def test_unique_together(self):
        SchoolContact.objects.create(
            school=self.school, email="jbd0050@moe.edu.my"
        )
        with self.assertRaises(Exception):
            SchoolContact.objects.create(
                school=self.school, email="jbd0050@moe.edu.my"
            )


class MagicLinkTokenModelTest(TestCase):
    def setUp(self):
        self.constituency = Constituency.objects.create(
            code="P140", name="Segamat", state="Johor"
        )
        self.school = School.objects.create(
            moe_code="JBD0050",
            name="SJK(T) Ladang Bikam",
            short_name="SJK(T) Ladang Bikam",
            state="Johor",
            constituency=self.constituency,
        )

    def test_create_token(self):
        token = MagicLinkToken.objects.create(
            email="jbd0050@moe.edu.my",
            school=self.school,
            expires_at=timezone.now() + timedelta(hours=24),
        )
        self.assertFalse(token.is_used)
        self.assertFalse(token.is_expired)
        self.assertTrue(token.is_valid)

    def test_expired_token(self):
        token = MagicLinkToken.objects.create(
            email="jbd0050@moe.edu.my",
            school=self.school,
            expires_at=timezone.now() - timedelta(hours=1),
        )
        self.assertTrue(token.is_expired)
        self.assertFalse(token.is_valid)

    def test_used_token(self):
        token = MagicLinkToken.objects.create(
            email="jbd0050@moe.edu.my",
            school=self.school,
            expires_at=timezone.now() + timedelta(hours=24),
            is_used=True,
        )
        self.assertFalse(token.is_valid)

    def test_str_representation(self):
        token = MagicLinkToken.objects.create(
            email="jbd0050@moe.edu.my",
            school=self.school,
            expires_at=timezone.now() + timedelta(hours=24),
        )
        self.assertIn("jbd0050@moe.edu.my", str(token))
        self.assertIn("JBD0050", str(token))


class UserProfileModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("testuser", "test@example.com", "pass")
        self.school = School.objects.create(
            moe_code="ABC1234",
            name="Sekolah Jenis Kebangsaan (Tamil) Test",
            short_name="SJK(T) Test",
            state="Selangor",
            ppd="Petaling Perdana",
        )

    def test_create_basic_profile(self):
        profile = UserProfile.objects.create(
            user=self.user,
            google_id="google-123",
            display_name="Test User",
        )
        self.assertEqual(profile.role, "USER")
        self.assertEqual(profile.points, 0)
        self.assertIsNone(profile.admin_school)
        self.assertTrue(profile.is_active)

    def test_google_id_unique(self):
        UserProfile.objects.create(user=self.user, google_id="google-123")
        user2 = User.objects.create_user("testuser2", "test2@example.com", "pass")
        with self.assertRaises(IntegrityError):
            UserProfile.objects.create(user=user2, google_id="google-123")

    def test_admin_school_unique(self):
        UserProfile.objects.create(
            user=self.user, google_id="g1", admin_school=self.school,
        )
        user2 = User.objects.create_user("testuser2", "test2@example.com", "pass")
        with self.assertRaises(IntegrityError):
            UserProfile.objects.create(
                user=user2, google_id="g2", admin_school=self.school,
            )

    def test_admin_school_nullable(self):
        profile = UserProfile.objects.create(user=self.user, google_id="g1")
        self.assertIsNone(profile.admin_school)

    def test_is_school_admin_property(self):
        profile = UserProfile.objects.create(
            user=self.user, google_id="g1", admin_school=self.school,
        )
        self.assertTrue(profile.is_school_admin)

    def test_is_school_admin_false_when_no_school(self):
        profile = UserProfile.objects.create(user=self.user, google_id="g1")
        self.assertFalse(profile.is_school_admin)

    def test_str(self):
        profile = UserProfile.objects.create(
            user=self.user, google_id="g1", display_name="Test User",
        )
        self.assertIn("Test User", str(profile))

    def test_role_choices(self):
        profile = UserProfile.objects.create(
            user=self.user, google_id="g1", role="MODERATOR",
        )
        self.assertEqual(profile.role, "MODERATOR")
