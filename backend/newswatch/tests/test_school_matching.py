"""Tests for newswatch school-name matching.

Two layers covered:
- _generate_name_variants — bridges PJS1/PJS 1, parens/quotes, with/
  without "Ladang" prefix.
- _resolve_school_codes — six in-table strategies plus the new
  Strategy 1.5 SchoolAlias lookup (Sprint 24 #10h).
"""

from django.test import TestCase

from schools.models import Constituency, School
from hansard.models import SchoolAlias
from newswatch.services.news_analyser import (
    _generate_name_variants,
    _resolve_school_codes,
)


class GenerateNameVariantsTest(TestCase):
    """Unit tests for the letter↔digit bridging variants."""

    def test_joined_yields_spaced_variant(self):
        variants = _generate_name_variants("PJS1")
        self.assertIn("PJS 1", variants)

    def test_spaced_yields_joined_variant(self):
        variants = _generate_name_variants("PJS 1")
        self.assertIn("PJS1", variants)

    def test_bridging_is_general(self):
        # Not PJS-specific: any letter+digit lot/section number bridges.
        self.assertIn("Boh 1", _generate_name_variants("Boh1"))


class ResolvePjsSchoolTest(TestCase):
    """End-to-end: Gemini's name resolves to the right school regardless of
    PJS spacing, and even against the legacy mis-cased 'Pjs 1' record.
    """

    def _make_school(self, short_name, moe_code="WBA1234"):
        return School.objects.create(
            moe_code=moe_code,
            name=f"Sekolah Jenis Kebangsaan (Tamil) {short_name}",
            short_name=short_name,
            state="Selangor",
        )

    def test_joined_mention_matches_spaced_name(self):
        school = self._make_school("SJK(T) PJS 1")
        resolved = _resolve_school_codes([{"name": "SJK(T) PJS1", "moe_code": ""}])
        self.assertEqual(resolved[0]["moe_code"], school.moe_code)

    def test_spaced_mention_matches_spaced_name(self):
        school = self._make_school("SJK(T) PJS 1")
        resolved = _resolve_school_codes([{"name": "SJK(T) PJS 1", "moe_code": ""}])
        self.assertEqual(resolved[0]["moe_code"], school.moe_code)

    def test_joined_mention_matches_legacy_miscased_name(self):
        # Until the live record is corrected it still reads "Pjs 1"; the
        # case-insensitive match plus the spaced variant must still resolve it.
        school = self._make_school("SJK(T) Pjs 1")
        resolved = _resolve_school_codes([{"name": "SJK(T) PJS1", "moe_code": ""}])
        self.assertEqual(resolved[0]["moe_code"], school.moe_code)


class VariantGeneratorBracketAndLadangTest(TestCase):
    """Sprint 24 #10h — bracket⇄quote and drop/add-Ladang variants."""

    def test_paren_yields_single_quote_variant(self):
        variants = _generate_name_variants("West Country (Timur)")
        self.assertIn("West Country 'Timur'", variants)

    def test_single_quote_yields_paren_variant(self):
        variants = _generate_name_variants("West Country 'Timur'")
        self.assertIn("West Country (Timur)", variants)

    def test_ladang_prefix_stripped(self):
        variants = _generate_name_variants("Ladang West Country")
        self.assertIn("West Country", variants)

    def test_ldg_prefix_stripped(self):
        variants = _generate_name_variants("Ldg West Country")
        self.assertIn("West Country", variants)

    def test_bare_name_yields_ladang_and_ldg_prefixed_variants(self):
        variants = _generate_name_variants("West Country")
        self.assertIn("Ladang West Country", variants)
        self.assertIn("Ldg West Country", variants)

    def test_already_ladang_prefixed_does_not_double_prefix(self):
        variants = _generate_name_variants("Ladang Boh 1")
        self.assertNotIn("Ladang Ladang Boh 1", variants)
        self.assertNotIn("Ldg Ladang Boh 1", variants)


