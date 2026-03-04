"""Donation tracking for Tamil Foundation contributions via Toyyib Pay."""

import uuid

from django.db import models


class Donation(models.Model):
    """A donation to Tamil Foundation via Toyyib Pay."""

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("redirected", "Redirected to Toyyib"),
        ("paid", "Paid"),
        ("failed", "Failed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_id = models.CharField(max_length=50, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    donor_name = models.CharField(max_length=200)
    donor_email = models.EmailField()
    donor_phone = models.CharField(max_length=20, blank=True, default="")
    message = models.TextField(blank=True, default="")

    # Toyyib Pay fields
    bill_code = models.CharField(max_length=50, blank=True, default="")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    toyyib_refno = models.CharField(max_length=100, blank=True, default="")
    toyyib_reason = models.CharField(max_length=200, blank=True, default="")

    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Donation {self.order_id} - RM{self.amount} ({self.status})"

    def generate_order_id(self):
        """Generate a unique order ID: SJKT-DON-YYYYMMDD-XXXX."""
        from django.utils import timezone

        date_str = timezone.now().strftime("%Y%m%d")
        short_uuid = uuid.uuid4().hex[:6].upper()
        self.order_id = f"SJKT-DON-{date_str}-{short_uuid}"

    def mark_paid(self, refno="", reason=""):
        from django.utils import timezone

        self.status = "paid"
        self.toyyib_refno = refno
        self.toyyib_reason = reason
        self.paid_at = timezone.now()
        self.save()

    def mark_failed(self, refno="", reason=""):
        self.status = "failed"
        self.toyyib_refno = refno
        self.toyyib_reason = reason
        self.save()
