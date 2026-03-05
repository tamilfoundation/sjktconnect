from pathlib import Path
from django.test import TestCase
from parliament.services.mp_scraper import (
    parse_parlimen_listing,
    parse_parlimen_profile,
    parse_mymp_sitemap,
)

FIXTURES = Path(__file__).parent / "fixtures"


class ParlimenListingParserTest(TestCase):
    def test_parse_listing(self):
        html = (FIXTURES / "parlimen_listing.html").read_text(encoding="utf-8")
        mps = parse_parlimen_listing(html)
        self.assertGreaterEqual(len(mps), 2)
        mp = next(m for m in mps if m["constituency_code"] == "P078")
        self.assertEqual(mp["name"], "YB Dato' Dr. Ramli bin Dato' Mohd Nor")
        self.assertEqual(mp["party"], "BN")
        self.assertIn("P078", mp["photo_url"])
        self.assertEqual(mp["parlimen_profile_id"], "4250")


class ParlimenProfileParserTest(TestCase):
    def test_parse_profile_contact_details(self):
        html = (FIXTURES / "parlimen_profile.html").read_text(encoding="utf-8")
        details = parse_parlimen_profile(html)
        self.assertEqual(details["phone"], "03-2601 7222")
        self.assertEqual(details["email"], "ramli@parlimen.gov.my")
        self.assertIn("Jalan Meru", details["service_centre_address"])

    def test_parse_profile_facebook(self):
        html = (FIXTURES / "parlimen_profile.html").read_text(encoding="utf-8")
        details = parse_parlimen_profile(html)
        self.assertTrue(details["facebook_url"].startswith("https://"))
        self.assertIn("facebook.com", details["facebook_url"])


class MyMPSitemapParserTest(TestCase):
    def test_parse_sitemap(self):
        html = (FIXTURES / "mymp_sitemap.html").read_text(encoding="utf-8")
        slugs = parse_mymp_sitemap(html)
        self.assertGreaterEqual(len(slugs), 2)
        self.assertEqual(slugs["ramli bin dato' mohd nor"], "ramli-bin-dato-mohd-nor")
        for slug in slugs.values():
            self.assertNotIn(" ", slug)
