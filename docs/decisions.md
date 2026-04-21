# Architectural Decisions

## Server-Side Map Data with ISR — Sprint 8.3, 2026-03-28

**Decision:** Fetch all 528 school map pins server-side in the homepage server component, then pass as props to the client-side SchoolMap. Use Next.js ISR with 24-hour revalidation.

**Alternatives considered:**
1. Client-side fetch with SWR/React Query caching (still hits DB per unique visitor)
2. Static JSON file generated at build time (stale until redeploy)
3. Edge caching via Cloudflare Workers (adds infrastructure complexity)

**Rationale:** ISR is the simplest path — one line (`export const revalidate = 86400`) and moving the fetch to the server component. No new infrastructure, no build step changes. Supabase sees 1 request/day instead of 1 per visitor.

**Trade-offs:** School data updates (new school, GPS correction) take up to 24 hours to appear on the map. Acceptable because school data changes ~monthly at most.

**Revisit if:** School data starts changing more frequently (e.g. real-time enrolment updates), or if on-demand ISR revalidation is needed (Next.js `revalidatePath` API).

## Brevo Webhook for Email Engagement Tracking — Sprint 8.5, 2026-03-28

**Decision:** Add engagement tracking fields (delivered_at, opened_at, open_count, clicked_at, click_count, bounce_type) directly on BroadcastRecipient model. Process Brevo webhook events via a public endpoint with optional HMAC.

**Alternatives considered:**
1. Separate EmailEvent table (normalised event log) — more flexible but heavier queries for simple stats
2. Polling Brevo API for delivery status — rate-limited, delayed, adds API dependency
3. Brevo built-in analytics only — no data ownership, can't correlate with our subscriber data

**Rationale:** Flat fields on BroadcastRecipient keeps queries simple (one table for broadcast stats). Webhook is real-time and free. We own the data and can build custom reports.

**Trade-offs:** Multiple opens/clicks only store first timestamp + count (no per-event log). Sufficient for current needs (open rate, click rate, bounce detection).

**Revisit if:** We need per-event analytics (e.g. which link was clicked, time-series open patterns), or if webhook volume becomes significant enough to warrant async processing (queue).

## `.defer("boundary_wkt")` over `.only()` for Egress Reduction — Egress Fix, 2026-03-29

**Decision:** Use `.defer("boundary_wkt")` on 6 non-GeoJSON views to exclude large WKT polygon fields from SQL SELECT, rather than switching to `.only()` with explicit field lists.

**Alternatives considered:**
1. `.only()` with explicit field lists — more surgical but brittle (breaks when fields are added to models)
2. Separate lightweight model/proxy for list views — over-engineered for this use case
3. Raw SQL with explicit SELECT — loses ORM benefits, harder to maintain

**Rationale:** `.defer()` is additive exclusion — it says "fetch everything except these fields". This is safer for evolving models because new fields are automatically included. The GeoJSON endpoints that need `boundary_wkt` use `.only()` with explicit field lists and were not touched.

**Trade-offs:** If code later accesses a deferred field, Django issues a separate query per instance (N+1 risk). Mitigated by the fact that no serializer or `__str__` method uses `boundary_wkt`.

**Revisit if:** A new serializer or view needs `boundary_wkt` alongside other data — they'd need to explicitly un-defer it or use a separate queryset.

## First-class `Broadcast.kind` Field over `audience_filter` Categories — News Digest & Urgent Alert Fix, 2026-04-22

**Decision:** Add a dedicated `Broadcast.kind` enum field (NEWS_DIGEST / URGENT_ALERT / MONTHLY_BLAST / PARLIAMENT_WATCH / OTHER) to track broadcast *type* as a first-class dimension, separate from `audience_filter` which tracks *who* receives the broadcast.

**Alternatives considered:**
1. Add a `type` key inside the existing `audience_filter` JSONField
2. Parse broadcast type from the subject line prefix at query time
3. Separate models per broadcast type (digest/alert/blast)

**Rationale:** Audience and type are orthogonal — a digest and an urgent alert can both target the `NEWS_WATCH` audience. Encoding type inside `audience_filter` entrenches the conflation and makes JSON-key queries slow (no index). A subject-line parser is brittle and can't be indexed. Separate models would fragment the broadcast log and complicate the admin UI. A first-class indexed enum field solves all three problems at one migration's cost.

**Trade-offs:** Adds a migration with a data backfill. The `kind` field is redundant with `audience_filter.category` for the legacy rows but will diverge as new broadcast types land. Writers must remember to set it — mitigated by making `OTHER` the default (failure mode is a non-fatal mis-tagged broadcast, not a crash).

**Revisit if:** A new broadcast type emerges that doesn't fit the existing enum (add a value) or if the type space grows beyond ~10 enum values (consider polymorphism).

## Two-Pass Urgency Classification with Separate Verification Call — News Digest & Urgent Alert Fix, 2026-04-22

**Decision:** Structure the urgency classifier as a two-gate first-pass prompt (Step 1 trigger match, Step 2 actionability) followed by a narrow second-pass verification call when the first pass returns `is_urgent=True`. If the verifier disagrees, the flag is downgraded.

**Alternatives considered:**
1. Extend the first-pass prompt with chain-of-thought reasoning in a single call
2. Add an article-age cap (reject anything older than N days) as the safety net
3. Require human DRAFT review on every urgent alert (feature-flagged off)
4. Train a separate classifier model on labelled SJK(T)-urgency examples

**Rationale:** Urgent classifications are expected to be rare (~1 per month). A second Gemini call at ~200 tokens is negligible cost at that rate. Two independent samples catch more first-pass false positives than one longer chain-of-thought prompt because the samples are less correlated. The verifier sees only the summary and urgency reason — it can't re-run the classifier's same keyword match. An article-age cap treats a symptom without fixing the classifier. Human review adds latency to genuine emergencies. A custom-trained model is overkill for the data volume.

**Trade-offs:** Genuine urgent classifications pay 2× Gemini calls. The verifier can also hallucinate (reject a genuine alert) — mitigated by the audit trail in `ai_raw_response["urgent_verification"]` which logs both first-pass and verifier reasons for post-hoc diagnosis, and by the dormant DRAFT-review flag as a kill switch.

**Revisit if:** Classification volume grows to where 2× calls become expensive, or if the verifier shows a consistent pattern of false-negative rejections blocking genuine alerts.
