"""Tests for School edit/confirm API endpoints (UserProfile-based auth)."""

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import UserProfile
from core.models import AuditLog
from schools.models import Constituency, School


class EditAuthorisationTest(TestCase):
    """Permission checks on /edit/ endpoint with UserProfile sessions."""

    def setUp(self):
        self.client = APIClient()
        self.constituency = Constituency.objects.create(
            code="P140", name="Segamat", state="Johor",
        )
        self.school = School.objects.create(
            moe_code="JBD0050",
            name="SJK(T) Ladang Bikam",
            short_name="SJK(T) Ladang Bikam",
            state="Johor",
            constituency=self.constituency,
            email="jbd0050@moe.edu.my",
        )
        self.other_school = School.objects.create(
            moe_code="JBD0099",
            name="SJK(T) Other",
            short_name="SJK(T) Other",
            state="Johor",
            constituency=self.constituency,
        )

    def _auth(self, profile):
        session = self.client.session
        session["user_profile_id"] = profile.id
        session.save()

    def test_unauthenticated_denied(self):
        response = self.client.get(f"/api/v1/schools/{self.school.moe_code}/edit/")
        self.assertEqual(response.status_code, 403)

    def test_school_admin_allowed(self):
        user = User.objects.create_user("admin", "admin@moe.edu.my")
        profile = UserProfile.objects.create(
            user=user, google_id="g-a", display_name="Admin",
            admin_school=self.school,
        )
        self._auth(profile)
        response = self.client.get(f"/api/v1/schools/{self.school.moe_code}/edit/")
        self.assertEqual(response.status_code, 200)

    def test_superadmin_can_edit_any_school(self):
        user = User.objects.create_user("super", "super@foo")
        profile = UserProfile.objects.create(
            user=user, google_id="g-s", display_name="Super", role="SUPERADMIN",
        )
        self._auth(profile)
        response = self.client.get(f"/api/v1/schools/{self.school.moe_code}/edit/")
        self.assertEqual(response.status_code, 200)

    def test_admin_of_other_school_denied(self):
        user = User.objects.create_user("otheradmin", "x@foo")
        profile = UserProfile.objects.create(
            user=user, google_id="g-o", display_name="Other",
            admin_school=self.other_school,
        )
        self._auth(profile)
        response = self.client.get(f"/api/v1/schools/{self.school.moe_code}/edit/")
        self.assertEqual(response.status_code, 403)

    def test_regular_user_without_admin_school_denied(self):
        user = User.objects.create_user("reg", "r@foo")
        profile = UserProfile.objects.create(
            user=user, google_id="g-r", display_name="Reg",
        )
        self._auth(profile)
        response = self.client.get(f"/api/v1/schools/{self.school.moe_code}/edit/")
        self.assertEqual(response.status_code, 403)

    def test_inactive_profile_denied(self):
        user = User.objects.create_user("inactive", "i@moe.edu.my")
        profile = UserProfile.objects.create(
            user=user, google_id="g-i", display_name="Inactive",
            admin_school=self.school, is_active=False,
        )
        self._auth(profile)
        response = self.client.get(f"/api/v1/schools/{self.school.moe_code}/edit/")
        self.assertEqual(response.status_code, 403)


class SchoolEditViewTest(TestCase):
    """GET/PUT /api/v1/schools/{moe_code}/edit/"""

    def setUp(self):
        self.client = APIClient()
        self.constituency = Constituency.objects.create(
            code="P140", name="Segamat", state="Johor",
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
        self.user = User.objects.create_user("admin", "jbd0050@moe.edu.my")
        self.profile = UserProfile.objects.create(
            user=self.user, google_id="g-a", display_name="Admin",
            admin_school=self.school,
        )
        session = self.client.session
        session["user_profile_id"] = self.profile.id
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
        # Sprint 28: phone is auto-normalised to +60-X XXX XXXX on save.
        self.assertEqual(self.school.phone, "+60-7 999 9999")
        self.assertEqual(self.school.enrolment, 150)

    def test_put_creates_audit_log(self):
        self.client.put(
            "/api/v1/schools/JBD0050/edit/",
            {"phone": "07-9999999"},
            format="json",
        )
        logs = AuditLog.objects.filter(action="update", target_id="JBD0050")
        log = next((e for e in logs if "changed_fields" in e.detail), None)
        self.assertIsNotNone(log)
        self.assertEqual(log.target_type, "School")
        self.assertIn("phone", log.detail["changed_fields"])
        self.assertEqual(log.detail["contact"], "jbd0050@moe.edu.my")

    def test_put_read_only_fields_ignored(self):
        self.client.put(
            "/api/v1/schools/JBD0050/edit/",
            {"name": "Hacked Name", "state": "Sabah"},
            format="json",
        )
        self.school.refresh_from_db()
        self.assertEqual(self.school.name, "SJK(T) Ladang Bikam")
        self.assertEqual(self.school.state, "Johor")

    def test_nonexistent_school_404(self):
        response = self.client.get("/api/v1/schools/ZZZZZZ/edit/")
        self.assertEqual(response.status_code, 404)

    def test_partial_update(self):
        response = self.client.put(
            "/api/v1/schools/JBD0050/edit/",
            {"name_tamil": "தோட்டம் பிக்கம்"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.school.refresh_from_db()
        self.assertEqual(self.school.name_tamil, "தோட்டம் பிக்கம்")
        self.assertEqual(self.school.phone, "07-1234567")

    # --- Sprint 26 validation tests ---

    def test_put_rejects_multi_number_phone(self):
        """Sprint 26 #1: phone with `/` is the canonical bad shape."""
        response = self.client.put(
            "/api/v1/schools/JBD0050/edit/",
            {"phone": "05-2421470/011-2379104"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("phone", response.data)

    def test_put_rejects_phone_with_letters(self):
        response = self.client.put(
            "/api/v1/schools/JBD0050/edit/",
            {"phone": "call us 03-1234"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_put_accepts_normal_phone_shapes(self):
        for phone in ["+60 4 966 3429", "04-966 3429", "(03) 2601 7222"]:
            response = self.client.put(
                "/api/v1/schools/JBD0050/edit/",
                {"phone": phone},
                format="json",
            )
            self.assertEqual(response.status_code, 200, f"rejected: {phone}")

    def test_put_rejects_invalid_session_type(self):
        """Sprint 26 #2: session_type is constrained to MOE values."""
        response = self.client.put(
            "/api/v1/schools/JBD0050/edit/",
            {"session_type": "MORNING"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("session_type", response.data)

    def test_put_accepts_valid_session_types(self):
        for v in ["Pagi Sahaja", "Pagi dan Petang", ""]:
            response = self.client.put(
                "/api/v1/schools/JBD0050/edit/",
                {"session_type": v},
                format="json",
            )
            self.assertEqual(response.status_code, 200, f"rejected: {v!r}")


