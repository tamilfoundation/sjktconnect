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


class WithoutLadangAliasTests(TestCase):
    """Test 'without Ladang' alias variant for estate schools."""

    @classmethod
    def setUpTestData(cls):
        cls.constituency = Constituency.objects.create(
            code="P099", name="Hulu Selangor", state="Selangor"
        )

    def test_generates_without_ladang_variant(self):
        """Schools with 'Ladang' should get a variant without it."""
        school = School.objects.create(
            moe_code="BBD0099",
            name="SEKOLAH JENIS KEBANGSAAN (TAMIL) LADANG SERENDAH",
            short_name="SJK(T) Ladang Serendah",
            state="Selangor",
            constituency=self.constituency,
        )
        aliases = generate_aliases_for_school(school)
        alias_texts = [a["alias_normalized"] for a in aliases]
        self.assertIn(
            "sjk(t) serendah",
            alias_texts,
            f"Expected 'sjk(t) serendah' alias, got: {alias_texts}",
        )

    def test_no_ladang_no_extra_alias(self):
        """Schools without 'Ladang' should NOT get a without-Ladang variant."""
        school = School.objects.create(
            moe_code="BBD0100",
            name="SEKOLAH JENIS KEBANGSAAN (TAMIL) TAMAN MELAWATI",
            short_name="SJK(T) Taman Melawati",
            state="Selangor",
            constituency=self.constituency,
        )
        aliases = generate_aliases_for_school(school)
        alias_texts = [a["alias_normalized"] for a in aliases]
        # No alias should match the "without Ladang" pattern since there is no Ladang
        self.assertNotIn("sjk(t) taman melawati".replace("taman ", ""), alias_texts)

    def test_ladang_bikam_existing_school(self):
        """The existing test school Ladang Bikam should get 'SJK(T) Bikam' alias."""
        school = School.objects.create(
            moe_code="JBD0099",
            name="SEKOLAH JENIS KEBANGSAAN (TAMIL) LADANG BIKAM",
            short_name="SJK(T) Ladang Bikam",
            state="Johor",
            constituency=self.constituency,
        )
        aliases = generate_aliases_for_school(school)
        alias_texts = [a["alias_normalized"] for a in aliases]
        self.assertIn("sjk(t) bikam", alias_texts)


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


class JenderataAliasesMigrationTest(TestCase):
    """Sprint 24 #10d — verify the 0008 data migration logic creates the
    expected 'Jenderata' (with-e) aliases for the 4 'Jendarata' schools.

    Calls the migration's add_jenderata_aliases() helper directly with
    the test's apps registry — same shape Django uses when running the
    RunPython operation.
    """

    def setUp(self):
        self.constituency = Constituency.objects.create(
            code="P078", name="Tanjung Karang", state="Selangor",
        )
        for moe_code, suffix in [
            ("ABDB002", "Jendarata 1"),
            ("ABDB003", "Jendarata Bhg 2"),
            ("ABDB004", "Jendarata Bhg 3"),
            ("ABDB006", "Jendarata Bahagian Alpha Bernam"),
        ]:
            School.objects.create(
                moe_code=moe_code,
                name=f"Sekolah Jenis Kebangsaan (Tamil) Ladang {suffix}",
                short_name=f"SJK(T) Ladang {suffix}",
                state="Selangor",
                constituency=self.constituency,
            )

    def _load_migration(self):
        # Module name starts with a digit so direct import doesn't work;
        # importlib resolves it.
        import importlib
        return importlib.import_module(
            "hansard.migrations.0008_add_jenderata_spelling_aliases"
        )

    def test_adds_jenderata_aliases_for_each_school(self):
        from django.apps import apps as _apps
        self._load_migration().add_jenderata_aliases(_apps, None)
        for moe_code in ("ABDB002", "ABDB003", "ABDB004", "ABDB006"):
            school = School.objects.get(moe_code=moe_code)
            aliases = SchoolAlias.objects.filter(
                school=school,
                alias_type=SchoolAlias.AliasType.HANSARD,
                alias_normalized__contains="jenderata",
            )
            self.assertGreater(
                aliases.count(), 0,
                f"No Jenderata alias created for {moe_code}",
            )

    def test_migration_is_idempotent(self):
        from django.apps import apps as _apps
        mod = self._load_migration()
        mod.add_jenderata_aliases(_apps, None)
        count1 = SchoolAlias.objects.filter(
            alias_type=SchoolAlias.AliasType.HANSARD,
            alias_normalized__contains="jenderata",
        ).count()
        mod.add_jenderata_aliases(_apps, None)
        count2 = SchoolAlias.objects.filter(
            alias_type=SchoolAlias.AliasType.HANSARD,
            alias_normalized__contains="jenderata",
        ).count()
        self.assertEqual(count1, count2)
        self.assertGreater(count1, 0)

    def test_reverse_removes_added_aliases(self):
        from django.apps import apps as _apps
        mod = self._load_migration()
        mod.add_jenderata_aliases(_apps, None)
        added_count = SchoolAlias.objects.filter(
            alias_type=SchoolAlias.AliasType.HANSARD,
            alias_normalized__contains="jenderata",
        ).count()
        self.assertGreater(added_count, 0)

        mod.remove_jenderata_aliases(_apps, None)
        remaining = SchoolAlias.objects.filter(
            alias_type=SchoolAlias.AliasType.HANSARD,
            alias_normalized__contains="jenderata",
        ).count()
        self.assertEqual(remaining, 0)


