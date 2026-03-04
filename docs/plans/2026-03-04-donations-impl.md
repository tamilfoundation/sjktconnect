# Donations Feature Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add two donation paths — bank details + DuitNow QR on school pages, and Toyyib payment for Tamil Foundation donations.

**Architecture:** Bank fields added to existing School model with data migration from TF Excel. New `donations` Django app for Toyyib integration. Frontend gets a sidebar card on school pages and a new `/donate` page.

**Tech Stack:** Django 5, DRF, Next.js, `qrcode` Python library, Toyyib Pay REST API, Brevo (receipts)

**Design doc:** `docs/plans/2026-03-04-donations-design.md`

---

## Sprint 4.1: School Bank Details + DuitNow QR

### Task 1: Add bank fields to School model

**Files:**
- Modify: `backend/schools/models.py` (after `fax` field, ~line 92)
- Create: `backend/schools/migrations/0006_add_bank_fields.py` (auto-generated)

**Step 1: Add fields to model**

In `backend/schools/models.py`, add after the `fax` field:

```python
    # ── Bank Details (for donations) ─────────────────────────────────
    bank_name = models.CharField(max_length=100, blank=True, default="")
    bank_account_number = models.CharField(max_length=50, blank=True, default="")
    bank_account_name = models.CharField(max_length=200, blank=True, default="")
```

**Step 2: Generate migration**

Run: `cd backend && python manage.py makemigrations schools -n add_bank_fields`

**Step 3: Apply migration**

Run: `cd backend && python manage.py migrate`

**Step 4: Commit**

```bash
git add backend/schools/models.py backend/schools/migrations/0006_add_bank_fields.py
git commit -m "feat: add bank detail fields to School model"
```

---

### Task 2: Import bank data from TF Excel

**Files:**
- Create: `backend/schools/management/commands/import_bank_details.py`

**Step 1: Write the import command**

```python
"""Import school bank details from Tamil Foundation Excel database."""

import openpyxl
from django.core.management.base import BaseCommand

from schools.models import School


class Command(BaseCommand):
    help = "Import bank details from TF Excel into School model"

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            default="data/பள்ளிகள் - மாநிலம்.xlsx",
            help="Path to TF Excel file",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be imported without saving",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        wb = openpyxl.load_workbook(options["file"], read_only=True)
        ws = wb.active

        updated = 0
        skipped = 0

        for row in ws.iter_rows(min_row=2, values_only=True):
            code = str(row[4]).strip() if row[4] else ""
            acct_name = str(row[39]).strip() if row[39] else ""
            acct_num = str(row[40]).strip() if row[40] else ""
            bank = str(row[41]).strip() if row[41] else ""

            if not code or not acct_num:
                skipped += 1
                continue

            try:
                school = School.objects.get(moe_code=code)
            except School.DoesNotExist:
                self.stdout.write(f"  School not found: {code}")
                skipped += 1
                continue

            if dry_run:
                self.stdout.write(
                    f"  Would update {code}: {bank} / {acct_name} / {acct_num}"
                )
            else:
                school.bank_name = bank
                school.bank_account_name = acct_name
                school.bank_account_number = acct_num
                school.save(
                    update_fields=["bank_name", "bank_account_name", "bank_account_number"]
                )
            updated += 1

        wb.close()

        action = "Would update" if dry_run else "Updated"
        self.stdout.write(
            self.style.SUCCESS(f"{action} {updated} schools, skipped {skipped}")
        )
```

**Step 2: Dry run to verify**

Run: `cd backend && python manage.py import_bank_details --dry-run`

Expected: ~203 schools listed.

**Step 3: Run for real**

Run: `cd backend && python manage.py import_bank_details`

**Step 4: Verify**

Run: `cd backend && python manage.py shell -c "from schools.models import School; print(School.objects.exclude(bank_account_number='').count())"`

Expected: ~203

**Step 5: Commit**

```bash
git add backend/schools/management/commands/import_bank_details.py
git commit -m "feat: add import_bank_details command, import 203 schools"
```

---

### Task 3: Expose bank fields in API + DuitNow QR endpoint

**Files:**
- Modify: `backend/schools/api/serializers.py` — add bank fields to `SchoolDetailSerializer`
- Modify: `backend/schools/api/views.py` — add DuitNow QR endpoint
- Modify: `backend/schools/api/urls.py` — add QR URL
- Modify: `backend/requirements.txt` — add `qrcode[pil]`

**Step 1: Install qrcode library**

