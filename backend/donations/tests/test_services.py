"""Tests for Toyyib Pay service layer (mocked API calls)."""

import hashlib
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, TestCase, override_settings

from donations.models import Donation
from donations.services import (
    create_bill,
    process_callback,
    verify_callback_hash,
)

TOYYIB_SETTINGS = {
    "TOYYIBPAY_SECRET_KEY": "test-secret-key",
    "TOYYIBPAY_CATEGORY_CODE": "test-cat-code",
    "TOYYIBPAY_BASE_URL": "https://toyyibpay.com",
}


class VerifyCallbackHashTest(SimpleTestCase):
    """Hash verification is pure logic — no DB needed."""

    def _make_hash(self, secret, status_id, order_id, refno):
        return hashlib.md5(
            f"{secret}{status_id}{order_id}{refno}ok".encode()
        ).hexdigest()

    def test_verify_callback_hash_valid(self):
        """Correct MD5 hash passes verification."""
        secret = "test-secret"
        h = self._make_hash(secret, "1", "ORDER-001", "REF001")
        self.assertTrue(
            verify_callback_hash(secret, "1", "ORDER-001", "REF001", h)
        )

    def test_verify_callback_hash_invalid(self):
        """Wrong hash fails verification."""
        self.assertFalse(
            verify_callback_hash("secret", "1", "ORDER-001", "REF001", "badhash")
        )

    def test_verify_callback_hash_different_params(self):
        """Hash computed with different parameters does not match."""
        secret = "test-secret"
        h = self._make_hash(secret, "1", "ORDER-001", "REF001")
        # Use different order_id
        self.assertFalse(
            verify_callback_hash(secret, "1", "ORDER-002", "REF001", h)
        )


@override_settings(**TOYYIB_SETTINGS)
class CreateBillTest(TestCase):
    def _make_donation(self):
        return Donation.objects.create(
            order_id="SJKT-DON-20260304-ABC123",
            amount=Decimal("50.00"),
            donor_name="Test Donor",
            donor_email="test@example.com",
            donor_phone="0123456789",
        )

    @patch("donations.services.requests.post")
    def test_create_bill_success(self, mock_post):
        """Successful bill creation saves bill_code and sets status to redirected."""
        mock_response = MagicMock()
        mock_response.json.return_value = [{"BillCode": "BILL-XYZ"}]
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        donation = self._make_donation()
        bill_code = create_bill(
            donation,
            return_url="https://example.com/thank-you",
            callback_url="https://example.com/callback",
        )

        self.assertEqual(bill_code, "BILL-XYZ")
        donation.refresh_from_db()
        self.assertEqual(donation.bill_code, "BILL-XYZ")
        self.assertEqual(donation.status, "redirected")

    @patch("donations.services.requests.post")
    def test_create_bill_posts_correct_data(self, mock_post):
        """Verify the POST data sent to Toyyib API."""
        mock_response = MagicMock()
        mock_response.json.return_value = [{"BillCode": "BILL-123"}]
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        donation = self._make_donation()
        create_bill(donation, "https://ret.url", "https://cb.url")

        call_data = mock_post.call_args[1].get("data") or mock_post.call_args[0][1] if len(mock_post.call_args[0]) > 1 else mock_post.call_args[1].get("data")
        if call_data is None:
            call_data = mock_post.call_args.kwargs.get("data", {})
        self.assertEqual(call_data["billAmount"], 5000)  # 50.00 * 100
        self.assertEqual(call_data["billExternalReferenceNo"], donation.order_id)
        self.assertEqual(call_data["billEmail"], "test@example.com")

    @patch("donations.services.requests.post")
    def test_create_bill_error_empty_response(self, mock_post):
        """Empty response from Toyyib raises ValueError."""
        mock_response = MagicMock()
        mock_response.json.return_value = []
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        donation = self._make_donation()
        with self.assertRaises(ValueError):
            create_bill(donation, "https://ret.url", "https://cb.url")

    @patch("donations.services.requests.post")
    def test_create_bill_error_no_billcode(self, mock_post):
        """Response without BillCode raises ValueError."""
        mock_response = MagicMock()
        mock_response.json.return_value = [{"Error": "Something went wrong"}]
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        donation = self._make_donation()
        with self.assertRaises(ValueError):
            create_bill(donation, "https://ret.url", "https://cb.url")


@override_settings(**TOYYIB_SETTINGS)
class ProcessCallbackTest(TestCase):
    def _make_donation(self, order_id="SJKT-DON-20260304-TEST01", status="redirected"):
        return Donation.objects.create(
            order_id=order_id,
            amount=Decimal("100.00"),
            donor_name="Callback Test",
            donor_email="cb@example.com",
            bill_code="BILL-CB",
            status=status,
        )

    def _make_hash(self, status_id, order_id, refno):
        return hashlib.md5(
            f"test-secret-key{status_id}{order_id}{refno}ok".encode()
        ).hexdigest()

    def test_process_callback_paid(self):
        """status_id '1' marks donation as paid."""
        donation = self._make_donation()
        h = self._make_hash("1", donation.order_id, "REF-PAID")

        result = process_callback(
            bill_code="BILL-CB",
            status_id="1",
            order_id=donation.order_id,
            refno="REF-PAID",
            reason="success",
            amount="10000",
            received_hash=h,
        )

        result.refresh_from_db()
        self.assertEqual(result.status, "paid")
        self.assertEqual(result.toyyib_refno, "REF-PAID")
        self.assertIsNotNone(result.paid_at)

    def test_process_callback_failed(self):
        """status_id '3' marks donation as failed."""
        donation = self._make_donation()
        h = self._make_hash("3", donation.order_id, "REF-FAIL")

        result = process_callback(
            bill_code="BILL-CB",
            status_id="3",
            order_id=donation.order_id,
            refno="REF-FAIL",
            reason="insufficient funds",
            amount="10000",
            received_hash=h,
        )

        result.refresh_from_db()
        self.assertEqual(result.status, "failed")
        self.assertEqual(result.toyyib_reason, "insufficient funds")

    def test_process_callback_invalid_hash(self):
        """Invalid hash raises ValueError."""
        donation = self._make_donation()

        with self.assertRaises(ValueError) as ctx:
            process_callback(
                bill_code="BILL-CB",
                status_id="1",
                order_id=donation.order_id,
                refno="REF-X",
                reason="",
                amount="10000",
                received_hash="invalidhash",
            )
        self.assertIn("Invalid callback hash", str(ctx.exception))

    def test_process_callback_already_paid(self):
        """Idempotent — already-paid donation is not modified."""
        donation = self._make_donation(status="paid")
        donation.toyyib_refno = "ORIGINAL-REF"
        donation.paid_at = donation.created_at
        donation.save()

        h = self._make_hash("1", donation.order_id, "NEW-REF")

        result = process_callback(
            bill_code="BILL-CB",
            status_id="1",
            order_id=donation.order_id,
            refno="NEW-REF",
            reason="",
            amount="10000",
            received_hash=h,
        )

        result.refresh_from_db()
        self.assertEqual(result.toyyib_refno, "ORIGINAL-REF")

    def test_process_callback_donation_not_found(self):
        """Unknown order_id raises ValueError."""
        h = self._make_hash("1", "FAKE-ORDER", "REF")

        with self.assertRaises(ValueError) as ctx:
            process_callback(
                bill_code="BILL",
                status_id="1",
                order_id="FAKE-ORDER",
                refno="REF",
                reason="",
                amount="100",
                received_hash=h,
            )
        self.assertIn("Donation not found", str(ctx.exception))
