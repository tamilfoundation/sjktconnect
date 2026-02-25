"""Tests for seed_aliases management command."""

from django.core.management import call_command
from django.test import TestCase

from hansard.management.commands.seed_aliases import (
    generate_aliases_for_school,
    normalize_alias,
)
from hansard.models import SchoolAlias
from schools.models import Constituency, School


class NormalizeAliasTests(TestCase):
    """Test alias normalisation."""

    def test_lowercase(self):
        self.assertEqual(normalize_alias("SJK(T) Ladang Bikam"), "sjk(t) ladang bikam")

    def test_collapse_whitespace(self):
        self.assertEqual(normalize_alias("ladang   bikam"), "ladang bikam")

    def test_strip(self):
        self.assertEqual(normalize_alias("  bikam  "), "bikam")

    def test_empty(self):
        self.assertEqual(normalize_alias(""), "")


class GenerateAliasesTests(TestCase):
    """Test alias generation for individual schools."""

    @classmethod
    def setUpTestData(cls):
        cls.constituency = Constituency.objects.create(
            code="P140", name="Segamat", state="Johor"
        )
        cls.school = School.objects.create(
            moe_code="JBD0050",
            name="SEKOLAH JENIS KEBANGSAAN (TAMIL) LADANG BIKAM",
            short_name="SJK(T) Ladang Bikam",
            state="Johor",
            constituency=cls.constituency,
        )

    def test_generates_official_alias(self):
        aliases = generate_aliases_for_school(self.school)
        types = {a["alias_type"] for a in aliases}
        self.assertIn(SchoolAlias.AliasType.OFFICIAL, types)

    def test_generates_short_alias(self):
        aliases = generate_aliases_for_school(self.school)
        types = {a["alias_type"] for a in aliases}
        self.assertIn(SchoolAlias.AliasType.SHORT, types)

    def test_generates_stripped_name(self):
        """Should generate 'Ladang Bikam' without SJK(T) prefix."""
        aliases = generate_aliases_for_school(self.school)
        normalized_values = {a["alias_normalized"] for a in aliases}
        self.assertIn("ladang bikam", normalized_values)

    def test_generates_sjkt_variant(self):
        """Should generate 'SJKT Ladang Bikam' variant."""
        aliases = generate_aliases_for_school(self.school)
        normalized_values = {a["alias_normalized"] for a in aliases}
        self.assertIn("sjkt ladang bikam", normalized_values)

    def test_generates_official_stripped(self):
        """Should strip 'SEKOLAH JENIS KEBANGSAAN (TAMIL)' from official name."""
        aliases = generate_aliases_for_school(self.school)
        normalized_values = {a["alias_normalized"] for a in aliases}
        # "LADANG BIKAM" normalised
        self.assertIn("ladang bikam", normalized_values)

    def test_no_duplicate_normalized(self):
        """No two aliases should have the same normalized form."""
        aliases = generate_aliases_for_school(self.school)
        normalized_values = [a["alias_normalized"] for a in aliases]
        self.assertEqual(len(normalized_values), len(set(normalized_values)))

    def test_alias_count(self):
        """Should generate at least 3 aliases (official, short, stripped, sjkt variant)."""
        aliases = generate_aliases_for_school(self.school)
        self.assertGreaterEqual(len(aliases), 3)


class SeedAliasesCommandTests(TestCase):
    """Test the seed_aliases management command."""

    @classmethod
    def setUpTestData(cls):
        cls.constituency = Constituency.objects.create(
            code="P140", name="Segamat", state="Johor"
        )

    def setUp(self):
        self.school1 = School.objects.create(
            moe_code="JBD0050",
            name="SEKOLAH JENIS KEBANGSAAN (TAMIL) LADANG BIKAM",
            short_name="SJK(T) Ladang Bikam",
            state="Johor",
            constituency=self.constituency,
        )
        self.school2 = School.objects.create(
            moe_code="ABD0010",
            name="SEKOLAH JENIS KEBANGSAAN (TAMIL) BATU ARANG",
            short_name="SJK(T) Batu Arang",
            state="Selangor",
            constituency=self.constituency,
        )

    def test_creates_aliases(self):
        call_command("seed_aliases")
        self.assertGreater(SchoolAlias.objects.count(), 0)

    def test_aliases_for_both_schools(self):
        call_command("seed_aliases")
        school1_aliases = SchoolAlias.objects.filter(school=self.school1)
        school2_aliases = SchoolAlias.objects.filter(school=self.school2)
        self.assertGreater(school1_aliases.count(), 0)
        self.assertGreater(school2_aliases.count(), 0)

    def test_idempotent(self):
        """Running twice should not create duplicates."""
        call_command("seed_aliases")
        count1 = SchoolAlias.objects.count()
        call_command("seed_aliases")
        count2 = SchoolAlias.objects.count()
        self.assertEqual(count1, count2)

    def test_clear_flag(self):
        """--clear should delete non-HANSARD aliases then re-seed."""
        call_command("seed_aliases")
        # Manually add a HANSARD alias
        SchoolAlias.objects.create(
            school=self.school1,
            alias="SJKT Bikam Estate",
            alias_normalized="sjkt bikam estate",
            alias_type=SchoolAlias.AliasType.HANSARD,
        )
        total_before = SchoolAlias.objects.count()

        call_command("seed_aliases", "--clear")

        # HANSARD alias should be preserved
        self.assertTrue(
            SchoolAlias.objects.filter(alias_type=SchoolAlias.AliasType.HANSARD).exists()
        )
        # Other aliases should be re-created
        self.assertGreater(SchoolAlias.objects.count(), 1)
