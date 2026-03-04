"""Tests for Donation model."""

import re
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from donations.models import Donation


class GenerateOrderIdTest(TestCase):
    def test_generate_order_id(self):
        """Order ID follows SJKT-DON-YYYYMMDD-XXXXXX format."""
        donation = Donation(
            amount=Decimal("50.00"),
            donor_name="Test",
            donor_email="test@example.com",
        )
        donation.generate_order_id()

        self.assertRegex(
            donation.order_id,
            r"^SJKT-DON-\d{8}-[A-F0-9]{6}$",
        )

    def test_generate_order_id_uses_current_date(self):
        """Date portion matches today's date."""
        donation = Donation(
            amount=Decimal("10.00"),
            donor_name="Test",
            donor_email="test@example.com",
        )
        donation.generate_order_id()

        today = timezone.now().strftime("%Y%m%d")
        self.assertIn(today, donation.order_id)

    def test_generate_order_id_unique(self):
        """Two calls produce different order IDs."""
        d1 = Donation(amount=Decimal("10.00"), donor_name="A", donor_email="a@x.com")
        d2 = Donation(amount=Decimal("10.00"), donor_name="B", donor_email="b@x.com")
        d1.generate_order_id()
        d2.generate_order_id()
        self.assertNotEqual(d1.order_id, d2.order_id)


class MarkPaidTest(TestCase):
    def test_mark_paid(self):
        """mark_paid sets status, refno, and paid_at."""
        donation = Donation.objects.create(
            order_id="SJKT-DON-20260304-AAAAAA",
            amount=Decimal("100.00"),
            donor_name="Test Donor",
            donor_email="test@example.com",
        )
        donation.mark_paid(refno="REF123", reason="success")

        donation.refresh_from_db()
        self.assertEqual(donation.status, "paid")
        self.assertEqual(donation.toyyib_refno, "REF123")
        self.assertIsNotNone(donation.paid_at)

    def test_mark_paid_sets_paid_at_timestamp(self):
        """paid_at is close to current time."""
        donation = Donation.objects.create(
            order_id="SJKT-DON-20260304-BBBBBB",
            amount=Decimal("50.00"),
            donor_name="Test",
            donor_email="test@example.com",
        )
        before = timezone.now()
        donation.mark_paid(refno="REF456")
        after = timezone.now()

        self.assertGreaterEqual(donation.paid_at, before)
        self.assertLessEqual(donation.paid_at, after)


class MarkFailedTest(TestCase):
    def test_mark_failed(self):
        """mark_failed sets status, refno, and reason."""
        donation = Donation.objects.create(
            order_id="SJKT-DON-20260304-CCCCCC",
            amount=Decimal("25.00"),
            donor_name="Test",
            donor_email="test@example.com",
        )
        donation.mark_failed(refno="REF789", reason="insufficient funds")

        donation.refresh_from_db()
        self.assertEqual(donation.status, "failed")
        self.assertEqual(donation.toyyib_refno, "REF789")
        self.assertEqual(donation.toyyib_reason, "insufficient funds")
        self.assertIsNone(donation.paid_at)


class DonationStrTest(TestCase):
    def test_str(self):
        """String representation includes order_id, amount, and status."""
        donation = Donation(
            order_id="SJKT-DON-20260304-DDDDDD",
            amount=Decimal("100.00"),
            status="pending",
        )
        result = str(donation)
        self.assertIn("SJKT-DON-20260304-DDDDDD", result)
        self.assertIn("100", result)
        self.assertIn("pending", result)
