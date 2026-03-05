from django.test import TestCase
from rest_framework.test import APIClient

from schools.models import Constituency
from parliament.models import MP


class ConstituencyMPAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.constituency = Constituency.objects.create(
            code="P078",
            name="Cameron Highlands",
            state="Pahang",
            mp_name="YB Dato' Dr. Ramli",
            mp_party="BN",
        )

    def test_constituency_detail_includes_mp_null(self):
        resp = self.client.get("/api/v1/constituencies/P078/")
        self.assertEqual(resp.status_code, 200)
        self.assertIsNone(resp.data["mp"])

    def test_constituency_detail_includes_mp_data(self):
        MP.objects.create(
            constituency=self.constituency,
            name="YB Dato' Dr. Ramli bin Dato' Mohd Nor",
            photo_url="https://parlimen.gov.my/images/P078.jpg",
            party="BN",
            email="ramli@parlimen.gov.my",
            phone="03-2601 7222",
            facebook_url="https://facebook.com/ramli",
            service_centre_address="No 1, Jalan Meru",
            parlimen_profile_id="4250",
            mymp_slug="ramli-bin-dato-mohd-nor",
        )
        resp = self.client.get("/api/v1/constituencies/P078/")
        self.assertEqual(resp.status_code, 200)
        mp = resp.data["mp"]
        self.assertEqual(mp["name"], "YB Dato' Dr. Ramli bin Dato' Mohd Nor")
        self.assertEqual(mp["email"], "ramli@parlimen.gov.my")
        self.assertEqual(mp["phone"], "03-2601 7222")
        self.assertIn("parlimen.gov.my", mp["parlimen_profile_url"])
        self.assertIn("mymp.org.my", mp["mymp_profile_url"])
        self.assertEqual(mp["photo_url"], "https://parlimen.gov.my/images/P078.jpg")
