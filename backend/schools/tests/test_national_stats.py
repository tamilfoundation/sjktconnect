"""Tests for the national statistics API endpoint."""

from django.test import TestCase
from rest_framework.test import APIClient

from schools.models import Constituency, School


class NationalStatsViewTest(TestCase):
    """Tests for GET /api/v1/stats/national/."""

    def setUp(self):
        self.client = APIClient()
        self.constituency = Constituency.objects.create(
            code="P001",
            name="Test Constituency",
            state="Johor",
            mp_name="Test MP",
            mp_party="Test Party",
        )

    def test_stats_with_no_schools(self):
        """Returns zero counts when no schools exist."""
        response = self.client.get("/api/v1/stats/national/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["total_schools"], 0)
        self.assertEqual(data["total_students"], 0)
        self.assertEqual(data["total_teachers"], 0)
        self.assertEqual(data["states"], 0)
        self.assertEqual(data["constituencies_with_schools"], 0)
        self.assertEqual(data["schools_under_30_students"], 0)

    def test_stats_with_schools(self):
        """Returns correct aggregated statistics."""
        School.objects.create(
            moe_code="JBD0001",
            name="SJK(T) Test One",
            short_name="SJK(T) Test One",
            state="Johor",
            enrolment=150,
            teacher_count=12,
            constituency=self.constituency,
        )
        School.objects.create(
            moe_code="ABD0001",
            name="SJK(T) Test Two",
            short_name="SJK(T) Test Two",
            state="Perak",
            enrolment=25,
            teacher_count=5,
            constituency=self.constituency,
        )

        response = self.client.get("/api/v1/stats/national/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["total_schools"], 2)
        self.assertEqual(data["total_students"], 175)
        self.assertEqual(data["total_teachers"], 17)
        self.assertEqual(data["states"], 2)
        self.assertEqual(data["constituencies_with_schools"], 1)
        self.assertEqual(data["schools_under_30_students"], 1)

    def test_excludes_inactive_schools(self):
        """Inactive schools are not counted."""
        School.objects.create(
            moe_code="JBD0001",
            name="SJK(T) Active",
            short_name="SJK(T) Active",
            state="Johor",
            enrolment=100,
            teacher_count=10,
        )
        School.objects.create(
            moe_code="JBD0002",
            name="SJK(T) Closed",
            short_name="SJK(T) Closed",
            state="Johor",
            enrolment=50,
            teacher_count=5,
            is_active=False,
        )

        response = self.client.get("/api/v1/stats/national/")
        data = response.json()
        self.assertEqual(data["total_schools"], 1)
        self.assertEqual(data["total_students"], 100)
        self.assertEqual(data["total_teachers"], 10)

    def test_null_enrolment_handled(self):
        """Schools with zero enrolment don't break aggregation."""
        School.objects.create(
            moe_code="JBD0001",
            name="SJK(T) Zero",
            short_name="SJK(T) Zero",
            state="Johor",
            enrolment=0,
            teacher_count=0,
        )

        response = self.client.get("/api/v1/stats/national/")
        data = response.json()
        self.assertEqual(data["total_schools"], 1)
        self.assertEqual(data["total_students"], 0)
        self.assertEqual(data["schools_under_30_students"], 1)
