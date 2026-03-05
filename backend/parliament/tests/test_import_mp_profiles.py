"""Tests for the import_mp_profiles management command."""

from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase

from parliament.models import MP
from schools.models import Constituency


MOCK_LISTING = [
    {
        "name": "YB Dato' Test MP",
        "constituency_code": "P078",
        "party": "PKR",
        "photo_url": "https://parlimen.gov.my/images/test.jpg",
        "parlimen_profile_id": "123",
    },
]

MOCK_PROFILE = {
    "phone": "03-12345678",
    "fax": "03-87654321",
    "email": "test@parlimen.gov.my",
    "service_centre_address": "123 Jalan Test",
    "facebook_url": "https://www.facebook.com/testmp",
}

MOCK_MYMP_SLUGS = {
    "dato' test mp": "dato-test-mp",
}


@patch("parliament.management.commands.import_mp_profiles.fetch_parlimen_listing")
@patch("parliament.management.commands.import_mp_profiles.fetch_parlimen_profile")
@patch("parliament.management.commands.import_mp_profiles.fetch_mymp_sitemap")
class TestImportMPProfiles(TestCase):

    def setUp(self):
        self.constituency_p078 = Constituency.objects.create(
            code="P078", name="Hulu Langat", state="Selangor",
        )
        self.constituency_p079 = Constituency.objects.create(
            code="P079", name="Sepang", state="Selangor",
        )

    def test_imports_mps(self, mock_sitemap, mock_profile, mock_listing):
        """Verifies MP is created with correct fields."""
        mock_listing.return_value = MOCK_LISTING
        mock_profile.return_value = MOCK_PROFILE
        mock_sitemap.return_value = MOCK_MYMP_SLUGS

        out = StringIO()
        call_command("import_mp_profiles", stdout=out)

        self.assertEqual(MP.objects.count(), 1)
        mp = MP.objects.first()
        self.assertEqual(mp.name, "YB Dato' Test MP")
        self.assertEqual(mp.constituency, self.constituency_p078)
        self.assertEqual(mp.party, "PKR")
        self.assertEqual(mp.phone, "03-12345678")
        self.assertEqual(mp.fax, "03-87654321")
        self.assertEqual(mp.email, "test@parlimen.gov.my")
        self.assertEqual(mp.facebook_url, "https://www.facebook.com/testmp")
        self.assertEqual(mp.service_centre_address, "123 Jalan Test")
        self.assertEqual(mp.parlimen_profile_id, "123")
        self.assertEqual(mp.mymp_slug, "dato-test-mp")
        self.assertIn("Created", out.getvalue())

    def test_dry_run_does_not_save(self, mock_sitemap, mock_profile, mock_listing):
        """Verifies no DB records with --dry-run, output contains 'DRY RUN'."""
        mock_listing.return_value = MOCK_LISTING
        mock_profile.return_value = MOCK_PROFILE
        mock_sitemap.return_value = MOCK_MYMP_SLUGS

        out = StringIO()
        call_command("import_mp_profiles", "--dry-run", stdout=out)

        self.assertEqual(MP.objects.count(), 0)
        self.assertIn("DRY RUN", out.getvalue())

    def test_skips_unknown_constituency(self, mock_sitemap, mock_profile, mock_listing):
        """Verifies MP with P999 code is not created."""
        mock_listing.return_value = [
            {
                "name": "YB Unknown",
                "constituency_code": "P999",
                "party": "IND",
                "photo_url": "",
                "parlimen_profile_id": "999",
            },
        ]
        mock_profile.return_value = {}
        mock_sitemap.return_value = {}

        out = StringIO()
        call_command("import_mp_profiles", stdout=out)

        self.assertEqual(MP.objects.count(), 0)
        self.assertIn("Skipping", out.getvalue())