Run: `cd backend && pip install "qrcode[pil]"` and add `qrcode[pil]` to `requirements.txt`.

**Step 2: Add bank fields to SchoolDetailSerializer**

In `backend/schools/api/serializers.py`, find the `SchoolDetailSerializer` `Meta.fields` list and add:

```python
"bank_name", "bank_account_number", "bank_account_name",
```

Also add to `SchoolEditSerializer` `Meta.fields` so schools can edit their bank details.

**Step 3: Add bank fields to SchoolEditForm field config**

In `backend/schools/api/serializers.py`, ensure `bank_name`, `bank_account_number`, `bank_account_name` are writable fields in `SchoolEditSerializer`.

**Step 4: Add DuitNow QR endpoint**

In `backend/schools/api/views.py`, add:

```python
import io
import qrcode
from django.http import HttpResponse
from rest_framework.decorators import api_view
from rest_framework.permissions import AllowAny


@api_view(["GET"])
def duitnow_qr(request, moe_code):
    """Generate a DuitNow QR code PNG for a school's bank account."""
    from schools.models import School

    try:
        school = School.objects.get(moe_code=moe_code)
    except School.DoesNotExist:
        return HttpResponse(status=404)

    if not school.bank_account_number:
        return HttpResponse(status=404)

    # DuitNow QR payload: account number + bank name
    # Simple format: donors scan and enter amount in their banking app
    qr_data = (
        f"Bank: {school.bank_name}\n"
        f"Account: {school.bank_account_number}\n"
        f"Name: {school.bank_account_name}"
    )

    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(qr_data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    return HttpResponse(buf.getvalue(), content_type="image/png")
```

**Step 5: Add URL**

In `backend/schools/api/urls.py`, add:

```python
path("schools/<str:moe_code>/duitnow-qr/", views.duitnow_qr, name="duitnow-qr"),
```

**Step 6: Run server and test**

Run: `cd backend && python manage.py runserver`
Test: `curl -o /tmp/qr.png http://localhost:8000/api/v1/schools/WBD0170/duitnow-qr/`

**Step 7: Commit**

```bash
git add backend/schools/api/serializers.py backend/schools/api/views.py backend/schools/api/urls.py backend/requirements.txt
git commit -m "feat: expose bank fields in API + DuitNow QR endpoint"
```

---

### Task 4: Frontend — Support This School card

**Files:**
- Create: `frontend/components/SupportSchoolCard.tsx`
- Modify: `frontend/lib/types.ts` — add bank fields to `SchoolDetail`
- Modify: `frontend/app/[locale]/school/[moe_code]/page.tsx` — add card to sidebar
- Modify: `frontend/messages/en.json`, `ta.json`, `ms.json` — i18n strings

**Step 1: Add bank fields to SchoolDetail type**

In `frontend/lib/types.ts`, add to `SchoolDetail`:

```typescript
  bank_name: string;
  bank_account_number: string;
  bank_account_name: string;
```

**Step 2: Create SupportSchoolCard component**

Create `frontend/components/SupportSchoolCard.tsx`:

```tsx
"use client";

import { useTranslations } from "next-intl";
import { useState } from "react";

interface Props {
  bankName: string;
  bankAccountNumber: string;
  bankAccountName: string;
  moeCode: string;
}

export default function SupportSchoolCard({
  bankName,
  bankAccountNumber,
  bankAccountName,
  moeCode,
}: Props) {
  const t = useTranslations("schoolDetail");
  const [copied, setCopied] = useState(false);

  if (!bankAccountNumber) return null;

  const handleCopy = () => {
    navigator.clipboard.writeText(bankAccountNumber);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const apiBase = process.env.NEXT_PUBLIC_API_URL || "";
  const qrUrl = `${apiBase}/api/v1/schools/${moeCode}/duitnow-qr/`;

  return (
    <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
      <div className="h-1 bg-green-500" />
      <div className="p-4">
        <h3 className="font-semibold text-gray-900 mb-3">
          {t("supportSchool")}
        </h3>

        <div className="space-y-2 text-sm">
          <div>
            <span className="text-gray-500">{t("bankName")}</span>
            <p className="font-medium">{bankName}</p>
          </div>
          <div>
            <span className="text-gray-500">{t("accountName")}</span>
            <p className="font-medium text-xs">{bankAccountName}</p>
          </div>
          <div>
            <span className="text-gray-500">{t("accountNumber")}</span>
            <div className="flex items-center gap-2">
              <p className="font-mono font-medium">{bankAccountNumber}</p>
              <button
                onClick={handleCopy}
                className="text-xs text-primary-600 hover:text-primary-800"
              >
                {copied ? t("copied") : t("copy")}
              </button>
            </div>
          </div>
        </div>

        {/* DuitNow QR */}
        <div className="mt-4 text-center">
          <p className="text-xs text-gray-500 mb-2">{t("scanToDonate")}</p>
          <img
            src={qrUrl}
            alt="DuitNow QR Code"
            className="mx-auto w-40 h-40 border rounded"
          />
        </div>
      </div>
    </div>
  );
}
```

