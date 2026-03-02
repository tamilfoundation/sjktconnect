"""Tests for SchoolLeader model."""

from django.db import IntegrityError
from django.test import TestCase

from schools.models import School, SchoolLeader


class SchoolLeaderModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.school = School.objects.create(
            moe_code="JBD0050",
            name="SJK(T) LADANG BIKAM",
            short_name="SJK(T) Test School",
            state="Johor",
        )

    def test_create_leader_each_role(self):
        """Can create a leader with each of the four roles."""
        for role, display in SchoolLeader.ROLE_CHOICES:
            leader = SchoolLeader.objects.create(
                school=self.school, role=role, name=f"Test {display}"
            )
            assert leader.pk is not None
            assert leader.role == role

    def test_str_representation(self):
        leader = SchoolLeader.objects.create(
            school=self.school, role="board_chair", name="En. Suresh"
        )
        assert str(leader) == "Board Chairman: En. Suresh (SJK(T) Test School)"

    def test_phone_and_email_optional(self):
        """Phone and email default to empty string (blank=True)."""
        leader = SchoolLeader.objects.create(
            school=self.school, role="headmaster", name="Pn. Kavitha"
        )
        assert leader.phone == ""
        assert leader.email == ""

    def test_unique_active_role_per_school(self):
        """Cannot have two active leaders with the same role for the same school."""
        SchoolLeader.objects.create(
            school=self.school, role="board_chair", name="En. Suresh"
        )
        with self.assertRaises(IntegrityError):
            SchoolLeader.objects.create(
                school=self.school, role="board_chair", name="En. Kumar"
            )

    def test_inactive_plus_active_same_role(self):
        """Can have an inactive and active leader with the same role."""
        SchoolLeader.objects.create(
            school=self.school, role="headmaster", name="Old HM", is_active=False
        )
        active = SchoolLeader.objects.create(
            school=self.school, role="headmaster", name="New HM", is_active=True
        )
        assert active.pk is not None

    def test_two_inactive_same_role(self):
        """Can have multiple inactive leaders with the same role."""
        SchoolLeader.objects.create(
            school=self.school, role="pta_chair", name="Old PTA 1", is_active=False
        )
        second = SchoolLeader.objects.create(
            school=self.school, role="pta_chair", name="Old PTA 2", is_active=False
        )
        assert second.pk is not None
