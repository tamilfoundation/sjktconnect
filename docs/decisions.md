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

## SameSite=None as a bridge fix for cross-domain session cookies — Audit & Community Auth, 2026-04-22

**Decision:** Add `SESSION_COOKIE_SAMESITE = "None"` and `CSRF_COOKIE_SAMESITE = "None"` to production settings as an immediate unblock for community sign-in, rather than doing the proper Cloudflare proxy adoption first.

**Alternatives considered:**
- Adopt Cloudflare proxy per `docs/proposals/2026-03-11-cloudflare-proxy-proposal.md` (~½ sprint; proper fix — makes cookies same-origin)
- Move backend to a same-domain subdomain via Cloud Run domain mapping (blocked by the exact same cookie bug the Cloudflare proposal was written to fix)
- Migrate to token-based auth instead of session cookies (substantial rewrite, and `SameSite=None` issue doesn't exist with bearer tokens — but CSRF protection would have to be handled elsewhere)

**Rationale:** The community was unblocked at the cost of expanded CSRF surface. `SameSite=None` + `Secure` + existing CORS allowlist + DRF's `SessionAuthentication` (explicitly pinned in the same sprint via TD-08 fix) keeps CSRF protection intact today. Cloudflare is 4-6 hours of focused work that deserves its own sprint; it's already scheduled for Sprint 11 (User Management).

**Trade-offs:** Chrome is phasing out third-party cookies globally sometime in 2026 — this fix has a bounded lifetime. Also expands attack surface to any site the user visits (any origin can now POST with the session cookie attached, though CORS blocks reading the response and CSRF middleware blocks most state-changing requests). Accepted because the alternative was "no community sign-in at all".

**Revisit if:** Chrome enables strict third-party cookie blocking in stable channel, or if the User Management sprint (Sprint 11, Cloudflare adoption) is delayed past the first community launch date.

## Prod-DB guard via opt-in `SJKTCONNECT_ALLOW_PROD_DB=1` — Audit & Community Auth, 2026-04-23

**Decision:** Guard destructive `manage.py` commands behind `SJKTCONNECT_ALLOW_PROD_DB=1` when `DATABASE_URL` points to a non-local host. Scope the guard to local dev only (bypass when `K_SERVICE` env var set or `DJANGO_SETTINGS_MODULE=production`).

**Alternatives considered:**
- Remove `DATABASE_URL` from repo-root `.env`, revert to sqlite for local dev, use a separate `.env.prod` for ops work
- Provision a Supabase dev branch
- Just warn, don't block
- Change the guard to opt-out (`--local-only` flag)

**Rationale:** The guard's real failure mode is a sleepy developer running `python manage.py migrate` without thinking. An opt-in flag is default-safe and shows up in any command history ("why is `SJKTCONNECT_ALLOW_PROD_DB=1` in the shell history?"). Opt-out would require remembering to add a flag every time. A pure warning is too easy to ignore. Remove-from-`.env` would break the convenience of `manage.py shell` for quick prod data checks, which has been a workflow for months. Supabase dev branch is the ideal long-term answer but not worth the setup friction for this sprint.

**Trade-offs:** The guard is code in `manage.py`, adding a small path every Django command pays. List of "destructive" commands is hardcoded and must be updated when new write-commands are added (accepted — Django's ecosystem is slow-moving). Relies on `K_SERVICE` being set by Cloud Run, which is a platform-provided guarantee.

**Revisit if:** The hardcoded destructive-commands list grows unwieldy, or if the deployment platform changes away from Cloud Run (losing the `K_SERVICE` bypass signal).

## Store school images as bytes in Supabase Storage, not URLs — Audit & Community Auth, 2026-04-22 (planning decision for Sprint 9)

**Decision:** For Sprint 9 (Image Library), store image bytes in Supabase Storage bucket `school-images`, not in Postgres, not as Google Places URLs.

**Alternatives considered:**
- Keep Google Places URLs, re-harvest more frequently (weekly scheduled job)
- Postgres `BinaryField` as used today by `Suggestion.image`
- Google Cloud Storage bucket
- Google Photos API (rejected at design — not a developer CDN)

**Rationale:** Google Places API (New) invalidates photo resource IDs on an unpredictable cycle. Every SJK(T) school's Places photo URLs are currently returning HTTP 400 — confirming the failure mode. Re-harvesting weekly would cost ~US$14 in API calls per run (403 searches × $0.035) and still have gaps between runs. Storing bytes once and forever eliminates the dependency on Google's URL stability, and Supabase Storage is already in the stack (1 GB free tier, S3-compatible API, same project/billing/credentials as the database). GCS would add another service boundary with no benefit at this scale.

**Trade-offs:** Supabase free-tier egress (2 GB/month) is a bounded ceiling — must monitor. Re-harvesting requires re-pulling bytes (not just URLs), slightly heavier one-off operation. Postgres `BinaryField` becomes available freed up when the Sprint 8.2 `Suggestion.image` field is migrated to also use Supabase Storage.

**Revisit if:** Supabase free-tier egress is consistently exceeded, or if image count per school grows 10×+ beyond current 20-photo cap.

## Tech debt as a living register, not per-item tickets — Audit & Community Auth, 2026-04-22

**Decision:** Track tech debt in a single `docs/tech-debt.md` file with per-entry frontmatter (what / why / blocks / cost-to-fix / severity), triaged at each sprint close. Not GitHub Issues, not per-item branches, not a separate board.

**Alternatives considered:**
- GitHub Issues with `tech-debt` label
- Per-item markdown files in `docs/tech-debt/`
- A dedicated project board (GitHub Projects / Linear / similar)
- Only in CLAUDE.md pending list (current pre-audit approach)

**Rationale:** The value of a tech-debt register is pattern-recognition across items — "these four all resolve in the Image Library sprint, maybe bring it forward". Single-file review makes that trivial; ticket-per-item makes it invisible. CLAUDE.md pending list works for tactical sprint planning but doesn't preserve the "why we accepted this debt" context that becomes critical at triage time (6 weeks later you won't remember whether the workaround was a deliberate tradeoff or a rushed fix). A single markdown file sits alongside the codebase, version-controlled, greppable, cross-referenceable to code and retrospectives.

**Trade-offs:** Not integrated with any task/project tool — if we adopt one later, entries will need to be copied or linked. Single-file review gets harder as debt count grows (mitigated by rigorous sprint-close triage + ✅ marker for resolved items with a short closure note rather than deletion).

**Revisit if:** Debt count exceeds ~40 entries (at which point file-level review breaks down) or if multiple contributors need concurrent updates.

## Subdomain over path-based routing for the API — Sprint 11a Phase 1, 2026-04-23

**Decision:** Map the backend at `api.tamilschool.org` (Cloud Run domain mapping + Cloudflare proxy) instead of routing `tamilschool.org/api/*` to the backend via Cloudflare Workers.

**Alternatives considered:**
- Path-based routing via Cloudflare Worker (`tamilschool.org/api/*` → backend, `tamilschool.org/*` → frontend) — required writing + maintaining a Worker.
- Single-domain monorepo where the frontend's API routes (`/api/*`) proxy to Django — adds an extra hop per request.

**Rationale:** Subdomain is simpler operationally — separate Cloud Run services map cleanly to separate Cloud Run domain mappings. Both subdomains share `tamilschool.org` as the registrable domain, so the browser treats them as same-site for cookie purposes — `SameSite=Lax` works as if they were the same origin. No Worker code required. SSL via Google's managed certs per service. Future flexibility: if we split into multiple backends or move one off Cloud Run, subdomains let us swap independently.

**Trade-offs:** Two SSL certs to manage (both auto-renewed by Google, so trivial). Two domain mappings to keep alive. Slightly more DNS records.

**Revisit if:** We need Service Worker / Workbox for offline support that requires same-origin scope, or if we move to a CDN that charges per zone.

## Auto-claim on @moe.edu.my Google Workspace sign-in — Sprint 11a Phase 3, 2026-04-23

**Decision:** Replace magic-link email round-trip with auto-binding `profile.admin_school` whenever a Google sign-in's email matches `<moe_code>@moe.edu.my` for an active School. Delete the magic-link system entirely.

**Alternatives considered:**
- Keep magic-link as a parallel path for users without Workspace access (e.g. lost password) — deferred to SUPERADMIN manual assignment fallback.
- Approve-by-SUPERADMIN claim flow (no automated binding) — doesn't scale to 528 schools.
- Verify a screenshot or document upload — too fragile and process-heavy.

**Rationale:** Verified via `dig MX moe.edu.my` that all 5 records resolve to `*.ASPMX.L.GOOGLE.COM`. Every `<moe_code>@moe.edu.my` IS a Google Workspace account. Signing in with that account proves the same thing the magic-link round-trip proved (access to the school's official inbox), in one click instead of four. Removed ~400 LOC of code that had 0 production users.

**Trade-offs:** Schools whose MOE account is inactive or whose admin has lost the password can't auto-claim. Mitigated by SUPERADMIN manual assignment via Django admin (one DB write per edge case). Also: if a single Google Workspace allows multiple users to share the same `<moe_code>@moe.edu.my` mailbox (unlikely but possible), the first to sign in wins the claim — resolvable by SUPERADMIN re-assigning.

**Revisit if:** MOE migrates off Google Workspace, or if we discover a meaningful fraction of schools whose accounts are inactive enough to warrant an alternate verification path.

## Inline EmailClaimIndicator over banner callout — Sprint 11a Phase 3, 2026-04-24

**Decision:** Render the claim/verified status as a small inline indicator next to the school's email field in the School Details card, not as a full-width alert callout at the top of the school page.

**Alternatives considered:**
- Big blue "This page is unclaimed" callout at the top (the original v1 — built and rejected within 15 minutes of shipping).
- Banner above the school name.
- Footer link only.

**Rationale:** User feedback after seeing v1 in production: "ugly, looks like Google's 'Own this business?'". Google Business profile renders ownership state as small inline text near the data it relates to, not as a top-of-page alert. The inline indicator is discoverable without dominating the layout, and the affordance lives next to the field that establishes the relationship (the email).

**Trade-offs:** Less attention-grabbing for headteachers who land on the page cold (the big banner had higher conversion potential). Mitigated by: (a) the indicator is in the email row that any HM looking at their school will scan, (b) the modal that opens on click contains the full sign-in CTA, (c) "Copy link to share" stays as a secondary action for non-HM visitors who want to alert the HM.

**Revisit if:** Initial school-claim conversion is low after launch. Could A/B test a small banner alongside the indicator.

## Skip Next 15, jump to Next 16 — Sprint 11a Phase 4, 2026-04-24

**Decision:** Run `npm install next@latest` which resolved to `16.2.4` rather than pinning to `15.x`. Migrate the codebase for Next 16 in one upgrade cycle.

**Alternatives considered:**
- Pin to `next@15` first, ship, then upgrade to 16 in a follow-up sprint — two upgrade cycles.
- Stay on 14 indefinitely — leaves the unresolved npm audit CVE in place even if not actively exploitable.

**Rationale:** The breaking changes between 14→15 and 15→16 are similar (async params/cookies/headers in both). One migration cycle covers both. We're not running production-critical Next 15-only code (e.g. partial prerendering experiments), so there's no transition value from a 15 stop.

**Trade-offs:** Less Internet evidence of "Next 16 in production" patterns at the time of upgrade (Next 16 is days old). Mitigated by the upgrade being mechanical (4 files for params API + a `global.d.ts` shim for the auto-generated types issue).

**Revisit if:** Next 16 introduces a breaking change in a minor version that requires us to pin back.

## One school, one admin (auto-unassign on reassignment) — Sprint 12, 2026-04-24

**Decision:** When SUPERADMIN assigns School X to User B via `PATCH /api/v1/auth/admin/users/<id>/`, if School X is already bound to User A's `admin_school`, User A is automatically un-bound (`admin_school=NULL`) as part of the same atomic update.

**Alternatives considered:**
- Allow multiple admins per school (ManyToMany instead of OneToOne) — changes the data model and requires a permission-aggregation design.
- Reject the assignment with 409 Conflict if school is taken — forces SUPERADMIN to do two operations (unassign A, assign B).

**Rationale:** One-school-one-admin matches the real-world use case (each school has one HM; multi-admin is an edge case we don't need now). `admin_school` is already a OneToOneField. Auto-unassign is safe because SUPERADMIN is doing it deliberately (via the UI flow). No silent side-effect on the unassigned user's other permissions — they retain role=USER and can still submit suggestions, upload photos, etc.

**Trade-offs:** If SUPERADMIN meant to assign a different school to B but picked the wrong one from the search dropdown, they've accidentally unassigned A. Mitigated by: (a) confirmation-style modal UX, (b) `claimed_at` is NOT reset on unassign so history is preserved, (c) reassignment is reversible by re-assigning A in one click.

**Revisit if:** Schools start having deputy HMs who need separate admin access, or if MANY schools share cluster-level admins.

## Self-demotion safety over allow-with-warning — Sprint 12, 2026-04-24

**Decision:** SUPERADMIN cannot change their own role away from SUPERADMIN or deactivate their own account via the admin endpoints. Returns 403 with clear error. Applied at serializer/view level, covered by 3 dedicated tests.

**Alternatives considered:**
- Allow with confirmation modal ("Are you sure? You won't be able to undo this without another SUPERADMIN.")
- Soft-require: allow only if at least one other SUPERADMIN exists
- Hard-require: always forbid regardless of state

**Rationale:** At current scale (1 SUPERADMIN), self-demotion would lock the entire organisation out of user management. Recovery path is manual DB update via Django admin, which is manageable but annoying. Prevention is strictly cheaper than recovery. Confirmation modal is easy to tap-through by accident. "Allow if 2+ SUPERADMINs" is more permissive but adds branching logic that's rarely exercised and potentially buggy.

**Trade-offs:** If we ever WANT to transfer SUPERADMIN cleanly (promote B, then demote A), it takes two steps instead of one — promote the new one first, then someone else can demote A. Acceptable friction.

**Revisit if:** We adopt 3+ SUPERADMINs and want convenient role rotation, or if we build a formal "transfer role" flow.