**Step 3: Add i18n strings**

Add to `frontend/messages/en.json` under `schoolDetail`:

```json
"supportSchool": "Support This School",
"bankName": "Bank",
"accountName": "Account Name",
"accountNumber": "Account Number",
"copy": "Copy",
"copied": "Copied!",
"scanToDonate": "Scan with your banking app"
```

Add Tamil and Malay equivalents.

**Step 4: Add card to school page sidebar**

In `frontend/app/[locale]/school/[moe_code]/page.tsx`, import and add `SupportSchoolCard` to the sidebar (right column), before or after the constituency card:

```tsx
<SupportSchoolCard
  bankName={school.bank_name}
  bankAccountNumber={school.bank_account_number}
  bankAccountName={school.bank_account_name}
  moeCode={school.moe_code}
/>
```

**Step 5: Add bank fields to SchoolEditForm**

In `frontend/components/SchoolEditForm.tsx`, add to the `FIELDS` array:

```typescript
{ key: "bank_name", labelKey: "bankName", type: "text" },
{ key: "bank_account_name", labelKey: "bankAccountName", type: "text" },
{ key: "bank_account_number", labelKey: "bankAccountNumber", type: "text" },
```

Update `SchoolEditData` type in `frontend/lib/types.ts` to include the bank fields.

**Step 6: Test locally**

Run: `cd frontend && npm run dev`
Visit: `http://localhost:3000/en/school/WBD0170` (SJK(T) Cheras — has bank data)

**Step 7: Commit**

```bash
git add frontend/components/SupportSchoolCard.tsx frontend/lib/types.ts frontend/app/\[locale\]/school/\[moe_code\]/page.tsx frontend/messages/ frontend/components/SchoolEditForm.tsx
git commit -m "feat: Support This School card with bank details + DuitNow QR"
```

---

## Sprint 4.2: Donate to Tamil Foundation (Toyyib)

### Task 5: Create donations Django app

**Files:**
- Create: `backend/donations/__init__.py`
- Create: `backend/donations/models.py`
- Create: `backend/donations/admin.py`
- Create: `backend/donations/services.py`
- Create: `backend/donations/api/__init__.py`
- Create: `backend/donations/api/views.py`
- Create: `backend/donations/api/urls.py`
- Create: `backend/donations/api/serializers.py`
- Modify: `backend/sjktconnect/settings/base.py` — add to INSTALLED_APPS
- Modify: `backend/sjktconnect/urls.py` — add URL include

**Step 1: Create app structure**

Run: `cd backend && python manage.py startapp donations`

Then create `donations/api/` directory with `__init__.py`.

**Step 2: Write the Donation model**

In `backend/donations/models.py`:

```python
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
```

**Step 3: Write the Toyyib service**

Create `backend/donations/services.py` (adapted from Thulivellam pattern):

```python
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
        "billName": f"Donation to Tamil Foundation"[:30],
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
        f"{base_url}/index.php/api/createBill", data=data, timeout=30,
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


def process_callback(bill_code, status_id, order_id, refno, reason, amount, received_hash):
    """Process a Toyyib Pay callback."""
    secret_key = settings.TOYYIBPAY_SECRET_KEY

    if not verify_callback_hash(secret_key, status_id, order_id, refno, received_hash):
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
```

**Step 4: Write API views**

Create `backend/donations/api/serializers.py`:

```python
from rest_framework import serializers

from donations.models import Donation


class DonationCreateSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=1)
    donor_name = serializers.CharField(max_length=200)
    donor_email = serializers.EmailField()
    donor_phone = serializers.CharField(max_length=20, required=False, default="")
    message = serializers.CharField(required=False, default="", allow_blank=True)
```

Create `backend/donations/api/views.py`:

```python
import logging

from django.http import HttpResponse
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from donations.models import Donation
from donations import services
from .serializers import DonationCreateSerializer

logger = logging.getLogger(__name__)


@api_view(["POST"])
@permission_classes([AllowAny])
def create_donation(request):
    """Create a donation and return the Toyyib payment URL."""
    serializer = DonationCreateSerializer(data=request.data)
    serializer.validate()

    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data

    donation = Donation(
        amount=data["amount"],
        donor_name=data["donor_name"],
        donor_email=data["donor_email"],
        donor_phone=data.get("donor_phone", ""),
        message=data.get("message", ""),
    )
    donation.generate_order_id()
    donation.save()

    base_url = request.build_absolute_uri("/")[:-1]
    return_url = f"{base_url}/donate/thank-you?order_id={donation.order_id}"
    callback_url = f"{base_url}/api/v1/donations/callback/"

    try:
        bill_code = services.create_bill(donation, return_url, callback_url)
        redirect_url = services.get_redirect_url(bill_code)
        return Response({"payment_url": redirect_url}, status=status.HTTP_201_CREATED)
    except Exception as e:
        logger.error("Failed to create Toyyib bill: %s", e)
        donation.status = "failed"
        donation.save()
        return Response(
            {"error": "Payment service unavailable"},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )


@api_view(["POST"])
@permission_classes([AllowAny])
def toyyib_callback(request):
    """Handle Toyyib Pay server-to-server callback."""
    try:
        services.process_callback(
            bill_code=request.POST.get("billcode", ""),
            status_id=request.POST.get("status_id", ""),
            order_id=request.POST.get("order_id", ""),
            refno=request.POST.get("refno", ""),
            reason=request.POST.get("reason", ""),
            amount=request.POST.get("amount", ""),
            received_hash=request.POST.get("hash", ""),
        )
    except ValueError as e:
        logger.warning("Callback error: %s", e)
    return HttpResponse("OK")


@api_view(["GET"])
@permission_classes([AllowAny])
def donation_status(request):
    """Check donation status by order_id."""
    order_id = request.query_params.get("order_id")
    if not order_id:
        return Response({"error": "order_id required"}, status=400)

    try:
        donation = Donation.objects.get(order_id=order_id)
    except Donation.DoesNotExist:
        return Response({"error": "Not found"}, status=404)

    return Response({
        "order_id": donation.order_id,
        "amount": str(donation.amount),
        "status": donation.status,
        "donor_name": donation.donor_name,
    })
```

Create `backend/donations/api/urls.py`:

```python
from django.urls import path

from . import views

urlpatterns = [
    path("", views.create_donation, name="create-donation"),
    path("callback/", views.toyyib_callback, name="toyyib-callback"),
    path("status/", views.donation_status, name="donation-status"),
]
```

**Step 5: Register app**

In `backend/sjktconnect/settings/base.py`, add `"donations"` to `INSTALLED_APPS`.

Add Toyyib settings:

```python
# Toyyib Pay
TOYYIBPAY_BASE_URL = os.environ.get("TOYYIBPAY_BASE_URL", "https://toyyibpay.com")
TOYYIBPAY_SECRET_KEY = os.environ.get("TOYYIBPAY_SECRET_KEY", "")
TOYYIBPAY_CATEGORY_CODE = os.environ.get("TOYYIBPAY_CATEGORY_CODE", "")
```

In `backend/sjktconnect/urls.py`, add:

```python
path("api/v1/donations/", include("donations.api.urls")),
```

**Step 6: Admin**

In `backend/donations/admin.py`:

```python
from django.contrib import admin
from .models import Donation


@admin.register(Donation)
class DonationAdmin(admin.ModelAdmin):
    list_display = ["order_id", "amount", "donor_name", "status", "created_at"]
    list_filter = ["status"]
    search_fields = ["order_id", "donor_name", "donor_email"]
    readonly_fields = ["id", "order_id", "bill_code", "toyyib_refno", "created_at"]
```

**Step 7: Migrate and test**

Run: `cd backend && python manage.py makemigrations donations && python manage.py migrate`

**Step 8: Commit**

```bash
git add backend/donations/
git add backend/sjktconnect/settings/base.py backend/sjktconnect/urls.py
git commit -m "feat: donations app with Toyyib Pay integration"
```

---

### Task 6: Frontend — Donate page

**Files:**
- Create: `frontend/app/[locale]/donate/page.tsx`
- Create: `frontend/components/DonationForm.tsx`
- Modify: `frontend/messages/en.json`, `ta.json`, `ms.json`