class SchoolAliasLookupTest(TestCase):
    """Sprint 24 #10h — Strategy 1.5 consults the SchoolAlias table.

    Critical: this activates 1,500+ existing seeded aliases AND every
    HANSARD-source alias added via data migrations (Jenderata, KKB,
    St Teresa, West Country) for the news matcher.
    """

    def setUp(self):
        self.constituency = Constituency.objects.create(
            code="P140", name="Segamat", state="Johor",
        )

    def _make_school(self, moe_code, short_name):
        return School.objects.create(
            moe_code=moe_code,
            name=f"Sekolah Jenis Kebangsaan (Tamil) {short_name.replace('SJK(T) ', '')}",
            short_name=short_name,
            state="Johor",
            constituency=self.constituency,
        )

    def _add_alias(self, school, alias_text):
        import re
        normalized = re.sub(r"\s+", " ", alias_text.lower().strip())
        SchoolAlias.objects.create(
            school=school,
            alias=alias_text,
            alias_normalized=normalized,
            alias_type=SchoolAlias.AliasType.HANSARD,
        )

    def test_alias_resolves_when_short_name_differs(self):
        # DB short_name uses mixed abbreviation; article uses full form.
        # The variant generator doesn't produce the mixed form, but the
        # alias does — Strategy 1.5 catches it before falling through.
        school = self._make_school("JBD7068", "SJK(T) Ladang Sg Muar")
        self._add_alias(school, "SJK(T) Ladang Sungai Muar")
        resolved = _resolve_school_codes([
            {"name": "SJK(T) Ladang Sungai Muar", "moe_code": ""}
        ])
        self.assertEqual(resolved[0]["moe_code"], "JBD7068")

    def test_alias_lookup_uses_normalised_form(self):
        # Case-insensitive + whitespace-collapsed lookup against the alias.
        school = self._make_school("JBD7068", "SJK(T) Ladang Sg Muar")
        self._add_alias(school, "SJK(T) Ladang Sungai Muar")
        resolved = _resolve_school_codes([
            {"name": "  sjk(t)  ladang   sungai  muar  ", "moe_code": ""}
        ])
        self.assertEqual(resolved[0]["moe_code"], "JBD7068")

    def test_alias_lookup_falls_through_when_no_match(self):
        # No alias for this name → falls through to the existing
        # strategies → still returns moe_code='' if nothing matches.
        self._make_school("JBD7068", "SJK(T) Ladang Sg Muar")
        resolved = _resolve_school_codes([
            {"name": "SJK(T) Nonexistent School", "moe_code": ""}
        ])
        self.assertEqual(resolved[0]["moe_code"], "")

    def test_alias_lookup_distinctive_form_matches_too(self):
        # Alias is the bare distinctive ("Ladang Sungai Muar" without prefix).
        # Article name has the SJK(T) prefix. Lookup must try both.
        school = self._make_school("JBD7068", "SJK(T) Ladang Sg Muar")
        self._add_alias(school, "Ladang Sungai Muar")
        resolved = _resolve_school_codes([
            {"name": "SJK(T) Ladang Sungai Muar", "moe_code": ""}
        ])
        self.assertEqual(resolved[0]["moe_code"], "JBD7068")


class ScreenshotFailureRegressionTest(TestCase):
    """End-to-end regression for the 4 specific match failures seen in
    production news articles (June 2026):

    - Ladang Sungai Muar — fixed by Strategy 1.5 + existing SHORT alias
    - West Country (Timur) — fixed by bracket variant + new alias
    - Kuala Kubu Baru — fixed by new alias (single-letter typo)
    - St. Theresa Convent — fixed by new alias (Theresa/Teresa drift)
    """

    def setUp(self):
        self.constituency = Constituency.objects.create(
            code="P140", name="Segamat", state="Johor",
        )

    def _make_school(self, moe_code, short_name, state="Johor"):
        return School.objects.create(
            moe_code=moe_code,
            name=f"Sekolah Jenis Kebangsaan (Tamil) {short_name.replace('SJK(T) ', '')}",
            short_name=short_name,
            state=state,
            constituency=self.constituency,
        )

    def _seed_alias(self, school, alias_text):
        import re
        SchoolAlias.objects.create(
            school=school,
            alias=alias_text,
            alias_normalized=re.sub(r"\s+", " ", alias_text.lower().strip()),
            alias_type=SchoolAlias.AliasType.HANSARD,
        )

    def test_ladang_sungai_muar_resolves(self):
        school = self._make_school("JBD7068", "SJK(T) Ladang Sg Muar")
        # Existing seeded alias shape (seed_aliases SHORT type).
        self._seed_alias(school, "SJK(T) Ladang Sungai Muar")
        resolved = _resolve_school_codes([
            {"name": "SJK(T) Ladang Sungai Muar", "moe_code": ""}
        ])
        self.assertEqual(resolved[0]["moe_code"], "JBD7068")

    def test_west_country_timur_resolves(self):
        school = self._make_school("BBD4063", "SJK(T) Ldg West Country 'Timur'")
        # Alias rows from hansard/0009 migration.
        self._seed_alias(school, "SJK(T) West Country (Timur)")
        resolved = _resolve_school_codes([
            {"name": "SJK(T) West Country (Timur)", "moe_code": ""}
        ])
        self.assertEqual(resolved[0]["moe_code"], "BBD4063")

    def test_kuala_kubu_baru_resolves(self):
        school = self._make_school("BBD5045", "SJK(T) Kuala Kubu Bharu", state="Selangor")
        self._seed_alias(school, "SJK(T) Kuala Kubu Baru")
        resolved = _resolve_school_codes([
            {"name": "SJK(T) Kuala Kubu Baru", "moe_code": ""}
        ])
        self.assertEqual(resolved[0]["moe_code"], "BBD5045")

    def test_st_theresa_convent_resolves(self):
        school = self._make_school("ABD6102", "SJK(T) St Teresa's Convent", state="Perak")
        self._seed_alias(school, "SJK(T) St. Theresa Convent")
        resolved = _resolve_school_codes([
            {"name": "SJK(T) St. Theresa Convent", "moe_code": ""}
        ])
        self.assertEqual(resolved[0]["moe_code"], "ABD6102")
