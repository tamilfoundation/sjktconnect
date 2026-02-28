"""Tests for School edit/confirm API endpoints and permission class."""

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import SchoolContact
from core.models import AuditLog
from schools.models import Constituency, School


class IsMagicLinkAuthenticatedTest(TestCase):
    """Test the Magic Link session permission class."""

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
        self.contact = SchoolContact.objects.create(
            school=self.school,
            email="jbd0050@moe.edu.my",
        )

    def test_unauthenticated_denied(self):
        response = self.client.get(f"/api/v1/schools/{self.school.moe_code}/edit/")
        self.assertEqual(response.status_code, 403)

    def test_authenticated_allowed(self):
        session = self.client.session
        session["school_contact_id"] = self.contact.id
        session["school_moe_code"] = self.school.moe_code
        session.save()
        response = self.client.get(f"/api/v1/schools/{self.school.moe_code}/edit/")
        self.assertEqual(response.status_code, 200)

    def test_inactive_contact_denied(self):
        self.contact.is_active = False
        self.contact.save()
        session = self.client.session
        session["school_contact_id"] = self.contact.id
        session["school_moe_code"] = self.school.moe_code
        session.save()
        response = self.client.get(f"/api/v1/schools/{self.school.moe_code}/edit/")
        self.assertEqual(response.status_code, 403)

    def test_nonexistent_contact_denied(self):
        session = self.client.session
        session["school_contact_id"] = 99999
        session["school_moe_code"] = self.school.moe_code
        session.save()
        response = self.client.get(f"/api/v1/schools/{self.school.moe_code}/edit/")
        self.assertEqual(response.status_code, 403)


class SchoolEditViewTest(TestCase):
    """Test GET/PUT /api/v1/schools/{moe_code}/edit/"""

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
            phone="07-1234567",
            enrolment=120,
        )
        self.contact = SchoolContact.objects.create(
            school=self.school,
            email="jbd0050@moe.edu.my",
        )
        # Set up session
        session = self.client.session
        session["school_contact_id"] = self.contact.id
        session["school_moe_code"] = self.school.moe_code
        session.save()

    def test_get_returns_school_data(self):
        response = self.client.get("/api/v1/schools/JBD0050/edit/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["moe_code"], "JBD0050")
        self.assertEqual(response.data["phone"], "07-1234567")
        self.assertEqual(response.data["enrolment"], 120)

    def test_put_updates_fields(self):
        response = self.client.put(
            "/api/v1/schools/JBD0050/edit/",
            {"phone": "07-9999999", "enrolment": 150},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.school.refresh_from_db()
        self.assertEqual(self.school.phone, "07-9999999")
        self.assertEqual(self.school.enrolment, 150)

    def test_put_sets_verification_timestamp(self):
        before = timezone.now()
        self.client.put(
            "/api/v1/schools/JBD0050/edit/",
            {"phone": "07-9999999"},
            format="json",
        )
        self.school.refresh_from_db()
        self.assertIsNotNone(self.school.last_verified)
        self.assertGreaterEqual(self.school.last_verified, before)
        self.assertEqual(self.school.verified_by, "jbd0050@moe.edu.my")

    def test_put_creates_audit_log(self):
        self.client.put(
            "/api/v1/schools/JBD0050/edit/",
            {"phone": "07-9999999"},
            format="json",
        )
        # Filter for our explicit audit log (has changed_fields), not the
        # signal-created one (has only {"action": "update"})
        logs = AuditLog.objects.filter(action="update", target_id="JBD0050")
        log = next((entry for entry in logs if "changed_fields" in entry.detail), None)
        self.assertIsNotNone(log)
        self.assertEqual(log.target_type, "School")
        self.assertIn("phone", log.detail["changed_fields"])

    def test_put_read_only_fields_ignored(self):
        """Read-only fields (moe_code, name, state) should not be updated."""
        self.client.put(
            "/api/v1/schools/JBD0050/edit/",
            {"name": "Hacked Name", "state": "Sabah"},
            format="json",
        )
        self.school.refresh_from_db()
        self.assertEqual(self.school.name, "SJK(T) Ladang Bikam")
        self.assertEqual(self.school.state, "Johor")

    def test_wrong_school_forbidden(self):
        """Rep can't edit a different school."""
        other = School.objects.create(
            moe_code="JBD0099",
            name="SJK(T) Other",
            short_name="SJK(T) Other",
            state="Johor",
            constituency=self.constituency,
        )
        response = self.client.get(f"/api/v1/schools/{other.moe_code}/edit/")
        self.assertEqual(response.status_code, 403)

    def test_nonexistent_school_404(self):
        session = self.client.session
        session["school_moe_code"] = "ZZZZZZ"
        session.save()
        response = self.client.get("/api/v1/schools/ZZZZZZ/edit/")
        self.assertEqual(response.status_code, 404)

    def test_partial_update(self):
        """PUT with partial=True should only update specified fields."""
        response = self.client.put(
            "/api/v1/schools/JBD0050/edit/",
            {"name_tamil": "தோட்டம் பிக்கம்"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.school.refresh_from_db()
        self.assertEqual(self.school.name_tamil, "தோட்டம் பிக்கம்")
        # Phone should remain unchanged
        self.assertEqual(self.school.phone, "07-1234567")


class SchoolConfirmViewTest(TestCase):
    """Test POST /api/v1/schools/{moe_code}/confirm/"""

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
        self.contact = SchoolContact.objects.create(
            school=self.school,
            email="jbd0050@moe.edu.my",
        )
        session = self.client.session
        session["school_contact_id"] = self.contact.id
        session["school_moe_code"] = self.school.moe_code
        session.save()

    def test_confirm_updates_timestamp(self):
        before = timezone.now()
        response = self.client.post("/api/v1/schools/JBD0050/confirm/")
        self.assertEqual(response.status_code, 200)
        self.school.refresh_from_db()
        self.assertIsNotNone(self.school.last_verified)
        self.assertGreaterEqual(self.school.last_verified, before)
        self.assertEqual(self.school.verified_by, "jbd0050@moe.edu.my")

    def test_confirm_response_body(self):
        response = self.client.post("/api/v1/schools/JBD0050/confirm/")
        self.assertEqual(response.data["message"], "School data confirmed.")
        self.assertIn("last_verified", response.data)
        self.assertEqual(response.data["verified_by"], "jbd0050@moe.edu.my")

    def test_confirm_creates_audit_log(self):
        self.client.post("/api/v1/schools/JBD0050/confirm/")
        log = AuditLog.objects.filter(action="confirm", target_id="JBD0050").first()
        self.assertIsNotNone(log)
        self.assertEqual(log.target_type, "School")

    def test_unauthenticated_denied(self):
        client = APIClient()
        response = client.post("/api/v1/schools/JBD0050/confirm/")
        self.assertEqual(response.status_code, 403)

    def test_wrong_school_forbidden(self):
        other = School.objects.create(
            moe_code="JBD0099",
            name="SJK(T) Other",
            short_name="SJK(T) Other",
            state="Johor",
            constituency=self.constituency,
        )
        response = self.client.post(f"/api/v1/schools/{other.moe_code}/confirm/")
        self.assertEqual(response.status_code, 403)

    def test_nonexistent_school_404(self):
        session = self.client.session
        session["school_moe_code"] = "ZZZZZZ"
        session.save()
        response = self.client.post("/api/v1/schools/ZZZZZZ/confirm/")
        self.assertEqual(response.status_code, 404)
