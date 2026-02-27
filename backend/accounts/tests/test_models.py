from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from accounts.models import MagicLinkToken, SchoolContact
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
