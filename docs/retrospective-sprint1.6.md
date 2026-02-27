# Sprint 1.6 Retrospective — Magic Link Authentication

**Date**: 27 February 2026
**Sprint goal**: Passwordless authentication for school representatives via magic link email

---

## What Was Built

- **accounts Django app** — MagicLinkToken (UUID, 24h expiry, single-use) + SchoolContact (verified school representative)
- **Token service** — validate @moe.edu.my domain, match email to school (by MOE code or stored email), generate/verify tokens
- **Brevo email service** — transactional email via Brevo API in production, console logging fallback in development
- **3 API endpoints** — POST request-magic-link, GET verify/{token}, GET me (session-based auth)
- **ClaimForm component** — email input with pre-fill from school code, loading/success/error states
- **Claim pages** — /claim (form + "How it works"), /claim/verify/[token] (auto-verify on mount)
- **ClaimButton activated** — changed from disabled placeholder to live link to /claim/?school=CODE
- **47 new tests** (33 backend + 14 frontend), total 421

## What Went Well

- **Two-pass school matching** worked cleanly: first match email local part against MOE code, then against stored email field. Covers both standard (jbd0050@moe.edu.my) and custom email addresses.
- **Console fallback for email** — zero cost during development, no external service dependency for testing.
- **Session auth over JWT** — simpler than token refresh logic; Django sessions + `credentials: "include"` work well with Next.js ISR.
- **Pre-fill UX** — ClaimButton passes MOE code to ClaimForm, which auto-generates the expected email address. Reduces friction.
- **Clean test structure** — backend tests cover models, services, and API separately. Frontend tests mock the API layer cleanly.

## What Went Wrong

- **Django ValidationError for malformed UUIDs** — `MagicLinkToken.objects.get(token=value)` raises `django.core.exceptions.ValidationError` when value is not a valid UUID string, not `ValueError` as expected. Required adding `ValidationError` to the except clause. Caught by tests.
- **Next.js Link trailing slash** — `Link href="/claim/?school=JBD0050"` renders as `/claim?school=JBD0050` (no trailing slash before query string). Test expectation needed updating. Minor but easy to miss.

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| Magic link over password | Schools don't need accounts — verify via MOE email, one-time session |
| 24-hour token expiry | Balances convenience (check email later) with security |
| Single-use tokens | Prevents replay attacks |
| Session-based auth | Simpler than JWT for server-rendered pages; no refresh token logic |
| Brevo with console fallback | Free tier for production; zero-cost development without API key |
| @moe.edu.my only | Official school domain ensures only authorised school staff can claim |
| SchoolContact unique on (school, email) | One verified contact record per email per school |

## Numbers

| Metric | Value |
|--------|-------|
| New backend files | 14 |
| Modified backend files | 2 |
| New frontend files | 3 |
| Modified frontend files | 4 |
| New test files | 4 |
| Modified test files | 1 |
| New backend tests | 33 |
| New frontend tests | 14 |
| Total tests (project) | 421 (309 backend + 112 frontend) |
| Bugs caught by tests | 1 (ValidationError for malformed UUIDs) |
| Bugs caught manually | 1 (Next.js Link trailing slash) |
