"""Tests for newswatch school-name matching, focused on the PJS section-code
spacing case: an article may write "PJS1" while the MOE name is "PJS 1"
(and vice versa). Matching must bridge that letter↔digit boundary.
"""

from django.test import TestCase

from schools.models import School
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
