"""Tests for school name repair utilities."""

from django.test import TestCase

from hansard.models import SchoolAlias
from parliament.services.name_repairer import repair_school_name
from schools.models import School


class RepairSchoolNameTests(TestCase):

    def setUp(self):
        self.school = School.objects.create(
            moe_code="CBD7094",
            name="Sekolah Jenis Kebangsaan (Tamil) Ladang Mentakab",
            short_name="SJK(T) Ladang Mentakab",
            state="Pahang", ppd="Temerloh",
        )
        SchoolAlias.objects.create(
            school=self.school,
            alias="Ladang Mentakab",
            alias_normalized="ladang mentakab",
            alias_type="COMMON",
        )

    def test_comma_removal_finds_match(self):
        result = repair_school_name("SJK(T) Ladang, Mentakab")
        self.assertIsNotNone(result)
        self.assertEqual(result["school_code"], "CBD7094")
        self.assertEqual(result["repaired_name"], "SJK(T) Ladang Mentakab")

    def test_exact_name_returns_match(self):
        result = repair_school_name("SJK(T) Ladang Mentakab")
        self.assertIsNotNone(result)
        self.assertEqual(result["school_code"], "CBD7094")

    def test_unresolvable_returns_none(self):
        result = repair_school_name("SJK(T) Nonexistent School")
        self.assertIsNone(result)

    def test_strips_trailing_punctuation(self):
        result = repair_school_name("SJK(T) Ladang Mentakab.")
        self.assertIsNotNone(result)

    def test_drops_filler_words(self):
        result = repair_school_name("SJK(T) di Ladang Mentakab")
        self.assertIsNotNone(result)
        self.assertEqual(result["school_code"], "CBD7094")

    def test_no_prefix_returns_none(self):
        result = repair_school_name("Random School Name")
        self.assertIsNone(result)

    def test_prefix_only_returns_none(self):
        result = repair_school_name("SJK(T)")
        self.assertIsNone(result)
