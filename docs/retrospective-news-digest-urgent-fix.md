# Retrospective — News Digest & Urgent Alert Fix (2026-04-21 → 2026-04-22)

## What Was Built

A focused fix sprint triggered by observing Broadcast 69's coverage window (7–20 Apr) when the expected window was 31 Mar – 13 Apr (a skipped Apr 13 digest) or 14–20 Apr (the Apr 20 one). Investigation revealed two independent defects that compounded.

### Digest cadence fix
- New `Broadcast.kind` field (NEWS_DIGEST / URGENT_ALERT / MONTHLY_BLAST / PARLIAMENT_WATCH / OTHER) separates broadcast *type* from *audience*. The old code conflated the two via `audience_filter["category"] = "NEWS_WATCH"`, which is shared by digests and urgent alerts.
- New `Broadcast.coverage_start_date` / `coverage_end_date` fields let `_get_since_date()` return `coverage_end + 1 day` instead of `created_at`, eliminating the off-by-one overlap between consecutive digests.
- `_should_skip()` and `_get_since_date()` filter by `kind=NEWS_DIGEST` — urgent alerts can no longer poison the digest cooldown or shift the coverage window.
- Migration 0006 adds all three fields and backfills existing 69 broadcasts. Subjects like "News Watch — 16 Mar 2026 – 30 Mar 2026" are regex-parsed into coverage dates.

### Urgency classifier rewrite
- Rewrote the urgency section of `ANALYSIS_PROMPT` in `newswatch/services/news_analyser.py` as a two-step gate: Step 1 checks three narrow triggers (confirmed closure, active emergency, binding government restriction); Step 2 requires a 7-day action window AND the trigger being the primary subject.
- Added six explicit negative examples (heat-policy announcement, rebuild announcement, enrolment trend, ministry visit, award controversy, general policy) — the heat-policy and rebuild examples mirror the exact Broadcast 68 misclassification.
- Added three positive examples showing what DOES qualify.
- New second-pass verification: when first-pass returns `is_urgent=True`, a narrow Gemini call double-checks. If the verifier disagrees, the flag is downgraded to False and both reasons are logged. Audit trail stored in `ai_raw_response["urgent_verification"]`.

### Dormant safety net
- `URGENT_ALERT_REQUIRE_REVIEW` setting (default `false`) preserves current auto-send behaviour.
- When flipped to `true` via Cloud Run env vars (no redeploy), `send_urgent_alerts` creates a DRAFT and exits — a moderator must approve it from the admin broadcasts queue.

