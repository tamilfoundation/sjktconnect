"""Sprint 32 test-debt catch-up: SchoolEnrolmentSnapshot model
+ SchoolDetailSerializer.enrolment_history field.
"""

from datetime import date

from django.db.utils import IntegrityError
from django.test import TestCase
from rest_framework.test import APIClient

from schools.models import School, SchoolEnrolmentSnapshot


class SchoolEnrolmentSnapshotTest(TestCase):
    def setUp(self):
        self.school = School.objects.create(
            moe_code="XBD1000", name="SJK(T) Test",
            short_name="SJK(T) Test", state="Selangor",
        )

    def test_unique_together_school_and_date(self):
        SchoolEnrolmentSnapshot.objects.create(
            school=self.school, snapshot_date=date(2025, 3, 1), students=400,
        )
        with self.assertRaises(IntegrityError):
            SchoolEnrolmentSnapshot.objects.create(
                school=self.school, snapshot_date=date(2025, 3, 1), students=450,
            )

    def test_ordering_by_date(self):
        SchoolEnrolmentSnapshot.objects.create(
            school=self.school, snapshot_date=date(2026, 4, 1), students=380,
        )
        SchoolEnrolmentSnapshot.objects.create(
            school=self.school, snapshot_date=date(2018, 1, 1), students=500,
        )
        SchoolEnrolmentSnapshot.objects.create(
            school=self.school, snapshot_date=date(2022, 6, 1), students=440,
        )
        dates = list(
            SchoolEnrolmentSnapshot.objects
            .filter(school=self.school)
            .values_list("snapshot_date", flat=True)
        )
        self.assertEqual(dates, [
            date(2018, 1, 1), date(2022, 6, 1), date(2026, 4, 1),
        ])


class EnrolmentHistorySerializerTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.school = School.objects.create(
            moe_code="XBD2000", name="SJK(T) HistTest",
            short_name="SJK(T) HistTest", state="Selangor",
        )

    def test_empty_history_returns_empty_list(self):
        resp = self.client.get(f"/api/v1/schools/{self.school.moe_code}/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["enrolment_history"], [])

    def test_history_returns_oldest_first(self):
        # Insert out of order — serializer must sort by date.
        SchoolEnrolmentSnapshot.objects.create(
            school=self.school, snapshot_date=date(2025, 3, 1), students=460,
        )
        SchoolEnrolmentSnapshot.objects.create(
            school=self.school, snapshot_date=date(2018, 1, 1), students=520,
        )
        resp = self.client.get(f"/api/v1/schools/{self.school.moe_code}/")
        history = resp.json()["enrolment_history"]
        self.assertEqual(
            [row["date"] for row in history],
            ["2018-01-01", "2025-03-01"],
        )
        self.assertEqual(history[0]["students"], 520)
