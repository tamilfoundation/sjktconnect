# Sprint 4.1–4.2 Retrospective — Donations Feature

**Date:** 2026-03-04
**Duration:** Single session
**Sprint goal:** Two donation paths — school bank details + DuitNow QR, and Toyyib Pay for Tamil Foundation

---

## What Was Built

### Sprint 4.1: School Bank Details + DuitNow QR
- 3 bank fields on School model (`bank_name`, `bank_account_number`, `bank_account_name`)
- `import_bank_details` management command — imported 202/528 schools from TF Excel
- DuitNow QR endpoint (`GET /api/v1/schools/<moe_code>/duitnow-qr/`) — generates PNG
- SupportSchoolCard sidebar component — bank details + copy button + QR image
- Bank fields editable via SchoolEditForm (magic link auth)
- i18n strings in EN/TA/MS

### Sprint 4.2: Toyyib Pay Donations
- `donations` Django app — Donation model, Toyyib Pay service, 3 API endpoints
- `/donate` page with DonationForm (preset amounts, custom, donor info)
- `/donate/thank-you` page with payment status check
- DonationAdmin for admin panel
- i18n strings in EN/TA/MS (20 keys)

### Tests
- 33 backend tests (model, service, API, QR)
- 14 frontend tests (SupportSchoolCard, DonationForm)
- Total project: 979 tests (714 backend + 265 frontend)

---

## What Went Well

1. **Subagent-driven development worked smoothly** — 7 implementation tasks dispatched sequentially, each subagent delivered clean code following existing patterns
2. **TF Excel data import was straightforward** — 202 schools had bank data, column indices matched the plan
3. **Thulivellam Toyyib pattern reused effectively** — service layer adapted with minimal changes
4. **Existing frontend patterns consistent** — SupportSchoolCard and DonationForm followed established component patterns without friction
5. **Header already had Donate nav link** — from the mega-menu work earlier in the session, no extra work needed

---

## What Went Wrong

1. **No end-to-end test against Toyyib sandbox** — the Toyyib integration is tested with mocks only. Need to verify with real sandbox credentials before going live.
2. **Backend test runner can't use `manage.py test`** — Supabase doesn't allow test DB creation. All backend tests run via pytest with `SimpleTestCase` or mocked DB. This is a known limitation but makes integration testing harder.

---

## Design Decisions

1. **SJKTConnect never handles school donation money** — displays bank details only. Donor transfers directly. Avoids Malaysian regulatory issues.
2. **DuitNow QR is informational, not transactional** — encodes bank name + account number as text, not a DuitNow payment standard QR. Donors scan to see the info, then transfer via their banking app.
3. **Toyyib Pay for TF donations only** — TF has an existing Toyyib account (same as Thulivellam). All TF donations go through one payment gateway.
4. **UUID primary key for Donation model** — prevents enumeration of donation records.
5. **Order ID format `SJKT-DON-YYYYMMDD-XXXXXX`** — human-readable, sortable by date.

---

## Numbers

| Metric | Value |
|--------|-------|
| Commits | 7 |
| Backend tests added | 33 |
| Frontend tests added | 14 |
| Total project tests | 979 |
| Schools with bank data | 202/528 |
| Files created | ~20 |
| Files modified | ~15 |
| Deployment | Pending |