### One-off cleanup
- `clear_stale_urgent_flags` management command sweeps `is_urgent=True` off articles older than 30 days that never fired an alert. Preserves history for articles that did fire (e.g. Broadcast 68's source article).

## What Went Well

- **Fast root-cause isolation.** The investigation — walking through Cloud Run execution timestamps, cross-referencing against broadcast IDs and urgent-alert job logs — identified Broadcast 68 as the poisoning event within ~10 minutes of starting the digest-gap inquiry.
- **User steering caught a classification mistake.** The initial fix plan included an article-age cap on urgent alerts (stop sending "URGENT" about 11-day-old articles). User pointed out the real design intent: urgency classification should be rare — the 30-day throttle is not about spamming subscribers but about how rare true crises should be. That reframed the fix from "work around the classifier" to "fix the classifier", which is the right cut.
- **Incremental verification at every step.** After migration: verified backfill counts and a sampling of parsed dates before moving on. After `_get_since_date` rewrite: `dry-run` showed `since = 2026-04-21` (correct = Broadcast 69's `coverage_end + 1 day`). After prompt rewrite: unit tests for all six negative fixtures + one positive fixture before wiring.
- **Dormant feature flag instead of forced safety net.** Building the DRAFT-review path but leaving it off by default respects the user's existing auto-send workflow and makes the kill-switch a single `gcloud run jobs update --update-env-vars` away — no redeploy.

## What Went Wrong

### 1. The misclassification slipped through the existing urgency criteria

- **What happened**: Broadcast 68 (URGENT: heat-closure policy) was auto-sent on 7 Apr about a story dated 27 Mar. The email subject described a KPM permissive guideline; the body described SJK(T) Gopeng's RM14.5M rebuild. Neither was urgent by any sensible definition.
- **Why it happened**: The existing `ANALYSIS_PROMPT` already listed "heat policy announcements" and "dilapidated building repair approvals" among things NOT to flag — yet Gemini flagged it anyway. Root cause: the urgency section was a single prose block where positive triggers and negative examples were in the same paragraph; positive keywords (*tutup sekolah*, *anai-anai*, *bangunan usang*) pattern-matched against the positive list more strongly than the negative list. The prompt structure buried the veto.
- **System change**: (a) Restructured urgency criteria as two sequential gates — Step 1 (trigger check) must match before Step 2 (actionability check) is even considered. (b) Added a second-pass Gemini verifier whose prompt is narrow and explicit about what disqualifies urgency. (c) Captured audit trail in `ai_raw_response` so future misfires are diagnosable. (d) Dormant DRAFT-review flag available as a kill switch if another slips through.

### 2. Digest cadence conflated broadcast type with audience

- **What happened**: The Apr 13 digest was silently skipped because Broadcast 68 (urgent alert) sat inside the 7-day cooldown window, and the cooldown query filtered only by `audience_filter__category="NEWS_WATCH"`. Subscribers lost a full fortnight of news coverage (31 Mar – 13 Apr never appeared in any digest).
- **Why it happened**: `audience_filter` describes *who* receives a broadcast; *what kind* of broadcast it is was never tracked as a first-class field. When `send_urgent_alerts.py` and `compose_news_digest.py` were written at different times, both used the same category string `"NEWS_WATCH"` because both target the same audience. The type distinction existed only implicitly in the subject line prefix (`"URGENT: ..."` vs `"News Watch — ..."`).
- **System change**: Added `Broadcast.kind` enum — five values, indexed, defaulted to `OTHER`, backfilled on existing rows. All five writers now set `kind` at creation. Future broadcast types don't need to invent a new audience_filter convention.

### 3. Coverage start was wrong even without urgent alerts

- **What happened**: Each digest's coverage period started from the *creation timestamp* of the previous digest, not from the day after the previous coverage ended. Every digest overlapped by one day with the one before. Historically harmless (one day of double-counted articles) but structurally wrong.
- **Why it happened**: `_get_since_date()` originally returned `last_digest.created_at` because `coverage_end_date` didn't exist as a field; the subject line was the only place the coverage period lived.
- **System change**: Store `coverage_start_date` / `coverage_end_date` as first-class fields, computed at compose time. `_get_since_date()` now returns `coverage_end + 1 day` as an aware datetime.

## Design Decisions

### `kind` field vs. expanded `audience_filter` keys

Considered adding a `broadcast_type` key inside `audience_filter` (e.g. `{"category": "NEWS_WATCH", "type": "digest"}`). Rejected: `audience_filter` is a JSONField and querying JSON keys is slower (no index), and it further entrenches the type-vs-audience conflation. A first-class `kind` field is indexed, cheap to filter, and semantically distinct. Same migration serves both queries.

### Second-pass verification vs. chain-of-thought in single prompt

Considered extending the first-pass prompt with more reasoning structure (chain-of-thought). Rejected in favour of a separate verification call:
- A narrow second prompt is ~200 tokens and only runs when first-pass returns True — negligible cost at the expected ~1-urgent-per-month rate.
- Two independent samples are less correlated than one longer prompt — genuinely reduces false-positive rate (the same LLM disagreeing with itself is meaningful signal).
- Audit trail is cleaner: we can see exactly what the first pass said and why the verifier overrode it.

### Backfill over reset

Considered wiping `is_urgent` on all historical articles and reclassifying from scratch. Rejected: would re-trigger `send_urgent_alerts` on every re-run and risk a wave of delayed alerts for old news. Instead, the `clear_stale_urgent_flags` command targets only articles older than 30 days with no alert history — preserving the audit trail while preventing stale articles from triggering future alerts.

### Dormant DRAFT-review flag vs. always-on

User-specified: build it but keep it off. This decision respects that auto-send is currently working for confirmed-good classifications, and the overhead of human approval on every alert would slow response time during a real crisis. The flag exists as a kill switch — flip it if the classifier misfires again, without waiting for another fix sprint.

## Numbers

- Files modified: 11
- Files added: 5 (migration, 3 test files, management command, plan doc, retrospective)
- Broadcasts backfilled locally: 25 (7 NEWS_DIGEST / 12 URGENT_ALERT / 4 MONTHLY_BLAST / 2 OTHER)
- Tests: 199 (broadcasts + newswatch + subscribers apps) all passing
- Full backend suite: passing (exit 0)
- New tests added: 18 (9 digest cadence, 6 urgency classifier, 3 feature flag)
- Days between bug first fired (Apr 7) and root cause identified (Apr 21): 14
- Prod digests skipped due to bug: 1 (Apr 13 — covered 31 Mar – 13 Apr, never sent)
- Classification misfires in prod: 1 (Broadcast 68, sent to 344 subscribers)

## Prod rollout checklist

- [ ] Deploy backend (rev 00089)
- [ ] Update all 6 Cloud Run jobs to rev 00089 image
- [ ] Verify migration 0006 applied cleanly on Supabase (check `django_migrations` table)
- [ ] Spot-check `Broadcast.kind` population on prod: expect ~same distribution as local (roughly 7 digests, ~12 urgent alerts, ~4 monthly blasts)
- [ ] Run `clear_stale_urgent_flags --dry-run` on prod, review, then apply
- [ ] Mon 4 May 2026: verify cron fires with coverage "21 Apr – 4 May"
- [ ] After first post-fix urgent alert (whenever that is): verify audit trail in `ai_raw_response["urgent_verification"]`
