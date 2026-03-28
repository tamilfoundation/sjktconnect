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
