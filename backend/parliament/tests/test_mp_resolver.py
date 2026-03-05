"""Tests for MP resolver — cross-references Gemini output against MP database."""

from django.test import TestCase

from parliament.models import MP
from schools.models import Constituency
from parliament.services.mp_resolver import resolve_mp


class ResolveMPTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.constituency = Constituency.objects.create(
            code="P078", name="Klang", state="Selangor",
        )
        cls.mp = MP.objects.create(
            constituency=cls.constituency,
            name="Tuan Ganabatirau a/l Veraman",
            party="PH(DAP)",
        )

    def test_resolve_by_constituency_name(self):
        """Should match MP when constituency name matches."""
        result = resolve_mp(mp_name="", mp_constituency="Klang", mp_party="")
        self.assertEqual(result["mp_name"], "Tuan Ganabatirau a/l Veraman")
        self.assertEqual(result["mp_party"], "PH(DAP)")

    def test_resolve_by_constituency_code(self):
        """Should match MP when constituency code matches."""
        result = resolve_mp(mp_name="", mp_constituency="P078", mp_party="")
        self.assertEqual(result["mp_name"], "Tuan Ganabatirau a/l Veraman")

    def test_resolve_by_name_substring(self):
        """Should match MP when name contains a substring match."""
        result = resolve_mp(mp_name="Ganabatirau", mp_constituency="", mp_party="")
        self.assertEqual(result["mp_constituency"], "Klang")
        self.assertEqual(result["mp_party"], "PH(DAP)")

    def test_no_match_returns_original(self):
        """When no MP matches, return the original values unchanged."""
        result = resolve_mp(mp_name="Unknown Person", mp_constituency="Unknown", mp_party="")
        self.assertEqual(result["mp_name"], "Unknown Person")
        self.assertEqual(result["mp_constituency"], "Unknown")
        self.assertEqual(result["mp_party"], "")

    def test_enriches_party_only(self):
        """When name matches but party is empty, fill in party from DB."""
        result = resolve_mp(mp_name="Tuan Ganabatirau a/l Veraman", mp_constituency="Klang", mp_party="")
        self.assertEqual(result["mp_party"], "PH(DAP)")

    def test_does_not_overwrite_existing_party(self):
        """When party is already set, don't overwrite it."""
        result = resolve_mp(mp_name="Ganabatirau", mp_constituency="Klang", mp_party="BN")
        self.assertEqual(result["mp_party"], "BN")
