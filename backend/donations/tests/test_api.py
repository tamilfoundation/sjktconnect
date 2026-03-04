"""Tests for donations REST API endpoints."""

import hashlib
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from donations.models import Donation

TOYYIB_SETTINGS = {
    "TOYYIBPAY_SECRET_KEY": "test-secret-key",
    "TOYYIBPAY_CATEGORY_CODE": "test-cat-code",
    "TOYYIBPAY_BASE_URL": "https://toyyibpay.com",
}


@override_settings(**TOYYIB_SETTINGS)
class CreateDonationAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()

    @patch("donations.api.views.services.create_bill")
    @patch("donations.api.views.services.get_redirect_url")
    def test_create_donation_success(self, mock_redirect, mock_bill):
        """POST with valid data returns 201 with payment_url."""
        mock_bill.return_value = "BILL-TEST"
        mock_redirect.return_value = "https://toyyibpay.com/BILL-TEST"

        response = self.client.post(
            "/api/v1/donations/",
            {
                "amount": "50.00",
                "donor_name": "Test Donor",
                "donor_email": "test@example.com",
                "donor_phone": "0123456789",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertIn("payment_url", response.data)
        self.assertEqual(response.data["payment_url"], "https://toyyibpay.com/BILL-TEST")

        # Verify donation was created in DB
        self.assertEqual(Donation.objects.count(), 1)
        donation = Donation.objects.first()
        self.assertEqual(donation.donor_name, "Test Donor")
        self.assertRegex(donation.order_id, r"^SJKT-DON-\d{8}-[A-F0-9]{6}$")

    def test_create_donation_validation_error_missing_name(self):
        """Missing donor_name returns 400."""
        response = self.client.post(
            "/api/v1/donations/",
            {
                "amount": "50.00",
                "donor_email": "test@example.com",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("donor_name", response.data)

    def test_create_donation_validation_error_missing_email(self):
        """Missing donor_email returns 400."""
        response = self.client.post(
            "/api/v1/donations/",
            {
                "amount": "50.00",
                "donor_name": "Test",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("donor_email", response.data)

    def test_create_donation_validation_error_missing_amount(self):
        """Missing amount returns 400."""
        response = self.client.post(
            "/api/v1/donations/",
            {
                "donor_name": "Test",
                "donor_email": "test@example.com",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("amount", response.data)

    def test_create_donation_validation_error_zero_amount(self):
        """Amount below minimum returns 400."""
        response = self.client.post(
            "/api/v1/donations/",
            {
                "amount": "0.00",
                "donor_name": "Test",
                "donor_email": "test@example.com",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    @patch("donations.api.views.services.create_bill")
    def test_create_donation_toyyib_failure(self, mock_bill):
        """Toyyib API failure returns 503."""
        mock_bill.side_effect = Exception("Connection refused")

        response = self.client.post(
            "/api/v1/donations/",
            {
                "amount": "50.00",
                "donor_name": "Test",
                "donor_email": "test@example.com",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 503)
        self.assertIn("error", response.data)

        # Donation should be marked as failed
        donation = Donation.objects.first()
        self.assertEqual(donation.status, "failed")


class DonationStatusAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.donation = Donation.objects.create(
            order_id="SJKT-DON-20260304-STATUS",
            amount=Decimal("100.00"),
            donor_name="Status Test",
            donor_email="status@example.com",
            status="paid",
        )

    def test_donation_status(self):
        """GET with valid order_id returns donation data."""
        response = self.client.get(
            "/api/v1/donations/status/",
            {"order_id": self.donation.order_id},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["order_id"], self.donation.order_id)
        self.assertEqual(response.data["status"], "paid")
        self.assertEqual(response.data["amount"], "100.00")
        self.assertEqual(response.data["donor_name"], "Status Test")

    def test_donation_status_not_found(self):
        """Unknown order_id returns 404."""
        response = self.client.get(
            "/api/v1/donations/status/",
            {"order_id": "SJKT-DON-00000000-XXXXXX"},
        )
        self.assertEqual(response.status_code, 404)

    def test_donation_status_missing_param(self):
        """Missing order_id returns 400."""
        response = self.client.get("/api/v1/donations/status/")
        self.assertEqual(response.status_code, 400)


@override_settings(**TOYYIB_SETTINGS)
class ToyyibCallbackAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.donation = Donation.objects.create(
            order_id="SJKT-DON-20260304-CBTEST",
            amount=Decimal("50.00"),
            donor_name="Callback Test",
            donor_email="cb@example.com",
            bill_code="BILL-CB-TEST",
            status="redirected",
        )

    def _make_hash(self, status_id, order_id, refno):
        return hashlib.md5(
            f"test-secret-key{status_id}{order_id}{refno}ok".encode()
        ).hexdigest()

    def test_toyyib_callback(self):
        """POST callback with valid hash processes donation."""
        h = self._make_hash("1", self.donation.order_id, "REF-CB")

        response = self.client.post(
            "/api/v1/donations/callback/",
            {
                "billcode": "BILL-CB-TEST",
                "status_id": "1",
                "order_id": self.donation.order_id,
                "refno": "REF-CB",
                "reason": "success",
                "amount": "5000",
                "hash": h,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.donation.refresh_from_db()
        self.assertEqual(self.donation.status, "paid")

    def test_toyyib_callback_invalid_hash_still_200(self):
        """Invalid hash logs warning but returns 200 (Toyyib expects OK)."""
        response = self.client.post(
            "/api/v1/donations/callback/",
            {
                "billcode": "BILL-CB-TEST",
                "status_id": "1",
                "order_id": self.donation.order_id,
                "refno": "REF-X",
                "reason": "",
                "amount": "5000",
                "hash": "badhash",
            },
        )

        # Toyyib callback always returns OK
        self.assertEqual(response.status_code, 200)
        # But donation should NOT be marked paid
        self.donation.refresh_from_db()
        self.assertEqual(self.donation.status, "redirected")
