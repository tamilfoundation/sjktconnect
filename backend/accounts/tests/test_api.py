from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import MagicLinkToken, SchoolContact
from accounts.services.token import (
    create_magic_token,
    find_school_by_email,
    validate_moe_email,
    verify_token,
)
from schools.models import Constituency, School


class ValidateMoeEmailTest(TestCase):
    def test_valid_moe_email(self):
        self.assertTrue(validate_moe_email("jbd0050@moe.edu.my"))

    def test_valid_moe_email_uppercase(self):
        self.assertTrue(validate_moe_email("JBD0050@MOE.EDU.MY"))

    def test_invalid_email(self):
        self.assertFalse(validate_moe_email("user@gmail.com"))

    def test_empty_email(self):
        self.assertFalse(validate_moe_email(""))

    def test_partial_domain(self):
        self.assertFalse(validate_moe_email("user@edu.my"))


class FindSchoolByEmailTest(TestCase):
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

    def test_find_by_moe_code(self):
        school = find_school_by_email("jbd0050@moe.edu.my")
        self.assertEqual(school, self.school)

    def test_find_by_moe_code_case_insensitive(self):
        school = find_school_by_email("JBD0050@moe.edu.my")
        self.assertEqual(school, self.school)

    def test_find_by_stored_email(self):
        # Change stored email to something different from moe_code pattern
        self.school.email = "custom@moe.edu.my"
        self.school.save()
        school = find_school_by_email("custom@moe.edu.my")
        self.assertEqual(school, self.school)

    def test_no_match(self):
        school = find_school_by_email("unknown@moe.edu.my")
        self.assertIsNone(school)


class VerifyTokenServiceTest(TestCase):
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

    def test_valid_token(self):
        token = create_magic_token("jbd0050@moe.edu.my", self.school)
        result = verify_token(str(token.token))
        self.assertIsNotNone(result)
        self.assertTrue(result.is_used)

    def test_expired_token(self):
        token = MagicLinkToken.objects.create(
            email="jbd0050@moe.edu.my",
            school=self.school,
            expires_at=timezone.now() - timedelta(hours=1),
        )
        result = verify_token(str(token.token))
        self.assertIsNone(result)

    def test_used_token(self):
        token = create_magic_token("jbd0050@moe.edu.my", self.school)
        verify_token(str(token.token))
        result = verify_token(str(token.token))
        self.assertIsNone(result)

    def test_invalid_token(self):
        result = verify_token("00000000-0000-0000-0000-000000000000")
        self.assertIsNone(result)

    def test_malformed_token(self):
        result = verify_token("not-a-uuid")
        self.assertIsNone(result)


class RequestMagicLinkAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
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

    @patch("accounts.api.views.send_magic_link_email", return_value=True)
    def test_request_magic_link_success(self, mock_email):
        response = self.client.post(
            "/api/v1/auth/request-magic-link/",
            {"email": "jbd0050@moe.edu.my"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("Magic link sent", response.data["message"])
        self.assertEqual(response.data["school_name"], "SJK(T) Ladang Bikam")
        mock_email.assert_called_once()
        self.assertEqual(MagicLinkToken.objects.count(), 1)

    def test_request_magic_link_non_moe_email(self):
        response = self.client.post(
            "/api/v1/auth/request-magic-link/",
            {"email": "user@gmail.com"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("moe.edu.my", response.data["error"])

    def test_request_magic_link_no_school_found(self):
        response = self.client.post(
            "/api/v1/auth/request-magic-link/",
            {"email": "unknown@moe.edu.my"},
            format="json",
        )
        self.assertEqual(response.status_code, 404)

    def test_request_magic_link_missing_email(self):
        response = self.client.post(
            "/api/v1/auth/request-magic-link/", {}, format="json"
        )
        self.assertEqual(response.status_code, 400)


class VerifyTokenAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
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

    def test_verify_valid_token(self):
        token = create_magic_token("jbd0050@moe.edu.my", self.school)
        response = self.client.get(f"/api/v1/auth/verify/{token.token}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["school_moe_code"], "JBD0050")
        self.assertEqual(response.data["email"], "jbd0050@moe.edu.my")
        # SchoolContact should be created
        self.assertEqual(SchoolContact.objects.count(), 1)

    def test_verify_creates_session(self):
        token = create_magic_token("jbd0050@moe.edu.my", self.school)
        self.client.get(f"/api/v1/auth/verify/{token.token}/")
        # Session should have school_contact_id
        me_response = self.client.get("/api/v1/auth/me/")
        self.assertEqual(me_response.status_code, 200)

    def test_verify_invalid_token(self):
        response = self.client.get(
            "/api/v1/auth/verify/00000000-0000-0000-0000-000000000000/"
        )
        self.assertEqual(response.status_code, 400)

    def test_verify_expired_token(self):
        token = MagicLinkToken.objects.create(
            email="jbd0050@moe.edu.my",
            school=self.school,
            expires_at=timezone.now() - timedelta(hours=1),
        )
        response = self.client.get(f"/api/v1/auth/verify/{token.token}/")
        self.assertEqual(response.status_code, 400)

    def test_verify_updates_existing_contact(self):
        SchoolContact.objects.create(
            school=self.school, email="jbd0050@moe.edu.my", is_active=False
        )
        token = create_magic_token("jbd0050@moe.edu.my", self.school)
        self.client.get(f"/api/v1/auth/verify/{token.token}/")
        contact = SchoolContact.objects.get(
            school=self.school, email="jbd0050@moe.edu.my"
        )
        self.assertTrue(contact.is_active)


class MeAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
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

    def test_me_unauthenticated(self):
        response = self.client.get("/api/v1/auth/me/")
        self.assertEqual(response.status_code, 401)

    def test_me_after_verify(self):
        token = create_magic_token("jbd0050@moe.edu.my", self.school)
        self.client.get(f"/api/v1/auth/verify/{token.token}/")
        response = self.client.get("/api/v1/auth/me/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["school_moe_code"], "JBD0050")
        self.assertEqual(response.data["email"], "jbd0050@moe.edu.my")

    def test_me_with_deactivated_contact(self):
        token = create_magic_token("jbd0050@moe.edu.my", self.school)
        self.client.get(f"/api/v1/auth/verify/{token.token}/")
        # Deactivate the contact
        SchoolContact.objects.filter(email="jbd0050@moe.edu.my").update(
            is_active=False
        )
        response = self.client.get("/api/v1/auth/me/")
        self.assertEqual(response.status_code, 401)