class LadangLabuBahagianAliasesMigrationTest(TestCase):
    """Sprint 27 #2 — verify the 0010 migration creates the NBD4079
    Bahagian/Division/Bhg variants that bridge the news-matcher gap.
    """

    def setUp(self):
        self.constituency = Constituency.objects.create(
            code="P132", name="Seremban", state="Negeri Sembilan",
        )
        School.objects.create(
            moe_code="NBD4079",
            name="Sekolah Jenis Kebangsaan (Tamil) Ladang Labu Bhg 4",
            short_name="SJK(T) Ladang Labu Bhg 4",
            state="Negeri Sembilan",
            constituency=self.constituency,
        )

    def _load_migration(self):
        import importlib
        return importlib.import_module(
            "hansard.migrations.0010_ladang_labu_bahagian_aliases"
        )

    def test_adds_bahagian_division_variants_for_nbd4079(self):
        from django.apps import apps as _apps
        self._load_migration().add_aliases(_apps, None)
        school = School.objects.get(moe_code="NBD4079")
        aliases = SchoolAlias.objects.filter(
            school=school,
            alias_type=SchoolAlias.AliasType.HANSARD,
        )
        self.assertGreaterEqual(aliases.count(), 10)
        # Spot-check the critical variants the news matcher was missing.
        normalized = set(aliases.values_list("alias_normalized", flat=True))
        self.assertIn("sjk(t) ladang labu bahagian 4", normalized)
        self.assertIn("sjk(t) ladang labu division 4", normalized)
        self.assertIn("ladang labu bahagian 4", normalized)

    def test_migration_is_idempotent(self):
        from django.apps import apps as _apps
        mod = self._load_migration()
        mod.add_aliases(_apps, None)
        count1 = SchoolAlias.objects.filter(
            school__moe_code="NBD4079",
            alias_type=SchoolAlias.AliasType.HANSARD,
        ).count()
        mod.add_aliases(_apps, None)
        count2 = SchoolAlias.objects.filter(
            school__moe_code="NBD4079",
            alias_type=SchoolAlias.AliasType.HANSARD,
        ).count()
        self.assertEqual(count1, count2)
        self.assertGreater(count1, 0)

    def test_reverse_removes_added_aliases(self):
        from django.apps import apps as _apps
        mod = self._load_migration()
        mod.add_aliases(_apps, None)
        mod.remove_aliases(_apps, None)
        remaining = SchoolAlias.objects.filter(
            school__moe_code="NBD4079",
            alias_type=SchoolAlias.AliasType.HANSARD,
        ).count()
        self.assertEqual(remaining, 0)