**Step 1: Create DonationForm component**

Create `frontend/components/DonationForm.tsx`:

```tsx
"use client";

import { useTranslations } from "next-intl";
import { useState } from "react";

const PRESET_AMOUNTS = [10, 50, 100, 250];

export default function DonationForm() {
  const t = useTranslations("donate");
  const [amount, setAmount] = useState<number | "">("");
  const [customAmount, setCustomAmount] = useState("");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const selectedAmount = typeof amount === "number" ? amount : Number(customAmount) || 0;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (selectedAmount < 1 || !name || !email) return;

    setLoading(true);
    setError("");

    try {
      const apiBase = process.env.NEXT_PUBLIC_API_URL || "";
      const res = await fetch(`${apiBase}/api/v1/donations/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          amount: selectedAmount,
          donor_name: name,
          donor_email: email,
          donor_phone: phone,
          message,
        }),
      });

      if (!res.ok) throw new Error("Payment service unavailable");

      const data = await res.json();
      window.location.href = data.payment_url;
    } catch (err) {
      setError(t("paymentError"));
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Amount selection */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          {t("selectAmount")}
        </label>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {PRESET_AMOUNTS.map((a) => (
            <button
              key={a}
              type="button"
              onClick={() => { setAmount(a); setCustomAmount(""); }}
              className={`py-3 px-4 rounded-lg border text-center font-semibold transition ${
                amount === a
                  ? "border-primary-600 bg-primary-50 text-primary-700"
                  : "border-gray-300 hover:border-gray-400"
              }`}
            >
              RM {a}
            </button>
          ))}
        </div>
        <div className="mt-3">
          <input
            type="number"
            min="1"
            placeholder={t("customAmount")}
            value={customAmount}
            onChange={(e) => { setCustomAmount(e.target.value); setAmount(""); }}
            className="w-full border border-gray-300 rounded-lg px-4 py-3 focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
          />
        </div>
      </div>

      {/* Donor info */}
      <div className="space-y-4">
        <input
          type="text"
          required
          placeholder={t("yourName")}
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="w-full border border-gray-300 rounded-lg px-4 py-3"
        />
        <input
          type="email"
          required
          placeholder={t("yourEmail")}
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="w-full border border-gray-300 rounded-lg px-4 py-3"
        />
        <input
          type="tel"
          placeholder={t("yourPhone")}
          value={phone}
          onChange={(e) => setPhone(e.target.value)}
          className="w-full border border-gray-300 rounded-lg px-4 py-3"
        />
        <textarea
          placeholder={t("optionalMessage")}
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          rows={3}
          className="w-full border border-gray-300 rounded-lg px-4 py-3"
        />
      </div>

      {error && <p className="text-red-600 text-sm">{error}</p>}

      <button
        type="submit"
        disabled={loading || selectedAmount < 1 || !name || !email}
        className="w-full bg-primary-600 text-white py-3 px-6 rounded-lg font-semibold hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition"
      >
        {loading ? t("processing") : `${t("donate")} RM ${selectedAmount || "..."}`}
      </button>
    </form>
  );
}
```

**Step 2: Create donate page**

Create `frontend/app/[locale]/donate/page.tsx`:

```tsx
import { useTranslations } from "next-intl";
import { getTranslations } from "next-intl/server";
import DonationForm from "@/components/DonationForm";
import { Link } from "@/i18n/routing";

export async function generateMetadata({ params }: { params: { locale: string } }) {
  const t = await getTranslations({ locale: params.locale, namespace: "donate" });
  return { title: t("pageTitle"), description: t("pageDescription") };
}

export default function DonatePage() {
  const t = useTranslations("donate");

  return (
    <main className="max-w-2xl mx-auto px-4 py-12">
      <h1 className="text-3xl font-bold text-gray-900 mb-2">{t("title")}</h1>
      <p className="text-gray-600 mb-8">{t("subtitle")}</p>

      <div className="bg-white rounded-xl border border-gray-200 p-6 mb-8">
        <DonationForm />
      </div>

      <div className="text-center text-sm text-gray-500">
        <p className="mb-2">{t("schoolDonationCta")}</p>
        <Link href="/" className="text-primary-600 hover:underline">
          {t("findSchool")}
        </Link>
      </div>
    </main>
  );
}
```

**Step 3: Create thank you page**

Create `frontend/app/[locale]/donate/thank-you/page.tsx`:

```tsx
"use client";

import { useTranslations } from "next-intl";
import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { Link } from "@/i18n/routing";

