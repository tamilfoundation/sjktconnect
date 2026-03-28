# Sprint 8.5 Retrospective — Brevo Webhook Integration

**Date**: 2026-03-28
**Duration**: ~1 hour (within same session as Sprint 8.4)

## What Was Built

- Brevo webhook endpoint (`POST /api/v1/webhooks/brevo/`) to receive real-time delivery events
- Full engagement tracking: delivered, opened (with count), clicked (with count), hard/soft bounce, spam complaint, Brevo-side unsubscribe
- Auto-deactivation of subscribers after 3 hard bounces
- Optional HMAC signature verification via `BREVO_WEBHOOK_SECRET`
- 19 new tests covering all event types, edge cases, and API endpoint

## What Went Well

1. **Clean separation of concerns** — webhook service (`webhook.py`) handles all event logic, API view (`views.py`) handles HTTP/auth. Easy to test each independently.
2. **All 1092 backend tests pass** — no regressions from model changes (new statuses, new fields).
3. **Quick deployment** — backend deployed in one shot, webhook endpoint verified live with a test curl.
4. **Brevo setup was straightforward** — the new Plugins & Integrations UI guided through 3 steps (name, endpoint, events).

## What Went Wrong

Nothing significant. The sprint was small and focused.

1. **Minor: Brevo event name uncertainty** — Brevo UI shows "Hard Bounced" / "Soft Bounced" / "Complaint" but the webhook payload may use different names (`hard_bounce`, `soft_bounce`, `spam`). Added both variants to the handler to be safe. Root cause: Brevo docs were inaccessible (403). Fix: handled all plausible event name variants.

## Design Decisions

1. **Engagement fields on BroadcastRecipient, not a separate table** — opens/clicks are per-email, not per-subscriber. Keeps queries simple (one JOIN to get broadcast stats).
2. **Only hard bounces increment bounce_count** — soft bounces are transient (mailbox full, server busy). Auto-deactivating on soft bounces would be too aggressive.
3. **Threshold of 3 hard bounces before deactivation** — gives the subscriber a chance (email might be temporarily misconfigured). One bad broadcast shouldn't kill a subscription.
4. **No HMAC secret required by default** — Brevo free tier doesn't offer HMAC in the new webhook UI. The endpoint accepts all POST requests but only processes events with matching message-ids, so spoofed events for non-existent message-ids are harmlessly ignored.
5. **F-expression for open/click counts** — uses `F("open_count") + 1` to avoid race conditions from concurrent webhook deliveries.

## Numbers

- Files changed: 10 (3 modified, 7 new)
- New tests: 19
- Total tests: 1382 (1092 backend + 290 frontend)
- Backend deploy: revision sjktconnect-api-00080-x67
- Brevo webhook: activated, tracking 7 event types
