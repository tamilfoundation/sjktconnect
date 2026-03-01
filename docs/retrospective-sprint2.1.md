# Sprint 2.1 Retrospective — Subscriber Models + Subscribe/Unsubscribe API

**Date**: 2026-03-01
**Duration**: ~30 minutes
**Sprint goal**: Create subscriber data layer and public API endpoints

## What Was Built

- New `subscribers` Django app with two models:
  - `Subscriber` — email (unique), name, organisation, is_active, unsubscribe_token (UUID)
  - `SubscriptionPreference` — per-subscriber toggle for 3 categories (Parliament Watch, News Watch, Monthly Blast)
- Service layer (`subscriber_service.py`) with subscribe, unsubscribe, get/update preferences functions
- 3 REST API endpoints (all public, token-secured):
  - POST `/api/v1/subscribers/subscribe/` — idempotent, creates with all prefs enabled
  - GET `/api/v1/subscribers/unsubscribe/<token>/` — one-click deactivation
  - GET/PUT `/api/v1/subscribers/preferences/<token>/` — view/update category toggles
- Django admin with inline preferences
- 51 new tests across 3 test files (models, services, API)

## What Went Well

- Clean sprint — straightforward scope, no blockers
- Existing codebase patterns (SchoolContact, MagicLinkToken) provided clear model design reference
- Service layer pattern separates business logic from views — reusable for Sprint 2.3 (confirmation email)
- All 426 backend tests pass, no regressions

## What Went Wrong

- Ordering test (`test_default_ordering`) failed due to `auto_now_add` timestamps being identical in fast test execution. Fixed by testing Meta.ordering directly instead of queryset order.
- Auto-generated `tests.py` from `startapp` conflicted with `tests/` package directory. Had to delete the file and clear `__pycache__`.

## Design Decisions

1. **Subscriber separate from SchoolContact** — subscribers can be anyone (journalists, community leaders, MPs' offices), not just school reps
2. **UUID unsubscribe tokens** — no expiry (unlike Magic Link tokens), acts as both authentication and unsubscribe mechanism
3. **Idempotent subscribe** — duplicate email returns 200, reactivates if previously unsubscribed
4. **Email normalisation** — lowercase + strip on subscribe to prevent duplicates
5. **All endpoints public** — no Django auth required; tokens provide access control for preferences/unsubscribe

## Numbers

| Metric | Value |
|--------|-------|
| Files created | 10 |
| Files modified | 3 |
| New tests | 51 |
| Total backend tests | 426 |
| Total tests (all) | 560 |
| Models added | 2 |
| API endpoints added | 3 |
