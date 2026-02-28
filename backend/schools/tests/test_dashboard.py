"""Tests for the admin verification dashboard."""

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from accounts.models import SchoolContact
from schools.models import Constituency, School


class VerificationDashboardAuthTest(TestCase):
    """Test that the dashboard requires login."""

    def test_anonymous_redirected_to_login(self):
        resp = self.client.get("/dashboard/verification/")
        assert resp.status_code == 302
        assert "/accounts/login/" in resp.url

    def test_authenticated_user_can_access(self):
        User.objects.create_user(username="admin", password="pass")
        self.client.login(username="admin", password="pass")
        # Need at least one school to avoid division by zero
        School.objects.create(
            moe_code="JBD0050",
            name="SJK(T) Test",
            short_name="SJK(T) Test",
            state="Johor",
            ppd="PPD Segamat",
        )
        resp = self.client.get("/dashboard/verification/")
        assert resp.status_code == 200


class VerificationDashboardContextTest(TestCase):
    """Test the context data passed to the template."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username="admin", password="pass")
        cls.constituency = Constituency.objects.create(
            code="P140", name="Segamat", state="Johor",
            mp_name="Test MP", mp_party="PH",
        )
        # 3 schools: 1 verified, 2 unverified (1 Johor, 1 Kedah)
        cls.verified_school = School.objects.create(
            moe_code="JBD0050",
            name="SJK(T) Verified",
            short_name="SJK(T) Verified",
            state="Johor",
            ppd="PPD Segamat",
            constituency=cls.constituency,
            last_verified=timezone.now(),
            verified_by="test@moe.edu.my",
        )
        cls.unverified_johor = School.objects.create(
            moe_code="JBD0051",
            name="SJK(T) Unverified Johor",
            short_name="SJK(T) Unverified Johor",
            state="Johor",
            ppd="PPD Segamat",
        )
        cls.unverified_kedah = School.objects.create(
            moe_code="AGD1234",
            name="SJK(T) Unverified Kedah",
            short_name="SJK(T) Unverified Kedah",
            state="Kedah",
            ppd="PPD Kulim",
        )
        # Inactive school — should be excluded
        School.objects.create(
            moe_code="ABD5111",
            name="SJK(T) Closed",
            short_name="SJK(T) Closed",
            state="Perak",
            ppd="PPD Kinta",
            is_active=False,
        )
        # A contact
        cls.contact = SchoolContact.objects.create(
            school=cls.verified_school,
            email="jbd0050@moe.edu.my",
            name="Test Teacher",
            role="Headmaster",
        )

    def setUp(self):
        self.client.login(username="admin", password="pass")
        self.resp = self.client.get("/dashboard/verification/")
        self.ctx = self.resp.context

    def test_total_schools_excludes_inactive(self):
        assert self.ctx["total_schools"] == 3

    def test_verified_count(self):
        assert self.ctx["verified_count"] == 1

    def test_unverified_count(self):
        assert self.ctx["unverified_count"] == 2

    def test_progress_percent(self):
        # 1 of 3 = 33.3%
        assert self.ctx["progress_percent"] == 33.3

    def test_recently_verified_contains_verified_school(self):
        recent = list(self.ctx["recently_verified"])
        assert len(recent) == 1
        assert recent[0].moe_code == "JBD0050"

    def test_recently_verified_excludes_unverified(self):
        recent_codes = [s.moe_code for s in self.ctx["recently_verified"]]
        assert "JBD0051" not in recent_codes
        assert "AGD1234" not in recent_codes

    def test_unverified_by_state(self):
        by_state = list(self.ctx["unverified_by_state"])
        # Both states have 1 unverified school each
        states = {row["state"]: row["count"] for row in by_state}
        assert states["Johor"] == 1
        assert states["Kedah"] == 1

    def test_unverified_by_state_ordered_by_count_desc(self):
        # Add another unverified Johor school to make ordering testable
        School.objects.create(
            moe_code="JBD0052",
            name="SJK(T) Extra",
            short_name="SJK(T) Extra",
            state="Johor",
            ppd="PPD Segamat",
        )
        resp = self.client.get("/dashboard/verification/")
        by_state = list(resp.context["unverified_by_state"])
        # Johor now has 2, Kedah has 1 — Johor should be first
        assert by_state[0]["state"] == "Johor"
        assert by_state[0]["count"] == 2

    def test_contacts_list(self):
        contacts = list(self.ctx["contacts"])
        assert len(contacts) == 1
        assert contacts[0].email == "jbd0050@moe.edu.my"

    def test_contacts_excludes_inactive(self):
        SchoolContact.objects.create(
            school=self.unverified_johor,
            email="inactive@moe.edu.my",
            is_active=False,
        )
        resp = self.client.get("/dashboard/verification/")
        contacts = list(resp.context["contacts"])
        emails = [c.email for c in contacts]
        assert "inactive@moe.edu.my" not in emails

    def test_template_used(self):
        self.assertTemplateUsed(self.resp, "schools/verification_dashboard.html")


class VerificationDashboardEmptyTest(TestCase):
    """Test the dashboard with zero schools (edge case)."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username="admin", password="pass")

    def test_zero_schools_no_division_error(self):
        self.client.login(username="admin", password="pass")
        resp = self.client.get("/dashboard/verification/")
        # With 0 schools, should still render without error
        assert resp.status_code == 200
        assert resp.context["total_schools"] == 0
        assert resp.context["progress_percent"] == 0
