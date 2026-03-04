"""Tests for DuitNow QR code endpoint on school API."""

from django.test import TestCase
from rest_framework.test import APIClient

from schools.models import Constituency, School


class DuitNowQRTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.constituency = Constituency.objects.create(
            code="P140", name="Segamat", state="Johor"
        )
        self.school_with_bank = School.objects.create(
            moe_code="JBD0050",
            name="SJK(T) Ladang Bikam",
            short_name="SJK(T) Ladang Bikam",
            state="Johor",
            constituency=self.constituency,
            bank_name="Maybank",
            bank_account_number="1234567890",
            bank_account_name="PIBG SJK(T) Ladang Bikam",
        )
        self.school_no_bank = School.objects.create(
            moe_code="JBD0051",
            name="SJK(T) Ladang Sagil",
            short_name="SJK(T) Ladang Sagil",
            state="Johor",
            constituency=self.constituency,
        )

    def test_duitnow_qr_returns_png(self):
        """School with bank data returns a PNG image."""
        response = self.client.get(
            f"/api/v1/schools/{self.school_with_bank.moe_code}/duitnow-qr/"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/png")
        # PNG files start with the PNG signature bytes
        self.assertTrue(response.content[:4] == b"\x89PNG")

    def test_duitnow_qr_no_bank_data(self):
        """School without bank account number returns 404."""
        response = self.client.get(
            f"/api/v1/schools/{self.school_no_bank.moe_code}/duitnow-qr/"
        )
        self.assertEqual(response.status_code, 404)

    def test_duitnow_qr_school_not_found(self):
        """Invalid moe_code returns 404."""
        response = self.client.get("/api/v1/schools/INVALID999/duitnow-qr/")
        self.assertEqual(response.status_code, 404)
