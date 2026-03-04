# Donations Feature — Design Document

**Date:** 2026-03-04
**Status:** Approved

## Problem

SJKTConnect has a "Donate" button but no donation infrastructure. Schools need funding support and donors need a trustworthy, frictionless way to contribute.

## Solution

Two donation paths:

1. **Donate to school** — display bank details + DuitNow QR code on school pages
2. **Donate to Tamil Foundation** — Toyyib payment gateway on a `/donate` page

SJKTConnect never handles money for school donations — it's a directory that connects donors to schools directly.

## Design

### 1. Donate to School (School Page)

**Model changes** — 3 new fields on `School`:

| Field | Type | Source |
|-------|------|--------|
| `bank_name` | CharField(100), nullable | TF Excel col 41 (வங்கி) |
| `bank_account_number` | CharField(50), nullable | TF Excel col 40 (கணக்கு எண்) |
| `bank_account_name` | CharField(200), nullable | TF Excel col 39 (வாரியக் கணக்கு பெயர்) |

**Data**: 203 of 529 schools (38%) already have bank details in TF's database. Banks: RHB (49), Maybank (41), CIMB (36), Public Bank (23), BSN (10), and others.

**Data migration**: Import bank details from TF Excel for the 203 schools with data.

**School edit flow**: Schools that have claimed their page via magic link can add/update their bank details through the existing edit form. New fields added to SchoolEditForm.

**DuitNow QR code**: Generated server-side as PNG using `qrcode` Python library. The QR encodes the bank account number in DuitNow format. Served via a new API endpoint: `GET /api/v1/schools/<moe_code>/duitnow-qr/`.

**Frontend — school page sidebar**: A "Support This School" card:
- Bank name, account name, account number (with copy button)
- DuitNow QR code image (scannable by any Malaysian banking app)
- For schools without bank details: "Bank details not yet available. If you're from this school, claim your page to add them."

**API**: Existing school serializer gets the 3 new bank fields. Only returned when populated.

**Privacy**: School board (LPS/PIBG) bank accounts are semi-public — printed on school circulars, used for fee collection. Displaying them is standard practice.

### 2. Donate to Tamil Foundation (Toyyib)

**New app**: `donations`

**Model**: `Donation`

| Field | Type |
|-------|------|
| `amount` | DecimalField |
| `donor_name` | CharField(200) |
| `donor_email` | EmailField |
| `message` | TextField, optional |
| `toyyib_bill_code` | CharField, nullable |
| `status` | CharField: PENDING / PAID / FAILED |
| `paid_at` | DateTimeField, nullable |
| `created_at` | DateTimeField |

**Flow**:
1. User visits `/donate` page
2. Selects amount (RM10 / RM50 / RM100 / custom), enters name + email
3. Backend creates Toyyib bill via API, returns payment URL
4. User redirected to Toyyib hosted payment page (FPX, credit card)
5. Toyyib sends callback to backend on payment completion
6. Backend updates Donation status, shows thank you page

**Toyyib config**: Reuse TF's existing Toyyib account (same as Thulivellam). Env vars: `TOYYIB_SECRET_KEY`, `TOYYIB_CATEGORY_CODE`. Free tier, up to RM1,000 per transaction.

**Frontend — `/donate` page**:
- Hero section explaining Tamil Foundation's mission
- Donation form with preset amounts + custom
- Link to school-specific donations: "Want to donate directly to a specific school? Find the school and use their bank details."
- Past donation stats (optional, future enhancement)

### 3. Files Affected

**Backend:**
- `schools/models.py` — 3 new fields on School
- `schools/migrations/` — schema migration + data migration (bank import)
- `schools/api/serializers.py` — expose bank fields
- `schools/api/views.py` — DuitNow QR endpoint
- `schools/edit_views.py` — bank fields in edit form
- `donations/` — new app (models, views, api, templates)

**Frontend:**
- `components/SupportSchoolCard.tsx` — new sidebar component
- `app/[locale]/school/[moe_code]/page.tsx` — add SupportSchoolCard
- `app/[locale]/donate/page.tsx` — new donate page
- `components/DonationForm.tsx` — new component
- i18n strings for EN/TA/MS

### 4. Dependencies

- `qrcode` Python library (QR generation)
- `toyyibpay` API (existing TF account)
- No new infrastructure or services
