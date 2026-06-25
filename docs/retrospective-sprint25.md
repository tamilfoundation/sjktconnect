# Sprint 25 Retrospective — Urgent Alerts + Parliament Watch UI

**Closed**: 2026-06-26
**Wall time**: ~1 hour from kickoff to tests passing (backend-only, all small Django changes).
**Scope**: ~9 files (5 backend code, 2 templates, 2 test files) + Sprint 23 leftovers folded in.

## What Was Built

1. **`URGENT_ALERT_REQUIRE_REVIEW` default = `true`** — `backend/sjktconnect/settings/base.py:238`. The 09:30 MYT cron continues to compose DRAFTs; admin manually reviews + sends. Removes the unpredictable-time auto-blast that an "URGENT:" subject doesn't deserve. Rollback is a Cloud Run env var, no redeploy.

2. **`send_test(broadcast_id, recipient_emails)` in `sender.py`** — sends to arbitrary addresses with `[TEST]` subject prefix; never touches `broadcast.status`, never creates `BroadcastRecipient` rows, bypasses the Brevo daily quota gate. Stub `TEST-SEND-DO-NOT-CLICK` token in the unsub/prefs footer.

3. **`--test-recipients` on `send_broadcast` mgmt command** — wraps `send_test()` for ops use. Mutually exclusive with the normal send path; CLI output makes the no-state-change explicit.

4. **`BroadcastSendTestView` + form on `broadcast_preview.html`** — POST endpoint capped at 5 recipients, login-required. The Send Test form sits above the real Send Broadcast button on every DRAFT preview. Flash messages report sent/failed counts.

5. **Kind filter dropdown on `BroadcastListView`** — `?kind=URGENT_ALERT` narrows the queryset; invalid values fall back to all. Kind column added to the table. Both URGENT_ALERT and PARLIAMENT_WATCH DRAFTs are now one-click discoverable.

6. **Dry-run hardening** on `compose_news_digest`, `compose_urgent_alert`, `compose_parliament_watch` — each now prints `Would target N subscriber(s)` in its dry-run output. Sprint 23 leftover.

## What Went Well

- **Scope was honest about the actual gap.** Reading `send_urgent_alerts.py` first surfaced that the auto-send was already gated by a feature flag — Sprint 25 just needed to flip its default. Saved us from reinventing the "DRAFT then approve" workflow that already exists for monthly blast.
- **`send_test()` reused `_wrap_broadcast_html` + Brevo send path** instead of forking. The test sends look structurally identical to real sends, which is the only way an admin's "did it render OK?" check is meaningful. Followed Sprint 24 lesson: audit shared-state lookups before adding strategies.
- **Tests covered the *invariants* not the implementation** — every `TestSendTest` and `TestBroadcastSendTestView` case asserts "broadcast stayed DRAFT, recipient list untouched" alongside the positive-path behaviour. That's what would catch a regression where someone accidentally calls `send_broadcast` from the test path.
- **Sprint 23 leftovers folded in without scope creep.** The `--test-recipients` flag and the dry-run audience-size line were the only Sprint 23 items still open (the rest landed in Sprint 23 itself). Bundling them here closed the chapter without a separate sprint.

## What Went Wrong

- **The plan's task #3 ("dry-run hardening") was nearly a no-op** — `compose_news_digest`'s dry-run already prints 4 useful lines; the addition is one extra line per command. Root cause: the Sprint 23 leftover description in CLAUDE.md was too terse ("dry-run hardening") and didn't carry the actual gap forward (it was specifically "show subscriber count so the operator knows the blast radius"). Fix: when carrying Sprint N→N+1 leftovers, the carry-over note must include the *specific* missing capability, not just the category. Added to lessons.md.
- **Pre-existing `b` variable shadowing in `test_views.py`** survived this sprint untouched — `b = Broadcast.objects.create(...)` collides visually with `b"..."` byte literals. Not introduced this sprint, but I added more `Broadcast.objects.create(...)` calls inside `test_kind_filter_narrows_queryset` and avoided the shadowing by not assigning to a name. Worth flagging: a future sprint that does a `community/tests/` style cleanup should rename `b` → `bcast` here.

## Design Decisions

(See `docs/decisions.md` for the new entries.)

1. **Test sends bypass Brevo's daily-quota gate** — quota exhaustion is a "many recipients" problem; a 1–5 address sanity check shouldn't be subject to it.
2. **5-recipient cap on the admin UI test send** — discourages "send to my whole team" as a substitute for the real broadcast, which would then skew the audit trail.
3. **`URGENT_ALERT_REQUIRE_REVIEW` default flip is a code-level change** (not a Cloud Run env var). Env-var-only changes drift silently on redeploy (Sprint 18 lesson: "env vars set via `--update-env-vars` can silently drop on `--source .` redeploys"). The default lives in `base.py` so it survives every deploy.

## Numbers

| Metric | Sprint 24 close | Sprint 25 close | Delta |
|---|---|---|---|
| Backend tests | 1389 | **1406** | +17 |
| Frontend tests | 320 | **328** | +8 (held bug fixes from Sprint 24 close) |
| Files touched | — | 13 | — |
| Wall time | — | ~1h | — |

## Operational follow-ups

- **27 Jun ~10:00 MYT**: confirm `sjktconnect-resume-sending` drains Broadcast 86's 240 remaining PENDING. Single observation, not an open monitoring item.
- **1 Jul 09:00 MYT**: confirm `sjktconnect-monthly-blast` auto-fires the June 2026 digest. First proof the un-paused scheduler works end-to-end.
- **Next urgent-flagged article**: confirm `sjktconnect-urgent-alerts` produces a DRAFT only (status URGENT_ALERT_REQUIRE_REVIEW=true post-deploy), not an auto-send.

## What I'd do differently

- The plan listed "Polish broadcast admin UI for previewing Parliament Watch + Urgent Alert specifically" as a separate item, but the actual work collapsed into the kind filter + the Send Test form (both general improvements that benefit every broadcast kind). Sprint plans for cross-cutting UX improvements should default to "general fix that benefits all kinds" over "per-kind branches".
