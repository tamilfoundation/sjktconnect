"""Toyyib Pay integration for SJKTConnect donations."""

import hashlib
import logging

import requests
from django.conf import settings

from .models import Donation

logger = logging.getLogger(__name__)


def get_base_url():
    return getattr(settings, "TOYYIBPAY_BASE_URL", "https://toyyibpay.com")


def create_bill(donation, return_url, callback_url):
    """Create a Toyyib Pay bill for a donation."""
    base_url = get_base_url()
    amount_cents = int(donation.amount * 100)

    data = {
        "userSecretKey": settings.TOYYIBPAY_SECRET_KEY,
        "categoryCode": settings.TOYYIBPAY_CATEGORY_CODE,
        "billName": "Donation to Tamil Foundation"[:30],
        "billDescription": f"SJKTConnect donation - {donation.order_id}"[:100],
        "billPriceSetting": 1,
        "billPayorInfo": 1,
        "billAmount": amount_cents,
        "billReturnUrl": return_url,
        "billCallbackUrl": callback_url,
        "billExternalReferenceNo": donation.order_id,
        "billTo": donation.donor_name[:100],
        "billEmail": donation.donor_email,
        "billPhone": donation.donor_phone or "0000000000",
        "billPaymentChannel": 0,
    }

    logger.info("Creating Toyyib bill: %s RM%s", donation.order_id, donation.amount)

    response = requests.post(
        f"{base_url}/index.php/api/createBill",
        data=data,
        timeout=30,
    )
    response.raise_for_status()
    result = response.json()

    if not result or not isinstance(result, list) or "BillCode" not in result[0]:
        raise ValueError(f"Unexpected Toyyib response: {result}")

    bill_code = result[0]["BillCode"]
    donation.bill_code = bill_code
    donation.status = "redirected"
    donation.save()

    logger.info("Toyyib bill created: %s -> %s", donation.order_id, bill_code)
    return bill_code


def get_redirect_url(bill_code):
    return f"{get_base_url()}/{bill_code}"


def verify_callback_hash(secret_key, status_id, order_id, refno, received_hash):
    expected = hashlib.md5(
        f"{secret_key}{status_id}{order_id}{refno}ok".encode()
    ).hexdigest()
    return expected == received_hash


def process_callback(
    bill_code, status_id, order_id, refno, reason, amount, received_hash
):
    """Process a Toyyib Pay callback."""
    secret_key = settings.TOYYIBPAY_SECRET_KEY

    if not verify_callback_hash(
        secret_key, status_id, order_id, refno, received_hash
    ):
        raise ValueError("Invalid callback hash")

    try:
        donation = Donation.objects.get(order_id=order_id)
    except Donation.DoesNotExist:
        raise ValueError(f"Donation not found: {order_id}")

    if donation.status in ("paid", "failed"):
        return donation

    if status_id == "1":
        donation.mark_paid(refno=refno, reason=reason)
        logger.info("Donation PAID: %s refno=%s", order_id, refno)
    elif status_id == "3":
        donation.mark_failed(refno=refno, reason=reason)
        logger.info("Donation FAILED: %s reason=%s", order_id, reason)

    return donation