export default function ThankYouPage() {
  const t = useTranslations("donate");
  const searchParams = useSearchParams();
  const orderId = searchParams.get("order_id");
  const [donation, setDonation] = useState<any>(null);

  useEffect(() => {
    if (!orderId) return;
    const apiBase = process.env.NEXT_PUBLIC_API_URL || "";
    fetch(`${apiBase}/api/v1/donations/status/?order_id=${orderId}`)
      .then((r) => r.json())
      .then(setDonation)
      .catch(() => {});
  }, [orderId]);

  return (
    <main className="max-w-lg mx-auto px-4 py-16 text-center">
      <h1 className="text-3xl font-bold text-gray-900 mb-4">
        {donation?.status === "paid" ? t("thankYou") : t("paymentProcessing")}
      </h1>
      {donation?.status === "paid" && (
        <p className="text-gray-600 mb-2">
          RM {donation.amount} {t("receivedFrom")} {donation.donor_name}
        </p>
      )}
      {orderId && (
        <p className="text-sm text-gray-400 mb-8">
          {t("referenceId")}: {orderId}
        </p>
      )}
      <Link
        href="/"
        className="text-primary-600 hover:underline"
      >
        {t("backToHome")}
      </Link>
    </main>
  );
}
```

**Step 4: Add i18n strings**

Add `donate` namespace to all three locale files with keys: `pageTitle`, `pageDescription`, `title`, `subtitle`, `selectAmount`, `customAmount`, `yourName`, `yourEmail`, `yourPhone`, `optionalMessage`, `donate`, `processing`, `paymentError`, `schoolDonationCta`, `findSchool`, `thankYou`, `paymentProcessing`, `receivedFrom`, `referenceId`, `backToHome`.

**Step 5: Add nav link**

Add "Donate" to the header navigation (existing Header component).

**Step 6: Test locally**

Run frontend and backend, test the flow end-to-end.

**Step 7: Commit**

```bash
git add frontend/app/\[locale\]/donate/ frontend/components/DonationForm.tsx frontend/messages/
git commit -m "feat: donate page with Toyyib payment integration"
```

---

### Task 7: Write tests

**Files:**
- Create: `backend/donations/tests.py`
- Create: `frontend/__tests__/DonationForm.test.tsx`
- Create: `frontend/__tests__/SupportSchoolCard.test.tsx`

**Backend tests:** Model tests (generate_order_id, mark_paid, mark_failed), service tests (mock Toyyib API calls, verify_callback_hash), API tests (create donation, callback, status endpoint).

**Frontend tests:** SupportSchoolCard renders bank details and copy button, hides when no bank data. DonationForm renders preset amounts, validates required fields, handles submit.

**Step 1: Write and run backend tests**
**Step 2: Write and run frontend tests**
**Step 3: Commit**

```bash
git commit -m "test: add donation backend + frontend tests"
```

---

### Task 8: Deploy + set env vars

**Step 1: Set Toyyib env vars on Cloud Run**

```bash
gcloud run services update sjktconnect-api --region asia-southeast1 \
  --set-env-vars "TOYYIBPAY_SECRET_KEY=xxx,TOYYIBPAY_CATEGORY_CODE=xxx,TOYYIBPAY_BASE_URL=https://toyyibpay.com"
```

(Get actual values from TF's Toyyib account — same as Thulivellam)

**Step 2: Deploy backend**

```bash
gcloud run deploy sjktconnect-api --source backend --region asia-southeast1 --quiet
```

**Step 3: Deploy frontend**

```bash
gcloud run deploy sjktconnect-web --source frontend --region asia-southeast1 --quiet
```

**Step 4: Run import on production**

```bash
cd backend && python manage.py import_bank_details
```

(Already connected to Supabase — runs against prod DB)

**Step 5: Verify live**

- Visit school page with bank details
- Test donation flow end-to-end
- Verify callback URL works

**Step 6: Final commit**

```bash
git commit -m "chore: sprint 4.1-4.2 complete — donations feature live"
```

---

## Summary

| Sprint | Tasks | What it delivers |
|--------|-------|------------------|
| **4.1** | Tasks 1-4 | Bank details + DuitNow QR on 203 school pages, editable via claim |
| **4.2** | Tasks 5-8 | `/donate` page with Toyyib payment for Tamil Foundation, deploy |

**Estimated new tests:** ~25 backend + ~10 frontend = ~35 new tests
**Files touched:** ~20 (within budget)
