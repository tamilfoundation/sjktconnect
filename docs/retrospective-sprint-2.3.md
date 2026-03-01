# Sprint 2.3 Retrospective — Broadcast Sending + Confirmation Email

## What Was Built

Wired up actual email sending for broadcasts and added welcome emails on subscribe:

- **Broadcast sender service**: Loops recipients, sends individual emails via Brevo transactional API, wraps content in email template with personalised unsubscribe/preferences links, tracks per-recipient SENT/FAILED status
- **Confirmation email service**: Welcome email with preferences and unsubscribe links sent to new subscribers
- **Management command**: `send_broadcast --id <pk>` for Cloud Run Job execution
- **Send view**: POST endpoint at `/broadcast/send/<pk>/` with JavaScript confirmation dialog
- **Detail view**: `/broadcast/<pk>/` showing broadcast details + per-recipient delivery status table
- **Status lifecycle**: DRAFT → SENDING → SENT (or FAILED on error)

## What Went Well

- Subagent produced a complete working implementation in one pass (32 tests, all passing)
- Two-stage review caught two critical issues before they could cause production problems
- Existing patterns (email_sender.py) made the Brevo integration straightforward
- Dev mode fallback (console logging without API key) enables local testing without credentials

## What Went Wrong

- **Race condition on status transition**: Initial implementation used a naive `get()` + check + `save()` pattern. Code review caught this — fixed with atomic conditional UPDATE
- **Stuck SENDING state**: No error recovery if an exception occurred during the send loop. Fixed with try/finally block that transitions to FAILED on unhandled errors
- **HTTP call inside transaction.atomic()**: Confirmation email was called inside the subscriber creation transaction, holding the DB connection during a 10s API call. Fixed by moving email send outside the atomic block
- **N+1 queries**: Recipient loop accessed `subscriber.unsubscribe_token` without prefetch. Fixed with `select_related("subscriber")`

## Design Decisions

1. **Atomic conditional UPDATE for status transition** (vs select_for_update): Simpler, no explicit lock management, naturally prevents concurrent sends
2. **FAILED status on unhandled exceptions**: Broadcast never gets stuck in SENDING — admin can see it failed and investigate
3. **0.5s sleep between emails**: Simple rate limiting that caps at ~120/min, well within Brevo free tier (300/day)
4. **Confirmation email outside transaction**: Prevents holding DB connections during API calls; email send failure doesn't roll back the subscriber creation

## Numbers

- Files created: 5 (sender service, email service, management command, detail template, test files)
- Files modified: 5 (views, urls, subscriber_service, preview template, list template)
- New tests: 32 (10 sender + 9 views + 4 command + 8 confirmation + 1 regression)
- Total tests: 516 backend passing
- Code review iterations: 1 (4 issues fixed in single pass)
