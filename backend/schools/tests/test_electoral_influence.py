"""Tests for electoral influence API response."""

from django.test import TestCase
from rest_framework.test import APIClient

from schools.models import Constituency


class ElectoralInfluenceAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.constituency = Constituency.objects.create(
            code="P075",
            name="Bagan Datuk",
            state="PERAK",
            mp_name="Zahid Hamidi",
            mp_party="BN",
            ge15_winning_margin=348,
            ge15_total_voters=58183,
            ge15_indian_voter_pct=22.0,
        )

    def test_electoral_influence_kingmaker(self):
        """Constituency with high ratio (>5x) returns 'kingmaker' verdict."""
        resp = self.client.get(f"/api/v1/constituencies/{self.constituency.code}/")
        self.assertEqual(resp.status_code, 200)
        influence = resp.json()["electoral_influence"]
        self.assertIsNotNone(influence)
        self.assertEqual(influence["winning_margin"], 348)
        self.assertEqual(influence["indian_voters"], 12800)  # 58183 * 22 / 100
        self.assertGreater(influence["ratio"], 5)
        self.assertEqual(influence["verdict"], "kingmaker")

    def test_electoral_influence_significant(self):
        """Constituency with ratio 1-5x returns 'significant' verdict."""
        self.constituency.ge15_winning_margin = 5000
        self.constituency.ge15_total_voters = 80000
        self.constituency.ge15_indian_voter_pct = 10.0
        self.constituency.save()

        resp = self.client.get(f"/api/v1/constituencies/{self.constituency.code}/")
        influence = resp.json()["electoral_influence"]
        self.assertIsNotNone(influence)
        # 80000 * 10% = 8000 / 5000 = 1.6x
        self.assertEqual(influence["verdict"], "significant")
        self.assertGreaterEqual(influence["ratio"], 1)
        self.assertLessEqual(influence["ratio"], 5)

    def test_electoral_influence_safe_seat(self):
        """Constituency with ratio <1x returns 'safe_seat' verdict."""
        self.constituency.ge15_winning_margin = 30000
        self.constituency.ge15_total_voters = 80000
        self.constituency.ge15_indian_voter_pct = 5.0
        self.constituency.save()

        resp = self.client.get(f"/api/v1/constituencies/{self.constituency.code}/")
        influence = resp.json()["electoral_influence"]
        self.assertIsNotNone(influence)
        # 80000 * 5% = 4000 / 30000 = 0.1x
        self.assertEqual(influence["verdict"], "safe_seat")
        self.assertLess(influence["ratio"], 1)

    def test_electoral_influence_null_when_no_data(self):
        """Constituency without election data returns null influence."""
        self.constituency.ge15_winning_margin = None
        self.constituency.ge15_total_voters = None
        self.constituency.ge15_indian_voter_pct = None
        self.constituency.save()

        resp = self.client.get(f"/api/v1/constituencies/{self.constituency.code}/")
        self.assertIsNone(resp.json()["electoral_influence"])

    def test_ge15_fields_in_response(self):
        """GE15 raw fields are included in the API response."""
        resp = self.client.get(f"/api/v1/constituencies/{self.constituency.code}/")
        data = resp.json()
        self.assertEqual(data["ge15_winning_margin"], 348)
        self.assertEqual(data["ge15_total_voters"], 58183)
        self.assertEqual(float(data["ge15_indian_voter_pct"]), 22.0)
