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

## Supabase Storage (S3-compat) over GCS for school images — Sprint 13, 2026-04-26

**Decision:** Store school image bytes in a dedicated Supabase Storage bucket (`school-images`), accessed via the S3-compatible endpoint, configured as Django's `STORAGES["default"]` backend (`storages.backends.s3.S3Storage`). Files are public; no signed URLs.

**Alternatives considered:**
1. Google Cloud Storage bucket in the same `sjktconnect` GCP project — requires another credential set + IAM management + an additional CDN config. Egress to Cloud Run from GCS is free in-region, but cross-region from frontend visitors costs.
2. Cloudflare R2 — also S3-compatible, free egress, but adds a third infra provider beyond Cloud Run + Supabase.
3. Keep storing URLs (status quo) and re-harvest more aggressively — doesn't solve the root cause; Google can still rotate IDs.
4. Postgres BinaryField — already proved unsuitable for community uploads (TD-07).

**Rationale:** We're already on Supabase for Postgres. Adding Storage is one menu click + one bucket policy + one set of S3 credentials in the same dashboard. `django-storages[boto3]` makes the integration boring (one settings block, no per-call code changes). Public read access matches our use case (school photos are public-by-design). Public bucket means the URLs are stable forever — `display_url` returns a CDN URL that lives at `kafuxsinrbqafvarckxu.storage.supabase.co/storage/v1/object/public/school-images/schools/<moe>/...`. Frontend bypasses our backend entirely for image bytes, eliminating the egress burden TD-06 was tracking.

**Trade-offs:** Bound to Supabase Storage pricing tiers (free 1 GB / 2 GB egress per month at our current plan). At 1534 images × ~150 KB avg ≈ 230 MB of stored bytes; well within free tier. Not portable to a different Postgres provider without bucket migration. Can't use signed URLs without flipping `querystring_auth=True` and rotating credentials, but that's a setting change not a re-architecture.

**Revisit if:** Storage volume crosses 5 GB (consider lower-cost archival tier or GCS), or if we ever need per-user signed access (e.g. for un-approved community uploads visible only to moderators — currently solved by keeping image bytes private inside `Suggestion.image` BinaryField until approval).

## `display_url` property over conditional fallback at every callsite — Sprint 13, 2026-04-26

**Decision:** Add `SchoolImage.display_url` as a `@property` that returns `image_file.url` if `image_file` is set, otherwise falls back to legacy `image_url`. Callers use `obj.display_url` and don't branch on which field is populated. Legacy `image_url` field is retained, not dropped.

**Alternatives considered:**
1. Drop `image_url` immediately and require all rows to have `image_file` before merge — forces an atomic migration with no rollback path; one bad row breaks every API call.
2. Branch in every serializer / view (`obj.image_file.url if obj.image_file else obj.image_url`) — duplication across ~5 call sites + every new caller has to remember.
3. Custom field manager / queryset method — heavier than a property, no real benefit.

**Rationale:** The migration was always going to be staged: harvester rewrite → migrate command → re-harvest passes for failed rows. During staging, some rows have `image_file`, some still have `image_url`, some have both. A property hides this entirely. Once the migration was 100% complete (post-Sprint-13), `image_url` becomes redundant — but keeping it costs nothing at the row level (it's a TextField that's already there) and gives us a free safety net if a future `image_file` write fails (corruption, accidental delete) — old `image_url` value still exists for forensics.

**Trade-offs:** Two fields covering roughly the same thing is a faint code smell. Schema is slightly bloated. We could drop `image_url` in a future cleanup sprint once we're confident no row depends on it; tracking as a low-priority cleanup item, not urgent.

**Revisit if:** We need to enforce "every row must have image_file" for some downstream invariant (e.g. analytics on byte size), or if `image_url` accumulates real divergent data we'd want to clean up.

## Lazy-fetch detail on InfoWindow open over including all fields in `/schools/map/` — Sprint 13, 2026-04-26

**Decision:** Keep `/api/v1/schools/map/` trimmed to ~10 fields (Sprint 8.3 egress fix). When the map InfoWindow opens, lazy-fetch the full school detail via `fetchSchoolDetail(moe_code)` and merge into local state. No re-harvest is triggered — the detail endpoint reads existing `SchoolImage` rows.

**Alternatives considered:**
1. Add `image_url` (and other display fields) back to `/schools/map/` — undoes the Sprint 8.3 egress optimisation that brought map payload from ~500 KB to ~50 KB. Egress cost would likely double.
2. Server-render the InfoWindow content in the same payload as a HTML blob — heavy, awkward for SPA-style interaction, breaks i18n flow.
3. Pre-fetch all 528 detail records on map mount — similar payload bloat as #1, with worse cache characteristics.

**Rationale:** The map is a high-traffic page (Googlebot + organic). The InfoWindow is a low-frequency interaction (only opens when a user clicks a pin). Optimising for the high-frequency case (map render) and paying the cost on the low-frequency case (detail fetch on click) is the correct trade-off. The detail fetch is also opportunistically cacheable by the browser since the URL is deterministic per school.

**Trade-offs:** Brief UX delay (~200ms typical) between clicking a pin and seeing the full hero image. Mitigated by rendering placeholder UI immediately + populating image when fetch resolves. Cancellation flag prevents stale-merge if the user clicks rapidly between pins.

**Revisit if:** Detail-fetch latency becomes user-perceptible (>500ms p95), or if InfoWindow click-through rate becomes high enough that bundling fields into the map payload is cheaper overall.

## `Suggestion.pending_image` ImageField over a separate StagedPhoto model — Sprint 14, 2026-04-26

**Decision:** Add `pending_image: ImageField` directly on `Suggestion` (path: `pending/<uuid>.<ext>` on the public `school-images` Supabase bucket). On approve, copy bytes to a fresh `SchoolImage.image_file`; on reject, delete the file. Bytes for un-approved uploads sit on a public bucket but at unguessable UUID paths.

**Alternatives considered:**
1. Separate `StagedPhoto` model with FK to Suggestion — more "correct" but doubles the number of DB rows for what is effectively a one-to-one relationship while in PENDING state.
2. Private Supabase bucket with signed URLs for pending images — eliminates the URL-secrecy bet but adds a separate bucket, separate bucket-policy config, signed-URL generation in serializers, and signed-URL refresh in moderator UI.
3. Keep BinaryField in Postgres for pending bytes only (drop on approve) — preserves the BinaryField cost we were trying to escape; just makes it transient.

**Rationale:** PENDING is short-lived (moderator queue typically clears within a day at our scale). UUID paths (32 hex chars) on a public bucket give effective access control via URL secrecy — a leaked URL exposes one user's pending photo, not catastrophic. Operational simplicity (one bucket, no signed URLs) is worth the modest residual risk.

**Trade-offs:** A leaked `pending_image_url` (e.g. via browser history of a moderator) gives anyone with the URL access to that one image until the suggestion is approved (file moves) or rejected (file deletes). For a community-photo platform this is acceptable; for sensitive content it would not be.

**Revisit if:** PENDING-photo content sensitivity changes (e.g. people start uploading children's faces with identifying captions) or if Supabase introduces sub-bucket signed URLs at low complexity.

## MODERATOR excluded from photo approval — Sprint 14, 2026-04-26

**Decision:** `IsPhotoApprover` permission grants approve/reject rights ONLY to SUPERADMIN or the bound school admin (`admin_school_id == suggestion.school_id`). MODERATOR role is explicitly NOT a photo approver, even though MODERATOR can approve DATA_CORRECTION and NOTE suggestions.

**Alternatives considered:**
1. Allow MODERATOR for all suggestion types (status quo from Sprint 8.2) — uniform but conflates "platform-wide quality" (notes, data corrections) with "school-specific representation" (which photo represents this school).
2. Add a separate PHOTO_MODERATOR role — more granularity but adds a fourth role with limited use case at our scale.
3. Allow MODERATOR but require school-admin co-sign for photos — workflow complexity not justified by the volume.

**Rationale:** Photos are school-scoped representational decisions; MODERATORs operate at the platform level and don't have local knowledge of "is this actually our school?" or "is this hero photo flattering enough?". School admins have that context; SUPERADMIN has it via override authority. Concentrating photo decisions on people who'll be held accountable for the result keeps the moderation queue intentional rather than rubber-stamped.

**Trade-offs:** If a school has no admin yet (most schools at present), only SUPERADMIN can approve photos for them. This is a soft bottleneck — mitigated by the auto-claim mechanism (`@moe.edu.my` Google sign-in auto-binds `admin_school`) which is already in place.

**Revisit if:** Volume of pending photos exceeds the SUPERADMIN's bandwidth before more schools have bound admins, OR if we ever want a "trust trail" feature where MODERATOR pre-screens then a school admin gives final approval.

## 20-photo cap enforced at approve, not upload — Sprint 14, 2026-04-26

**Decision:** Uploads are accepted regardless of how many APPROVED photos a school has; the `PHOTO_CAP_PER_SCHOOL = 20` check fires at approve time and returns 409 `slot_full`. Service layer also no-ops as defence in depth.

**Alternatives considered:**
1. Reject uploads at submit when school is at cap — upfront feedback to user, but penalises the user for moderator backlog.
2. Auto-replace the lowest-ranked existing photo — too magical; users wouldn't know what got bumped.
3. Cap PENDING+APPROVED combined — would block uploads when many are PENDING, again pushing user-visible failure for moderator inaction.

**Rationale:** Cap is fundamentally about display quality (don't drown a school page in 50 photos), not about storage or queue management. Display-time enforcement is the right place. Moderator gets a clear `slot_full` banner and a link to the image manager to delete an existing photo first; user sees nothing scary.

**Trade-offs:** Slightly more storage churn — uploads that ultimately can't be approved still consume Supabase egress + storage briefly. At our scale (community uploads are rare) this is negligible. A janitor command can clean up long-PENDING photos for schools at cap if it ever becomes a real cost.

**Revisit if:** Storage cost becomes meaningful (we'd need ~10× more uploads-per-day before this matters), or if the moderator queue regularly fills with un-approvable photos at popular schools.

## `yet-another-react-lightbox` over alternatives — Sprint 15, 2026-04-26

**Decision:** Adopted `yet-another-react-lightbox` (~15 KB gzipped, MIT, with first-party Captions plugin) for the public photo lightbox. Lazy-imported via `next/dynamic` so the lib loads on first click and is excluded from SSR + the first-load JS budget.

**Alternatives considered:**
1. **`react-image-lightbox`** — older, ~30 KB, last meaningful release 2021. Discontinued in spirit.
2. **`react-photo-view`** — small, smooth pinch-zoom, but no caption plugin and no plugin architecture for future features (download, share).
3. **`yet-another-react-lightbox`** — actively maintained, plugin architecture, captions/zoom/thumbs/fullscreen plugins available individually. ESM-only.
4. **Hand-roll a `<dialog>` + `useEffect` swipe handler** — total control, no dep, but ~200 lines + a swipe library + accessibility work. Not worth it for our scale.

**Rationale:** Smallest actively-maintained option with a clean plugin interface. The plugin architecture means we can add zoom/share/download in Sprint 16+ without changing the wrapper. Lazy-loading neutralises the bundle-size concern for users who never click a photo.

**Trade-offs:** ESM-only ships breaks Jest unit tests of the wrapper without a `transformIgnorePatterns` exception. Resolved by leaning on integration tests in `SchoolImage.test.tsx` instead of unit-testing `PhotoLightbox` in isolation. Lessons.md captures the general rule for any future ESM-only frontend lib.

**Revisit if:** The plugin architecture becomes a maintenance burden as we add more interactive features (e.g. report-photo button, in-lightbox edit), or if a meaningfully smaller actively-maintained alternative emerges.

## `SchoolImage.caption` (not `Suggestion.caption`) — Sprint 15, 2026-04-26

**Decision:** The caption field lives on `SchoolImage`, edited via `PATCH /schools/<moe>/images/<id>/caption/` post-approval. The `Suggestion` model does not get a caption field; uploaders cannot supply a caption at upload time.

**Alternatives considered:**
1. **Caption on `Suggestion`, copied to `SchoolImage` at approve** — uploaders write captions, moderators edit before approving. More user-friendly but doubles the edit surface (two places where a caption can be wrong).
2. **Caption on both, with `SchoolImage.caption` taking precedence** — most flexible, but the precedence rule is the kind of subtle gotcha that breaks 6 months later.
3. **Caption only on `SchoolImage`, edited post-approval (chosen)** — simpler lifecycle: caption is a property of the persistent image, not of the ephemeral suggestion.

**Rationale:** Captions describe the *photo* (e.g. "Hall block, viewed from the field"), which is a property of the persistent image. Letting uploaders write captions adds a moderation surface (offensive captions, misleading claims) without commensurate value at our current scale. Editing post-approval keeps the moderation workflow focused on the photo itself; captions can be polished by school admins after the fact.

**Trade-offs:** Loses the "uploader's voice" aspect. If we ever want photo attribution to the uploader-as-author, we'd need a separate `attribution` field — but that's distinct from a descriptive caption and can be added later without breaking this decision.

**Revisit if:** Community uploads scale enough that the SUPERADMIN bandwidth for caption editing becomes a bottleneck, OR if uploaders start consistently providing context in their suggestion notes that would make a better caption than what admins write.

## Logout endpoint is `AllowAny` + idempotent — Sprint 15, 2026-04-26

**Decision:** `POST /api/v1/auth/logout/` flushes `request.session` with no permission check (`AllowAny`) and returns 200 on every call, including when the session is already empty.

**Alternatives considered:**
1. **`IsAuthenticated` permission** — only allows logout when there's an active session. Symmetrical with login. **Rejected** because the bug we're fixing is exactly "the session is stale and the user wants to flush it without re-authenticating".
2. **Return 401 if no session to flush** — symmetric with HTTP semantics but useless to the frontend (which would have to ignore the 401).
3. **`AllowAny` + idempotent (chosen)** — calling logout always succeeds regardless of state. Frontend doesn't have to branch on session state.

**Rationale:** Logout is the operation that exists to handle the "I want to be in a logged-out state" command. Refusing the request because the user is already logged out (or has a stale credential) defeats the purpose. CSRF is mitigated by the request being a no-op for unauthenticated callers — there's nothing to forge.

**Trade-offs:** A bot hitting `/logout/` constantly adds a Cloud Run request count but zero state change. At our scale, the cost is negligible. If it ever became measurable, throttling would be the right tool, not permission gating.

**Revisit if:** Logout becomes a user-visible action with side effects beyond session flush (e.g. invalidating refresh tokens, broadcasting a "user signed out" event), in which case the surface needs to be re-evaluated as a whole.

## `__Secure-` cookie override on csrfToken instead of upstream patch — Sprint 16, 2026-04-27

**Decision:** In `frontend/lib/auth.ts`, override `@auth/core`'s default `csrfToken` cookie name from `__Host-authjs.csrf-token` to `__Secure-authjs.csrf-token`. All other Auth.js cookies (state, pkceCodeVerifier, sessionToken) keep their `__Secure-` defaults.

**Alternatives considered:**
1. **Fork @auth/core or pin a custom build** — guarantees the change can't drift, but maintenance burden across every upstream release.
2. **Configure Cloudflare to stop modifying `Set-Cookie`** — would require finding which Cloudflare feature does the modification (Page Rules? Workers? Cache?) and disabling it; risks breaking other behaviour we depend on; opaque to future maintainers.
3. **Override cookie name in our auth.ts (chosen)** — surgical, preserves the security intent of cookie prefixes (we drop one notch from `__Host-` to `__Secure-`, keeping the secure-context + httpOnly + sameSite=lax guarantees), survives Auth.js upgrades because cookies override is a public API.
4. **Drop CSRF cookie entirely** — strictly worse than option 3; removes the protection rather than adapting it to Cloudflare.

**Rationale:** The `__Host-` prefix's strict requirements (no `Domain` attribute, `Path=/`, must be from a secure origin) are incompatible with Cloudflare's `Set-Cookie` rewriting behaviour in our config. The browser silently drops the cookie when prefix semantics are violated. `__Secure-` keeps the secure-only + httpOnly properties without the `Domain`/`Path` strictness, which is the actual constraint Cloudflare can't satisfy. The state and pkceCodeVerifier cookies — which contain the actual OAuth flow secrets — already default to `__Secure-` and survive Cloudflare unchanged, so the security story is consistent: every flow-secret cookie is secure-only, none rely on `__Host-` strictness.

**Trade-offs:** We give up the `__Host-` extra-strict guarantee on the csrfToken cookie (no `Domain` override). At our scale, with a single registrable domain (tamilschool.org) where all auth happens, the `Domain` defence is practically unused. If we ever multi-tenant onto subdomains where csrfToken-cookie scope matters, we'd need to revisit — but that's a different deployment shape.

**Revisit if:** Cloudflare changes its `Set-Cookie` handling to be `__Host-`-compliant (would let us tighten back), or if we deploy on a different proxy/CDN that doesn't have this issue, or if Auth.js stops exposing the cookies override.

## Module-scoped pub/sub for "Django session ready" — Sprint 16, 2026-04-27

**Decision:** Created `frontend/lib/auth-events.ts` — a ~30-line module-scoped pub/sub emitter (`emitProfileReady` / `onProfileReady`). `UserMenu` calls `emitProfileReady()` after `syncGoogleAuth()` resolves; `EditSchoolLink` and `SuggestButton` subscribe via `onProfileReady` and re-fetch `/me` on the signal. No React Context, no TanStack Query, no setTimeout polling.

**Alternatives considered:**
1. **React Context with profile state** — would force a Provider above every component that needs auth. Most components on the school page don't need auth at all; wrapping all of them in a context to serve two consumers is overkill.
2. **TanStack Query / SWR** — gives us proper cache invalidation + retry-on-window-focus. Heavyweight introduction (new dep, new concept, ~50 KB) for two consumers. Would be the right call if we had 5+ auth-aware components, but we don't.
3. **setTimeout retry in the consumers** — quick and dirty: if fetchMe returns null while authenticated, retry after 500ms, give up after 3 tries. Hides the race rather than fixing it; brittle to changes in the cookie-write timing.
4. **Move syncGoogleAuth into AuthProvider so it runs before any consumer mounts** — the cleanest architectural fix, but requires lifting the syncGoogleAuth + profile state up the tree, plus a Context for consumers. Heavier change for the same outcome.
5. **Module-scoped pub/sub (chosen)** — minimum viable abstraction. Two consumers wire in with `useEffect(() => onProfileReady(load), [])`; UserMenu fires the signal once. No global Provider, no waterfall.

**Rationale:** The race is a one-shot ordering problem between two effects that both react to the same NextAuth state transition. The minimum information needed to fix it is a single signal: "the Django session is ready." A module-scoped Set + emit() + on() expresses exactly that, no more. Pure JavaScript, no React-specific machinery. If a future consumer outside the React tree needs the same signal (a service worker, a background fetch handler), the module just exports `onProfileReady` and they wire in.

**Trade-offs:** No React Context means no automatic re-render — consumers have to call setState themselves inside the listener. Acceptable for our two consumers; if we ever have 5+, a Context or SWR is worth re-evaluating. Also: module-scoped state survives hot reload differently than Context — but our build doesn't do React Refresh of this module path so it's not a concern.

**Revisit if:** A third or fourth auth-aware component starts subscribing — at that point a `useCurrentProfile()` custom hook or full Context becomes more ergonomic.

## TD-11 + TD-12 (test-coverage padding) deferred indefinitely — Sprint 16, 2026-04-27 (PARTIALLY REVERSED 2026-04-28)

**Decision:** TD-11 (`accounts/services/google.py` 25% coverage) and TD-12 (`hansard/pipeline/extractor.py` 26% coverage) are marked deferred — no scheduled sprint. They'll be picked up if and when the underlying code changes or starts producing bugs.

**Alternatives considered:**
1. **Sprint 17 dedicated to test-coverage** — would honour the "every TD eventually closes" pattern but adds a sprint of low-leverage work for coverage on stable, well-exercised paths.
2. **Roll into Sprint 16 (chosen at sprint-start)** — would have stretched a Code-Quality Pass into a Test-Coverage Pass too. Different in flavour; would have lost focus.
3. **Defer indefinitely (final choice at close)** — the code in question (Google ID token verification, PDF extraction) hasn't changed in 8 sprints and hasn't produced a single bug since the modules were written. Coverage as a number doesn't mean these paths are correct; it means certain branches aren't exercised by tests. Adding tests now costs time without reducing real risk.

**Rationale:** Test coverage is a means, not an end. The 25% and 26% numbers come from large try/except branches and dead-code-via-environment paths (e.g. SQLite vs Postgres) that are intentionally untested in the local suite — they'd require fixture proliferation to exercise. The actual user-facing flows (sign in works, hansard PDFs extract correctly) are tested via integration / end-to-end paths. Marking these "deferred indefinitely" is more honest than "Sprint 17" if there's no real plan to do them.

**Trade-offs:** If the underlying code ever DOES break in an untested branch, the regression won't be caught by the suite. Acceptable: those branches are well-isolated (Google's verify_oauth2_token error paths; pdfplumber's encrypted-PDF path), and a real failure surfaces visibly on prod before silently corrupting data.

**Revisit if:** Either module starts producing bugs in production, OR a refactor of either module is on the table (in which case adding tests around the change is the right move).

**Update 2026-04-28:** TD-11 reversed and resolved. After re-surveying both items at Sprint 18 close, TD-11 (Google auth) was a 30-min surgical fix because (a) the file was small (51 LOC) with an existing test file ready to extend, (b) the failure paths are security-critical (forged-issuer, audience mismatch) — insurance worth carrying, (c) the cost-benefit ratio actually favoured the fix at this size. Coverage now 82%; see TD-11 entry in tech-debt.md. **TD-12 stays deferred** — its cost ratio is genuinely poor (no test file, no PDF fixtures, ~2-3 hours to author both), and a hansard-format-change failure is loud not silent (the pipeline crashes, doesn't corrupt data). Explicit trigger for TD-12: "if `hansard/pipeline/extractor.py` is modified for any reason — Hansard format change, library bump, refactor — add the missing edge-case tests as part of that change rather than as standalone work."

## IPBlockMiddleware in app code, not Cloud Armor / Cloudflare WAF — Sprint 17, 2026-04-27

**Decision:** Block known abusive scraper IPs via a Django middleware (`backend/core/middleware.py — IPBlockMiddleware`) wired FIRST in the `MIDDLEWARE` chain, instead of using Google Cloud Armor or Cloudflare WAF firewall rules.

**Alternatives considered:**
1. **Cloud Armor security policy** with a deny rule on the IP — rejects at the edge, no Cloud Run cold-start cost. Operational: another GCP resource to remember + version. State lives in GCP, not in the repo.
2. **Cloudflare WAF rule** (we're behind Cloudflare proxy) — same edge-rejection benefit, lives in Cloudflare dashboard. Same drawback: state outside the repo.
3. **App-level middleware (chosen)** — block lives in code, runs on every request that reaches our app. Each blocked request still wakes a Cloud Run instance; middleware short-circuits before routing/DB.
4. **robots.txt update** — useless for scrapers that ignore robots.txt (which is exactly the population we're blocking).

**Rationale:** The block lives in code, so it's testable (6 unit tests), reviewable (PR diff shows the IP being added), and travels with deploys. Anyone restoring from backup gets the block back automatically. Cloud Armor / WAF rules silently disappear from the repo's mental model — the next maintainer would have to know to check them. At our current scale (one IP, ~1,400 req/day) the cost of waking a Cloud Run instance to return 403 is negligible compared to the egress of NOT blocking. The middleware runs as the first entry in `MIDDLEWARE`, so the request never touches routing, the DB, serializers, or any other significant work.

**Trade-offs:** Each blocked request still costs one Cloud Run request count + a few ms of cold-start CPU. If the blocklist grows past ~50 IPs OR if the volume per blocked IP exceeds ~100K/day, the math flips and Cloud Armor becomes the right answer. We're nowhere near either threshold.

**Revisit if:** Blocklist grows >50 entries, total blocked traffic exceeds 1M req/day, or we discover we're paying meaningfully for the Cloud Run wake-up cost on blocked requests.

## Distribution metric (not counter) for per-route egress — Sprint 17, 2026-04-27

**Decision:** The two new Cloud Logging metrics (`sjktconnect_api_egress_per_route` + `sjktconnect_web_egress_per_route`) are DISTRIBUTION value-type metrics over `httpRequest.responseSize`, not COUNTER metrics summing total bytes.

**Alternatives considered:**
1. **Counter / GAUGE summing bytes per route** — simplest, just gives total bytes. Can't answer "is the median response growing?" or "is there a long-tail of huge responses?".
2. **Distribution (chosen)** — records the size of each individual response in histogram buckets. Cloud Monitoring can then sum, average, percentile, or histogram any way we want.
3. **Two metrics: counter for total + summary for size distribution** — twice the metric storage cost, less ergonomic to query. The distribution alone supports both "total bytes" (sum aggregator) and "median/p99 bytes" (percentile aggregator) from the same series.

**Rationale:** Egress problems take two shapes — a steady increase in baseline traffic (catchable with sum-over-time) and a long-tail of one-off huge responses (catchable only with percentile/histogram view). A distribution gives us both from one metric. Same Cloud Logging cost as a counter. The bucket option `exponentialBuckets={numFiniteBuckets:20, growthFactor:4, scale:100}` covers from ~100 bytes (404s, redirects) up to ~10 GB (catastrophic) in 20 buckets — comfortable for a 4-9 KB typical-API-response codebase.

**Trade-offs:** Distribution metrics with high-cardinality labels (route × user_agent here) consume slightly more query-time CPU in Metrics Explorer than counters. At our metric volume (a few thousand requests/day distributed across ~30 routes × ~20 user-agents) the cost is invisible. If routes or user-agents ever exploded to 1000s, we'd need to drop one of the labels.

**Revisit if:** Metric query times in Metrics Explorer become noticeable, or if we cross into pricing-tier territory on Cloud Monitoring (currently well within the free quota).

## `backfill_since` widens briefs + meeting_reports only — Sprint 18, 2026-04-27

**Decision:** The new `--backfill-since` flag on `compose_monthly_blast` (Sprint 18) widens the lookback window for SittingBriefs and ParliamentaryMeeting reports, but NOT for HansardMentions, NewsArticles, or MPScorecards.

**Alternatives considered:**
1. **Apply backfill to all sources uniformly** — simpler API; the date param means the same thing for every query.
2. **Apply backfill only to briefs + meeting reports** (chosen) — matches the user's mental model of "things I missed since X date" which only applies to long-running summary artifacts.
3. **Per-source backfill flags** (`--backfill-briefs-since`, `--backfill-meetings-since`, etc.) — most flexible but cluttered for a one-time-fill scenario.

**Rationale:** Mentions and news are point-in-time events tied to the month they happened in. Backfilling them would surface content that was either already in a prior digest (duplicate) or that should appear in its native month, not retroactively in a later month. Scorecards are intentionally lifetime-aggregated already — backfill doesn't apply to them. Briefs and meeting reports are the only artifacts where "I missed this content from a prior period" is the natural complaint, because they're synthesised post-hoc and may be published days or weeks after the underlying events. The flag name is generic enough to extend later if a source needs it; the docstring documents the current narrow semantics.

**Trade-offs:** Operators who wanted "include all March news in the April digest" would expect this flag to do that. They'd be surprised. Mitigated by the docstring + the dry-run output explicitly listing which sources are widened. If the surprise becomes real, switching to per-source flags is a small refactor.

**Revisit if:** A real use-case appears for backfilling mentions or news (e.g. a late-arriving Hansard PDF that gets analysed weeks after the sitting). At that point either widen this flag's semantics or add a sibling flag.

## `scorecards_are_lifetime_fallback` as side-channel bool — Sprint 18, 2026-04-27

**Decision:** When `aggregate_month()` falls back to lifetime top-3 MP scorecards (because no MP was active in the target month), it returns the queryset AS-IS plus a separate `scorecards_are_lifetime_fallback: True` boolean in the result dict. Templates and the analyst prompt read the bool to label the section accurately ("Lifetime top MPs" vs "Most active MPs this month").

**Alternatives considered:**
1. **Encode the fallback in the queryset itself** (annotate, custom manager method) — would require introspecting SQL or wrapping in a custom class to read it back out at the template layer. Excessive for one bool.
2. **Empty the scorecards section when no MP is active** — cleanest semantically but leaves the section visually blank in quiet months, which looks like a bug.
3. **Include lifetime data ALWAYS, mention "this month" or "lifetime" via labels** — simpler, but would lose the meaningful signal "this MP was active this month vs last quarter".
4. **Side-channel bool (chosen)** — minimum information needed; template + analyst stay simple; the flag is exactly where you'd look for it (the result dict).

**Rationale:** The fallback is editorially distinct from "real" current-month data; readers should know which they're seeing. The bool conveys exactly that fact in 4 bytes. No fancy abstraction needed.

**Trade-offs:** The result dict now has 6 keys (was 3 in Sprint 2.7). Each new key adds a tiny cognitive load when reading aggregator output. Acceptable; the alternatives all add more.

**Revisit if:** The result-dict shape grows to 10+ keys (at which point a typed dataclass would be ergonomic), or if the fallback semantics need to extend to per-source labels (e.g. "news is lifetime fallback").

## 5-tab layout for the school edit page — Sprint 19, 2026-04-28

**Decision:** `/school/[moe_code]/edit` is rebuilt as a 5-tab layout (Core, Contact, Leaders, Support, Images) rather than the prior single long form, collapsible sections, or a multi-step wizard. Active tab id persists in the URL hash (`#core`, `#contact`, …) so deep-links and browser back navigation work.

**Alternatives considered:**
1. **Long single form (status quo)** — kept everything visible at once but required heavy scrolling for 20+ fields and made it easy for school admins to miss sections (especially the Leaders + Support sections at the bottom).
2. **Collapsible sections** — visible group headings, click to expand. Pros: still single-page, no tab-state mental model. Cons: accordion state is fiddly (open one, close another? remember across page loads?), URL deep-links are hard, screen-readers struggle.
3. **Multi-step wizard (Next / Back)** — implies a sequential flow. School admins typically want to edit ONE thing (e.g. update enrolment after a new school year). A wizard makes one-thing edits N clicks instead of 1.
4. **Tabs (chosen)** — direct random-access to any section, deep-links via hash, URL changes communicate position to screen readers via `aria-selected`, keyboard nav works.

**Rationale:** School admins are not new users learning the app; they're return users updating one or two fields. Tabs match that mental model. Hash-persisted tab id means a "claim button" or future email could link directly to a specific tab (e.g. `/school/<moe>/edit#support` to prompt a school to add bank details for the donations card).

**Trade-offs:** A user who edits across multiple tabs has to click Save on each. We accept the friction — it makes the per-tab change boundary explicit and keeps the audit log entries focused. If real users complain, we can hoist the Save button to a sticky footer that scopes to the current tab without losing in-progress changes when switching tabs.

**Revisit if:** A common workflow emerges that crosses tabs (e.g. "update enrolment, then immediately update bank details") and users complain about per-tab saves. At that point a sticky footer with cross-tab change tracking is the right fix.

## Single endpoint for both detail + edit pages — Sprint 19, 2026-04-28

**Decision:** `SchoolEditSerializer` was extended with read-only MOE metadata (`ppd`, `grade`, `assistance_type`, `skm_eligible`, `location_type`, `gps_lat`, `gps_lng`, `gps_verified`, `claimed_at`) and a nested `leaders` array — so the tabbed edit page renders from a single `GET /api/v1/schools/<moe>/edit/` call instead of fetching `SchoolDetailSerializer` separately for the read-only context.

**Alternatives considered:**
1. **Two endpoints** — fetch `/edit/` for writable fields + `/detail/` for read-only context. Cons: two round trips, frontend has to coordinate two `useState` + loading states.
2. **One endpoint with everything** (chosen) — extend `SchoolEditSerializer`. Cons: serializer is now ~80% of `SchoolDetailSerializer` (duplication risk).
3. **Single shared serializer used by both views** — collapse `SchoolEditSerializer` into `SchoolDetailSerializer` with `read_only` markers per field. Cons: detail endpoint payload grows even for non-editing consumers (the public school page doesn't need the editable-field structure); also harder to audit "what can a school admin actually write?" when the writable surface is scattered across markers.

**Rationale:** The edit page is admin-only and rare; one extra round trip is invisible to a single human user, but **two round trips means two race conditions to handle** (which loaded first, what if one fails). Single endpoint is simpler frontend code. Duplication risk is real but small — the two serializers are likely to diverge over time (detail will add public-only fields like `image_url`, edit will add admin-only metadata) and we can refactor when the divergence is concrete rather than hypothetical.

**Trade-offs:** Field-level changes need to be made in both serializers if they need to appear in both. We accept this — the cost is bounded (max 9 fields shared today) and the alternative is worse (two-call coordination on every tab switch).

**Revisit if:** The read-only field list in `SchoolEditSerializer` and the equivalent in `SchoolDetailSerializer` start to genuinely diverge in semantics, OR if a third consumer needs the same shape (at which point a shared base serializer becomes worth the refactor).

## GPS edit gated to SUPERADMIN — Sprint 19, 2026-04-28

**Decision:** GPS lat/lng fields on the school edit page are **read-only for school admins**, **editable for SUPERADMIN**. School admins see a "verified via Google Places" badge alongside the muted-background readout.

**Alternatives considered:**
1. **Editable for any school admin** — assume the school knows its own location best. Risk: a single typo silently breaks the map for that school's pin.
2. **Editable for school admin if the pin is NOT yet verified** — a "verified→locked" workflow. Adds state-dependent UI logic; depends on `gps_verified` flag staying accurate.
3. **SUPERADMIN-only edit (chosen)** — any GPS correction is a small infrastructure-grade change that goes through a human-reviewed channel.
4. **No edit at all** — GPS is set entirely by the import scripts + Sprint 5.4 batch verification. Cons: doesn't cover the cases where Google Places had the wrong pin and a SUPERADMIN needs to correct it.

**Rationale:** Sprint 5.4 batch-verified 519 school pins via Google Places after a manual review of each diff. The verification flag `gps_verified=True` means a human (well, semi-human — the Google Places API + the human check) signed off on those coordinates. A school admin overriding their own pin to a wrong value would silently break the map and we wouldn't notice until a public visitor noticed. The expected volume of "GPS needs correcting" is very low (≤1/month), so funneling it through a SUPERADMIN review is fine.

**Trade-offs:** A school admin who genuinely needs to correct their pin has to email feedback@tamilschool.org. UX cost is real but low-volume. If volume rises, alternative #2 (verified-aware editability) becomes worth implementing.

**Revisit if:** SUPERADMIN gets >2 GPS-correction requests/month, OR a credible mechanism for "school-admin edit logged but GPS-verified flag goes False until SUPERADMIN re-approves" can be designed.

## SchoolLeader role immutable on PATCH — Sprint 20, 2026-04-28

**Decision:** `PATCH /api/v1/schools/<moe>/leaders/<id>/` accepts `name`, `phone`, `email` but NOT `role`. To change a leader's role, the operator deletes the old leader and creates a new one. The serializer's `update()` explicitly pops `role` from `validated_data` so a malicious PATCH including role is silently ignored.

**Alternatives considered:**
1. **Allow role to be updated via PATCH, validate uniqueness** — adds a PATCH-time uniqueness check, mutates the slot the leader occupies in the tabbed UI (confusing UX), and supports a workflow nobody asked for ("the same person now plays a different role").
2. **Role immutable (chosen)** — to change a leader's role, delete + recreate. Two clicks instead of one for an edge case.
3. **Don't expose `role` in the serializer at all on PATCH** — same effect as our `pop('role')` but harder to read at the call site. Ours is more explicit.

**Rationale:** A leader change in the real world ("PTA chair retired, board chair stepped up to PTA") is rarely "the same row, different role" — it's two separate transitions (delete the old, create the new). Allowing PATCH to mutate role models a transition that doesn't reflect how schools actually replace their leaders. Plus: the tabbed UI's slot pattern depends on `role` being stable for the row; mutating it would cause the leader to "jump" to a different tab section visually.

**Trade-offs:** A typo in the role at create time costs one delete + one create instead of one PATCH. Acceptable — typing a role wrong is rare (it's a constrained dropdown of 4 choices, not free text), and the recovery cost is two clicks.

**Revisit if:** A real workflow emerges where the same individual genuinely transitions between roles WITHOUT phone/email churn AND the two-click recreate flow is a friction point.

## Sequential save flush in LeadersTab, not parallel — Sprint 20, 2026-04-28

**Decision:** When the LeadersTab saves N pending changes (mix of creates / updates / deletes), it awaits each one sequentially rather than firing `Promise.all`.

**Alternatives considered:**
1. **`Promise.all` parallel save** — fastest wall-time. Cons: a delete and a create on the same role would race against the unique-active-role constraint. The "delete must commit before create can succeed" ordering is fragile to implement with parallel promises (you'd need to bucket changes by role and serialise within each bucket).
2. **Sequential save (chosen)** — N × per-call latency. With max 4 leaders per school and ~200ms per round trip, worst-case wall time is ~800ms — single-button-click perceptually.
3. **Bucket by role + parallel across roles** — middle ground. Adds complexity that isn't justified at N ≤ 4.

**Rationale:** The only constraint that matters is the unique-active-role constraint per school. A delete-and-recreate of the same role REQUIRES the delete to commit first. Sequential trivially satisfies this without bucketing logic. The performance cost is invisible to a single human user.

**Trade-offs:** If we ever scale to many leaders per school (we won't — the model is fixed at 4 roles), sequential save would become noticeable. Today's max is 4 changes per save; ~800ms total is fine.

**Revisit if:** The leader role list grows (new role choices added) AND users complain about save latency. At that point bucket-by-role-then-parallel is the right refactor.

## Default `fetchJSON` to ISR-cached fetch — Sprint 21, 2026-04-29

**Decision:** `fetchJSON()` in `frontend/lib/api.ts` always sets `next: { revalidate: 86400 }`. Server-rendered public pages inherit this automatically; auth endpoints bypass the helper and use direct `fetch()` with `credentials: "include"`.

**Alternatives considered:**
1. Force every caller to pass `next: { revalidate: ... }` — easy to forget; Sprint 17 demonstrated this exact failure mode at the page-`revalidate` level.
2. Two helpers: `fetchJSONCached()` + `fetchJSONFresh()` — adds API surface for a binary that's already implicit (auth = direct fetch; public = fetchJSON).
3. Accept an options parameter on fetchJSON — premature; only one knob would matter (cache window) and the default suffices.

**Rationale:** The vast majority of fetchJSON callers are server components on ISR-cached pages. Defaulting to cached makes the contract automatic and the override site obvious (auth endpoints with `credentials: "include"` are visually distinct in the file).

**Trade-offs:** A future endpoint that needs sub-24h freshness AND goes through fetchJSON would silently get cached. Mitigated by the auth split being clear at the call site.

**Revisit if:** A public endpoint needs sub-24h freshness (e.g. live counter) — at that point grow `fetchJSON` an `options` parameter.

## MQL over GUI aggregation for Cloud Monitoring distribution metrics — Sprint 21, 2026-04-29

**Decision:** All 4 widgets in the egress dashboard use Monitoring Query Language (MQL) instead of the GUI-style aggregation pipeline. Pattern: `fetch <resource>::<metric> | align delta(1h) | every 1h | group_by [metric.<label>], sum(value) | top N`.

**Alternatives considered:**
1. GUI aggregation with `perSeriesAligner: ALIGN_DELTA + crossSeriesReducer: REDUCE_SUM + secondaryAggregation.perSeriesAligner: ALIGN_SUM + pickTimeSeriesFilter` — what was deployed first, but the secondary aggregation didn't reliably fold distribution → scalar in API responses, leaving `pickTimeSeriesFilter` to error with "input cannot be a distribution" (the original Sprint 17 dashboard error).
2. Recreate metrics as INT64 instead of DISTRIBUTION — GCP rejects INT64 + valueExtractor (`A value extractor can only be specified for a DISTRIBUTION value type`).
3. Counter metric (INT64, value=1 per log line) for request counts + separate distribution for bytes — splits the data; harder to chart "bytes per route per UA".

**Rationale:** MQL `top N` produces scalar `doubleValue` per series deterministically. Verified live via `timeSeries:query` API. Source-of-truth dashboard JSON committed in `backend/docs/metrics/dashboard.json` so future sprints don't lose the working query.

**Trade-offs:** MQL queries are harder to edit in the GCP web GUI's chart builder. Future dashboard tweaks need YAML-style edits to the committed JSON or careful UI use.

**Revisit if:** GCP fixes the secondary-aggregation distribution-folding behaviour, or we move to a different observability stack.

## Empty `generateStaticParams()` over pre-building all 528 schools — Sprint 21, 2026-04-29

**Decision:** Each dynamic-segment public page exports `generateStaticParams() { return []; }`. Empty array opts the route into ISR-on-demand caching: nothing pre-built at deploy time; each unique URL caches on first hit for `revalidate` seconds.

**Alternatives considered:**
1. Pre-build all 528 schools × 3 locales = 1584 pages at deploy time — adds ~5 minutes to build, forces Cloud Build to reach the API for every URL, mostly wasted for low-traffic URLs.
2. Pre-build a curated top-N (e.g. 50 most-trafficked schools) — needs traffic data we don't have, plus extra logic to maintain the list.
3. Omit generateStaticParams entirely — Next 15+ treats this as "fully dynamic" and returns `Cache-Control: no-cache` (the actual Sprint 21 bug).

**Rationale:** Site traffic is low and uneven. Most school URLs may never be hit; pre-building them is wasted work. First-hit ~300ms latency is acceptable for the ones that do get hit.

**Trade-offs:** First hit on a given URL is uncached. Mitigated by Cloudflare absorbing repeat hits via `s-maxage=86400`.

**Revisit if:** Traffic increases such that first-hit latency becomes user-visible, or if Cloudflare cache hit rate drops because edges aren't seeing repeat traffic on the same URLs.

## SEO label island in `lib/seo.ts` — Sprint 22, 2026-05-01

**Decision:** Locale-aware labels used inside `generateMetadata` (Address/Alamat/முகவரி + Email + Phone + Location + Assistance + area-page terminology) are inlined in `frontend/lib/seo.ts` as plain TypeScript constants — not loaded via `next-intl/server.getTranslations`.

**Alternatives considered:**
1. Call `await getTranslations("schoolProfile")` inside `generateMetadata` so labels share the same i18n source as the page UI.
2. Move every label into `messages/{locale}.json` and load via a different mechanism (e.g. read JSON at build time).
3. Inline as done — duplicate the 10-15 labels needed for SEO into `lib/seo.ts`.

**Rationale:** Option 1 forces every dynamic-segment page to await translations during ISR generation, adding async surface to metadata that is already async (waiting on the API call). Option 2 adds machinery for marginal benefit. Option 3 keeps `generateMetadata` synchronous after the data fetch, and the label set is small (≈10 keys per locale × 3 locales = 30 strings) so drift risk is bounded.

**Trade-offs:** SEO labels can drift from UI labels. Mitigation: a comment in `lib/seo.ts` points at the `schoolProfile` namespace, and the unit tests for `buildSchoolMetadata` assert the exact label strings — so drift surfaces as a test failure, not a production bug.

**Revisit if:** the SEO label set grows beyond ~30 strings, or the project adopts a fourth locale (each locale forces another duplication).

## SEO snippet structure as labelled key/value pairs — Sprint 22, 2026-05-01

**Decision:** Meta descriptions for school / constituency / DUN pages are formatted as `Label: value · Label: value · ...` (using middot separator) rather than natural-language prose.

**Alternatives considered:**
1. Natural-language prose (the pre-Sprint-22 form): "SJK(T) Trolak is a Tamil primary school in Trolak, Perak. 17 students and 9 teachers..."
2. JSON-LD only — let Google extract structured data from `EducationalOrganization` schema and ignore the meta description.
3. Labelled k/v pairs (chosen): "Address: ... · Email: ... · Phone: ... · Location: ... · Assistance: ..."

**Rationale:** GSC observation of the Sprint 21 export showed Google's SERP snippet picker pulling rich-data snippets from `/ms/school/...` pages because the Bahasa Malaysia UI labels (Alamat/E-mel/Telefon) gave Google clear field cues. English/Tamil pages got generic prose snippets because their meta descriptions were prose. JSON-LD alone is a weaker signal than meta description for snippet selection. The k/v form is a single, consistent, locale-aware contract that travels everywhere Google parses (description tag, Twitter card, og:description). Loses some natural-language warmth; gains structured snippet candidacy on every locale.

**Trade-offs:** Meta description reads more like a data card than ad copy. For social-share previews (Slack, WhatsApp, Twitter) this is slightly less inviting than prose. The og:description carries the same labelled form, so social previews show the data block; this is acceptable for an info-oriented site (people copying a school link want the address, not a sales pitch).

**Revisit if:** GSC starts penalising "data-style" descriptions, or if engagement metrics (CTR / time-on-page) suggest social shares are being suppressed by the format.

## Branded SVG placeholder over Maps Static API for hero fallback — Sprint 22, 2026-05-01

**Decision:** When a school has no SchoolImage records, the hero gallery renders `/public/school-placeholder.svg` (1200×630, brand-coloured, contains "SJK(T)" + "Tamil Primary School" + "tamilschool.org"). Same URL is used as og:image and JSON-LD image fallback.

**Alternatives considered:**
1. Compute a Google Maps Static API URL using school GPS — gives a real satellite photo but bakes an API key into the rendered HTML for every page.
2. Compute a Google Street View Static URL — same key issue, plus Street View coverage is patchy in rural areas where many SJK(T) schools sit.
3. Generate a per-state PNG with state crest server-side — needs a backend job + storage of 11 images.
4. Ship one branded SVG (chosen) — single asset, no API key, deterministic.

**Rationale:** Sprint 13 lessons #24 says "Never bake API keys into stored URLs." Maps Static URLs are computed at render not stored, so the rule strictly doesn't apply, but the spirit (don't expose keys to bots crawling pages) does — Static Maps URLs are visible in `<img src>` and would be hit by every crawl. State crests are nicer but cost effort that doesn't directly drive SEO. The branded SVG is identical for all 528 schools — Google may treat that as duplicate-image signal, but the page-level uniqueness (title, description, address, schema) is the primary ranking signal; the image is for thumbnail extraction only. Worth it for the consistency.

**Trade-offs:** All schools share the same fallback image. SERPs may show identical thumbnails for schools without harvested photos. Mitigation: this is a *fallback* — Sprint 13 already harvests for most schools, Sprint 14 adds community uploads, so the fallback applies only to the long tail. As coverage improves, the fallback's prevalence decreases.

**Revisit if:** Google starts treating the shared placeholder as duplicate-content signal that hurts rankings, or if a backend job to generate per-state crest images becomes cheap (e.g. via Gemini image API).

## Cloudflare API automation over manual dashboard for canonical/redirect/DNS work — Sprint 22, 2026-05-02

**Decision:** Apply the www→root 301 redirect via the Cloudflare REST API (POST `/zones/{zone_id}/rulesets`, phase `http_request_dynamic_redirect`, Single Redirect rule) using a zone-scoped API token saved in `Development/SJKTConnect/.env`. Token permissions: DNS / Zone Settings / Config Rules / Single Redirect (all Edit). Future canonical/redirect/DNS work on the `tamilschool.org` zone defaults to API automation.

**Alternatives considered:**
1. Manual user action through the Cloudflare dashboard — clicked through Single Redirects UI on each operation.
2. Terraform / `cloudflare-go` / `pulumi-cloudflare` IaC — declarative, reviewable, but requires committing state files and learning a tool that owns one zone.
3. CLI tools (`cloudflare-cli`, `flarectl`) — same shape as direct REST calls but adds an intermediary tool to maintain.
4. Cloudflare API direct via Python `requests` (chosen) — minimal dependency, scriptable inline, leaves no state file, every change is auditable as a one-shot script.

**Rationale:** The Cloudflare zone in scope is small (one zone, ~5-10 settings touched in 18 months of operation). An IaC tool would add more setup and ongoing maintenance than it saves on a zone that changes ~quarterly. Direct API calls via `requests` give the same auditability (the call is in the commit message; the rollback is one DELETE) without binding the project to an IaC tool. The token lives in `.env` (gitignored) so the secret stays out of git. Token rolling is one click on the dashboard if it ever leaks. Permissions are zone-scoped, so a leaked token cannot affect other tamilfoundation.org zones. Sprint 22's www→root 301 took ~5 minutes from token creation to verified live, vs. an estimated 20-30 minutes of dashboard clicking with no checked-in artifact.

**Trade-offs:** No declarative state of "what should be on this zone" — the source of truth is whatever the Cloudflare zone actually has. If a setting is changed on the dashboard out of band, the next API run won't notice. Mitigation: keep change descriptions in CHANGELOG + retro + ruleset id in the memory file, so an audit can compare expected vs. actual. For a zone changing this slowly, that's adequate.

**Revisit if:** the zone gains ≥5 redirect rules, custom WAF rules, or worker bindings — at that point, declarative IaC saves more than it costs.

## Carryover items reclassified as Future work, not Sprint-N+1 deferral — Sprint 22, 2026-05-02

**Decision:** Sprint 22's two carryover items (Egress <150 MB/day confirmation; Task #43 Supabase Storage hot-link protection) are re-routed to (a) a single dated checkpoint on 2026-05-08 for the egress observation, and (b) the CLAUDE.md "Future work" bucket with a measurable pull-in trigger for Task #43 — *not* deferred to "Sprint 23".

**Alternatives considered:**
1. Defer both to Sprint 23 (mirror the Sprint 21 → Sprint 22 pattern that caused the drift).
2. Pull both into Sprint 23's plan (forces Sprint 23 to expand beyond its stated Monthly Digest Quality scope).
3. Reclassify Egress as monitoring (single dated checkpoint) and Task #43 as Future work with a pull-in trigger (chosen).

**Rationale:** Sprint 21 close said "Task #43 deferred to Sprint 22"; Sprint 22's actual scope was set by an unrelated GSC export that landed *after* Sprint 21 closed, so Task #43 was never engineered and silently slipped a second time. The pattern that broke: deferring by sprint index assumes the next sprint's scope is fungible. It isn't. The fix is to defer to "Future work with a measurable trigger" — that decouples the deferral from the sprint cadence and forces an explicit pull-in decision when the trigger fires. Egress monitoring is operational, not engineering — it doesn't belong on a sprint plan at all; it belongs on a calendar with a dashboard URL and a threshold.

**Trade-offs:** "Future work" can become a dumping ground if not pruned. Mitigation: each Future work item must include a pull-in trigger (egress >250 MB/day for 3+ days, in Task #43's case) and an estimate, so the bar to revisit is concrete. Items without triggers should be removed.

**Revisit if:** Future work accumulates >10 items without any being pulled in over 2-3 sprints — that's a signal the triggers are mis-calibrated or the items are stale.

## Fortnightly digest cadence: weekly cron + data-anchored 14-day guard, not a fortnightly cron — News Digest Stuck-Loop Fix, 2026-06-11

**Decision:** Keep the Cloud Scheduler cron at `0 9 * * 1` (every Monday) and enforce the fortnight in code: `compose_news_digest._should_skip()` skips unless the last SENT/SENDING/DRAFT digest's `coverage_end_date` is >= 14 days ago. The scheduler named `sjktconnect-fortnightly-digest` is therefore fortnightly-by-guard, not fortnightly-by-cron.

**Alternatives considered:**
1. True fortnightly cron `0 9 1-7,15-21 * 1` (1st + 3rd Monday) — structurally cannot double-fire; was the plan's original recommendation.
2. Weekly cron + a `sent_at`/`created_at`-based ~13-day skip window — rejected outright: a send can finish days after compose (2-day quota drain), so a timestamp guard would have wrongly skipped the owner's chosen 22 Jun issue (sent 11 Jun, only 11 days before).
3. Weekly cron + coverage-anchored 14-day guard (chosen).

**Rationale:** The owner locked a recovery timeline requiring the next full digest on Monday **22 June** — the 4th Monday of the month, which a 1st/3rd-Monday cron can never fire on. Beyond the one-off, the coverage-anchored guard produces a steadier cadence: exactly every 14 days (22 Jun, 6 Jul, 20 Jul…) versus the 1st/3rd-Monday pattern's irregular 14-or-21-day gaps across month boundaries. Anchoring on `coverage_end_date` (data) rather than timestamps follows lesson 60 and makes the cadence self-healing after any delay: the next issue is eligible exactly a fortnight after the last issue's *coverage*, regardless of when its send physically completed.

**Trade-offs:** The guard is now load-bearing — a bug in `_should_skip` re-opens the weekly double-fire this incident started with. Mitigated by regression tests (day-8 skip, exact-14 send, FAILED/CANCELLED/SENDING semantics) and two independent tripwires (window-width abort in compose; FAILED sweep in resume_sending). Also, the job name no longer matches its mechanics — acceptable; renaming a scheduler is churn with no behavioural benefit.

**Revisit if:** the digest cadence ever needs to be calendar-pinned (e.g. "always the 1st and 3rd Monday" for editorial reasons), or if a second guard bug causes a double-fire — at that point, switch to the fortnightly cron AND keep the guard as belt-and-braces.

## State name display: normalise at storage, not at display — Sprint 24, 2026-06-26

**Decision:** Rewrite `School.state` / `Constituency.state` / `DUN.state` to canonical compact form ("W.P. Kuala Lumpur", not "Wilayah Persekutuan Kuala Lumpur") via data migration `schools/0011`, AND apply `format_state()` at import in `import_schools.py` so future re-imports stay normalised. No display-time helper.

**Alternatives considered:**
1. Display-time helper — `format_state(s)` called from every component (frontend) + serializer (backend) that renders state. ~25 frontend files + ~5 serializers.
2. DB normalisation (chosen).
3. Hybrid — store raw, expose normalised via API only (frontend stays as-is). Would have kept MOE canonical form in the DB.

**Rationale:** State name is read in ~25 frontend files (state filter dropdown, school detail page, SEO metadata, search results, etc.) — display-time normalisation would need each of those to know about and call the helper. Easy to forget; easy to drift. Storage normalisation costs one migration but eliminates the per-component dependency entirely. The W.P. abbreviation is a stable canonical form for Malaysia (used by MOE, KKM, JKR, every Malaysian government dept) so this is unlikely to need re-normalisation later. Trade-off accepted: storage encodes display style, but the W.P. style is so well-established that the coupling is low-risk.

**Trade-offs:** Lose the MOE-canonical Malay form in storage. A future audit asking "what was the raw MOE state name?" needs to reverse-map via `_STATE_DISPLAY`. The migration's `reverse_code` does this if the migration is ever rolled back. Not reversible if someone hand-edits the migration to delete the mapping.

**Revisit if:** MOE introduces a new federal territory (would need a new mapping row), or a stakeholder wants the full Malay form somewhere (would need a per-surface helper that maps back — defeating the simplicity gain).

## News matcher cluster ranking: hybrid score, not Gemini judgement — Sprint 24, 2026-06-25

**Decision:** Rank topic clusters in the monthly digest by `score = (article_count × 2) + max_relevance + severity_bonus` where `severity_bonus = NEGATIVE:2 / POSITIVE:1 / NEUTRAL:0`. Take the top N (currently 10) as story cards; everything else rolls into a "Plus N other articles" footer.

**Alternatives considered:**
1. `article_count` DESC only — cheapest and most deterministic, but ignores high-impact single-source stories.
2. Hybrid code-level scoring (chosen).
3. Gemini-driven top-N selection — second pass asking "of these N clusters, which 10 matter most?". Editorially smarter but ~$0.001 extra per render, non-deterministic, harder to test.

**Rationale:** A single negative story with `relevance=5` shouldn't lose to a 4-article positive cluster with `relevance=3`. The hybrid formula gives the count signal a strong base (Dengkil's 4 articles × 2 = 8) while letting `max_relevance` (1-5) and severity bonus (0-2) provide editorial tie-breaks. Deterministic across runs — same input always produces same ranking, which matters for testing and for the user's "is this clustering consistent?" intuition. Cheap (pure Python; no extra API call). Easy to tune: weights are constants in `_score_cluster`.

**Trade-offs:** A novel single-article story (high relevance, high severity) competes well but doesn't dominate. Example: a positive 4-article cluster (`4×2 + 5 + 1 = 14`) outranks a negative 1-article cluster (`1×2 + 5 + 2 = 9`). Acceptable — multi-source coverage is generally a signal of editorial importance and a single source can still surface via the footer link. Less acceptable for breaking-news contexts where coverage hasn't propagated yet; the urgent-alerts system (Sprint 25 next) handles that case separately.

**Revisit if:** the editorial team wants a different weighting (e.g. all-negative-news edition), or if the article-count signal degrades because Google Alerts starts surfacing more duplicate-source coverage. Both are easy tunes; the formula is a single Python expression in `_score_cluster`.

## News matcher Strategy 1.5: read SchoolAlias before exhausting in-table strategies — Sprint 24, 2026-06-26

**Decision:** `_resolve_school_codes` now consults the `SchoolAlias` table as Strategy 1.5 — after exact `short_name` match (Strategy 1) and before all variant-generation strategies. Single IN-query against normalised forms of `{original name, distinctive part, every variant from _generate_name_variants, each prefixed with "SJK(T) "}` — one DB round-trip covers ~10 lookup strings.

**Alternatives considered:**
1. Add alias lookup as Strategy 7 (last resort) — wrong order; lets in-table fuzzies override curated aliases.
2. Add as Strategy 0 (before exact short_name) — same DB cost but skips the cheap in-memory exact match for no reason.
3. Strategy 1.5 (chosen) — between exact short_name and variant generation. Curated aliases get priority over fuzzy variants but don't pre-empt the cheap exact case.
4. Drop the in-table strategies entirely and rely on aliases for everything — would require seeding aliases for every possible spelling at import time. Brittle; doesn't gracefully handle Gemini's novel name forms.

**Rationale:** The alias table is the only place where curated, human-reviewed name variants live. Putting it before variant generation means a Hansard-found "Jenderata" alias resolves correctly even if the variant generator would have eventually found the canonical "Jendarata" via fuzzy match — the curated mapping is more trustworthy than fuzzy. Putting it after Strategy 1 (exact short_name) preserves the zero-cost path for the common case where Gemini returns the canonical name. The single IN-query is essentially free (~1ms) so adding it doesn't bloat the per-article cost.

**Trade-offs:** Adds a hansard-app dependency to newswatch (`from hansard.models import SchoolAlias`). Acceptable: SchoolAlias is the canonical alias table for the whole project, not a hansard-internal concept. Future refactor: move SchoolAlias to `schools/models.py` (cross-cutting), then both newswatch and hansard import from schools. Not done in Sprint 24 because the model already exists with a lot of historical migrations rooted in the hansard app; moving it is a separate refactor.

**Revisit if:** the SchoolAlias table grows large enough that the IN-query becomes slow (>10ms per article), at which point switch to a single PK lookup with normalised text as the secondary index. Currently ~1,500 rows; IN-queries are fine at this scale.

## Test sends bypass the Brevo daily-quota gate — Sprint 25, 2026-06-26

**Decision:** `send_test(broadcast_id, recipient_emails)` does NOT consult `brevo_quota.get_quota()` before sending. It calls Brevo directly per recipient, with the per-email 0.5s rate-limit, and lets Brevo's own 429 response (if quota is actually exhausted) surface as a failed count. The admin UI further caps test sends at 5 recipients per submission.

**Alternatives considered:**
1. Apply the same `_quota_allowance` gate as real sends — semantically consistent, but blocks a 2-email sanity check the moment the day's 300-recipient blast has used the quota. The admin then can't verify their next draft.
2. Reserve N slots per day for test sends — adds a separate counter to track + reset; the complexity dwarfs the actual gain.
3. Per-admin-user quota — premature; we have one admin in practice.
4. Bypass the gate, cap at 5 per submission (chosen) — test sends are bounded by the UI; the worst case is one admin spamming themselves, which Brevo's own per-second limits would catch anyway.

**Rationale:** The quota gate exists to keep a bulk send from going over the daily cap; test sends are intrinsically small. Letting test sends through doesn't materially change the day's total. The 5-recipient cap discourages "send to the whole team" as a substitute for the real broadcast, which would corrupt the audit trail (recipients don't get a Broadcast row for a test send). The cap is at the admin UI layer, not the service layer — because the management-command path is for ops who might legitimately want to test on 10 inboxes in a one-off backfill scenario, and forcing the cap there would be more annoying than safe.

**Trade-offs:** A pathological admin could test-send 100 times in a day and consume a measurable chunk of quota. Mitigated by the 5-cap on the UI + the per-email 0.5s sleep (so 100 test sends = 50 seconds, visibly slow). We accept this over the alternative of "an admin can't verify a draft because the day's blast already happened."

**Revisit if:** test-send volume becomes meaningful relative to bulk-send volume (rough threshold: >10% of day's quota), at which point a daily-per-admin counter would help.

## `URGENT_ALERT_REQUIRE_REVIEW` default flips in code, not via Cloud Run env var — Sprint 25, 2026-06-26

**Decision:** Change the default literal in `backend/sjktconnect/settings/base.py` from `"false"` to `"true"`. Do NOT only set the env var on `sjktconnect-urgent-alerts` Cloud Run job.

**Alternatives considered:**
1. Set `URGENT_ALERT_REQUIRE_REVIEW=true` via `gcloud run jobs update --update-env-vars` — zero code change, can be reverted in seconds.
2. Change the code default + keep the env var as an explicit override (chosen) — the in-code default survives every deploy; env var still works for emergency rollback.
3. Hard-code the behaviour (remove the flag entirely) — removes the safety net for cases where auto-send is genuinely desired.

**Rationale:** Env-var-only defaults drift silently — `gcloud run deploy --source .` has been observed to drop env vars set via `--update-env-vars`, and a subsequent operator has no way to know the "default" should have been overridden. The code-level default codifies the intended permanent behaviour while preserving the env var as a documented escape hatch. This matches the pattern we use for other safety-critical defaults (e.g. `DEBUG`, `ALLOWED_HOSTS`).

**Trade-offs:** Rollback requires either a code revert + redeploy OR setting `URGENT_ALERT_REQUIRE_REVIEW=false` env var on the job. Slightly more friction than a one-line env-var flip; the tradeoff is "code-level defaults can't drift silently."

**Revisit if:** Auto-send becomes the desired behaviour for a specific operational mode (drill, load test, regression test). At that point the env-var override is the right tool — no code change needed.

## `tel:` link strategy: split on multi-number separators, preserve visual chars — Sprint 26, 2026-06-26

**Decision:** `firstPhoneForTelUri(raw)` splits multi-number values on `/`, `,`, or `;`, trims whitespace, and returns the first segment AS-IS — including dashes and spaces. It does NOT strip non-digits.

**Alternatives considered:**
1. **Aggressive strip** — `raw.replace(/[^\d+]/g, "")` — produces canonical `+60326017222` form. Maximally portable, but the value shown on tap (`+60326017222`) no longer matches the displayed label (`03-2601 7222`).
2. **Reject multi-number entirely** — display "Invalid phone" instead of the first number. Surfaces the data quality issue, but breaks user flow for what's actually a usable number.
3. **Take the first number, preserve visual separators (chosen)** — RFC 3966 allows `-` and space as visual separators; every modern dialer parses them; the value-on-tap matches the value-shown.

**Rationale:** Phone display is one of those rare cases where visual formatting carries information ("you're calling a Selangor landline"). Stripping it for tel: gets the user to the right call but changes the value visible in the dialer history, which causes a "did I type that right?" double-take. The RFC compatibility means we don't trade portability for the visual preservation.

**Trade-offs:** A dialer that doesn't follow RFC 3966 strictly could fail on the visual chars. None of the major mobile dialers (iOS, Android) have this problem; legacy desktop dialers (which mostly don't exist on phones-of-record anymore) might.

**Revisit if:** A user reports that a specific dialer refuses to call the formatted number. At that point the right answer is probably to strip on a per-dialer-detected basis, but we'd revisit per-data first.

## Frontend + backend validation for the same constraint always ship together — Sprint 26, 2026-06-26

**Decision:** Every input constraint added in Sprint 26 (phone shape, email shape, session_type enum) ships with BOTH a frontend rule (inline error in the React form) AND a backend rule (`serializer.validate_<field>`). Neither layer is sufficient alone.

**Alternatives considered:**
1. **Backend-only** — frontend just lets the user type anything; on Save the API responds with 400 + field errors and the form renders them. Smallest code surface. Cost: opaque UX (user types invalid data for 30 seconds, hits Save, sees a red toast).
2. **Frontend-only** — inline validation prevents Save when invalid. Cost: `curl` users + browser console hackers can write any garbage. The point of validation is the trust boundary, which lives at the API.
3. **Both layers, paired in the same commit (chosen)** — frontend gives immediate feedback, backend guarantees the rule. The pair is the right shape; either alone is a missing-half.
4. **Shared schema via JSON Schema / OpenAPI** — generate both layers from one source. Right answer for a much larger codebase. Overkill for our scale.

**Rationale:** Inline frontend errors save a round-trip and let the user correct mistakes immediately — that's UX. Server-side validation refuses bad data even when the frontend is bypassed — that's the trust boundary. The two concerns are orthogonal; covering only one is incomplete. The cost of duplicating regex constants between `frontend/lib/validation.ts` and `serializers.py` is low — the regex is 10 chars long and changes once a decade.

**Trade-offs:** Regex drift risk between frontend + backend (a fix in one place doesn't propagate to the other). Mitigated by the test suite — both layers have tests asserting the same canonical bad inputs are rejected. If the regex grows past ~30 chars or starts using lookahead, the case for shared-schema generation gets stronger.

**Revisit if:** We add 3+ more validation rules (then the duplication becomes annoying and a shared-schema tool earns its complexity), OR if a regex drift causes a real bug.

## Scrape-time + display-time guards for bad data (two-layer fix) — Sprint 26, 2026-06-26

**Decision:** When fixing bad data sourced from a scraper (Sprint 26 #5, the generic ParlimenMY Facebook URLs), patch the scraper to stop writing the bad shape going forward AND patch the frontend to hide existing bad rows in the database.

**Alternatives considered:**
1. **Scraper-only fix + run a one-off cleanup** — fix the scraper, then run a Django shell command to clear existing `MP.facebook_url` rows matching the generic pattern. Cost: requires a destructive one-off operation on prod data; if the cleanup runs before the scraper fix lands, the next scrape re-adds the bad rows.
2. **Display-only fix** — frontend hides the bad URLs. Cost: the next scrape still adds new bad rows; the DB has stale data forever; downstream consumers (CSV export, analytics) still see them.
3. **Both (chosen)** — scraper drops at write time so future runs are clean; frontend hides existing rows so users don't see them. The pair lets us defer the SQL cleanup indefinitely with no user-visible impact.
4. **DB constraint** (`CHECK (facebook_url NOT IN (...))`) — over-engineered for a value-list of 4 generic slugs. Hard to test, hard to revoke.

**Rationale:** The two layers cover different time windows. The scraper guard protects future state; the frontend guard protects current state. Together they decouple "fix the bug now" from "clean up the existing bad rows" — the cleanup becomes optional ops work, not a release blocker. This pattern generalises to any scraper-sourced data quality bug.

**Trade-offs:** The DB still carries stale bad rows. A future data-consumer that bypasses the frontend (e.g. a CSV export) would see them. Mitigated by documenting the pattern + running the SQL cleanup whenever convenient (we have a TODO carry-over for it in retro). If we ever add a CSV export, that's the trigger to schedule the cleanup before shipping.

**Revisit if:** We add a non-frontend consumer of `MP.facebook_url` (CSV export, analytics dashboard, public API endpoint).

## ISR + explicit revalidation, not "drop ISR" or "shrink revalidate" — Sprint 27, 2026-06-26

**Decision:** Keep `revalidate=86400` on the public school page AND add a `/api/revalidate` route handler that the edit flow calls after a successful save. Three layers: edge cache (Cloudflare) + Next ISR (24h) + explicit invalidation on edit.

**Alternatives considered:**
1. **Drop ISR on the school page** (`revalidate=0` or `dynamic="force-dynamic"`) — guarantees freshness but kills the egress optimisation Sprint 17/21 worked hard to land. School pages get 1000s of bot hits a day; rebuilding per-hit is wasteful when the data changes maybe once a month per school.
2. **Shrink revalidate to 60s** — still stale by up to 60s after an edit, AND wastes most of the cache benefit. Worst of both worlds.
3. **Both ISR (24h) and explicit revalidate on edit (chosen)** — Next.js idiomatic pattern. Cache benefit retained for the 99% of traffic that's read-only; freshness guaranteed for the 1% that's edit-driven.
4. **Server-Sent Events / WebSocket signal** — way over-engineered for a page that updates from "any admin saves" → "1 user looking at the freshly-saved version."

**Rationale:** ISR's whole reason for existing is "cache aggressively, invalidate explicitly when you know data changed." We knew. We just hadn't wired the invalidation. The cost is one route handler (~40 lines) + 6 lines of client code (revalidate + push). The benefit is the edit flow finally feels responsive — the user lands on the public page with their change reflected, instead of seeing stale data and wondering if Save worked.

**Trade-offs:** The route handler is unauthenticated (we'd otherwise have to pass cookies through from a client component, which is fragile). Worst-case abuse is "a malicious caller invalidates the cache for a specific moe_code" — same impact as a normal ISR miss, so essentially zero damage. We further restrict the route's path-building so only `/(en|ta|ms)/school/<UPPERCASE_KEY>` paths can be revalidated, never arbitrary paths.

**Revisit if:** We add other ISR-cached pages that also need explicit invalidation (constituency, DUN, news article pages). At that point the `{type, key}` shape extends naturally — add a switch case per type. If the count grows past ~5 types, consider a per-type route handler or a typed RPC instead.

## School URL slug: `<name>-<city>-<moe>`, name first, moe at end — Sprint 28, 2026-06-26

**Decision:** School URLs are `/school/<name-slug>-<city-slug>-<moe-code>` (e.g. `subramaniya-barathee-gelugor-pbd1088`). Page handler accepts both the slug AND the legacy bare-code form; non-canonical visits 301 to the canonical. Sitemap, JSON-LD `@id`/`url`, `<link rel=canonical>` all emit the slug form.

**Alternatives considered:**
1. **Bare moe-code only** (status quo before Sprint 28) — URL has zero keyword density, ranks behind any site that puts the school name in the URL (apac.com.my SERP position #3 vs ours at #7).
2. **`<moe>-<name>-<city>` (moe first)** — moe-code at start makes parsing trivial, but loses SEO benefit. Google weights early-path words more.
3. **`<name>` only (no moe)** — best SEO BUT names collide ("Ladang Bikam" exists in multiple states). Requires a slug-collision resolver (DB unique constraint + suffix-N suffixes). Brittle.
4. **`<name>-<city>-<moe>` (chosen)** — keyword density at the start, city adds local relevance, moe at the end is the lookup primary key.

**Rationale:** apac.com.my outranks us at #3 vs our #7 mainly because their URL is `/pbd1088/SJK%20T%20SUBRAMANIYA%20BARATHEE,%20GELUGOR.html` — the school name is in the URL. For a query like "sjkt subramaniya barathee", the URL alone matches half the query words before Google even reads our title. Sprint 22's labelled-meta-description gave us competitive snippet quality but couldn't close the URL-relevance gap. The slug shape mirrors what every well-ranking directory site does (Wikipedia, GitHub, Stripe). Keeping the moe-code at the end gives us an exact-match parse-back regex (`/^.+-([a-z]{3,4}\d{3,4})$/`) and prevents collisions without a DB constraint.

**Trade-offs:**
- Existing inbound links to `/school/PBD1088` keep working (legacy form accepted) but route through a 301 to the slug. Mild SEO cost for the redirect chain; Google handles 301 redirects well.
- When a school's `short_name` or `city` changes (rare), old slugs in the wild become stale — they still 301 to the new canonical, no broken links.
- Sitemap regenerates ~528 URLs once; Google re-crawls and the old canonicals fade from the index over 2-4 weeks.
- Internal links that don't pass full school context (admin pages with just `moe_code`) emit bare-code and rely on the 301. One extra redirect per click; acceptable for non-public surfaces.

**Revisit if:** Google penalises us for excessive 301 redirects in the link graph (unlikely; 301s are first-class), OR if a school's slug collides somehow despite the moe suffix (impossible by design — moe-code is unique).

## `Bhg ⇔ Bahagian ⇔ Division` bridge in seed_aliases, not as per-school migrations — Sprint 28, 2026-06-26

**Decision:** Extend `generate_aliases_for_school` to detect `\b(Bhg|Bahagian|Division)\s+<number>\b` in any school's name and emit two synonym variants. Re-running `seed_aliases` materialises the new aliases for every affected school automatically.

**Alternatives considered:**
1. **Per-school migration** (Sprint 27's `hansard/0010` approach) — explicit, reviewable, but requires a new migration for every newly-imported school that contains these tokens. Manual maintenance burden.
2. **Generic Strategy 5 patch** (my initial Sprint 27.5 proposal) — extend `_GENERIC_WORDS` to include "bahagian", "division" so Strategy 5 stops falsely matching them. Works as a fallback but doesn't help the alias lookup find the right school; just makes the failure mode "no match" instead of "wrong match".
3. **Both 1 and 3 (chosen for Sprint 28)**: extend the alias generator (the proper layer per owner instinct) AND keep the Sprint 27 migration as belt-and-braces. Either alone would work; both together is defence-in-depth.

**Rationale:** Owner correctly diagnosed that aliasing is the proper mechanism — articles use journalists' spelling, our aliases should bridge to MOE's canonical spelling. The variant bridge belongs in the generator because: (a) it covers every future school automatically, (b) it's one block of code instead of one migration per school, (c) re-running `seed_aliases` after a schools-table import refreshes everything. Strategy 5 stays as a fallback for cases the generator can't anticipate (e.g. typos, transliteration drift).

**Trade-offs:** Re-running `seed_aliases` regenerates COMMON-type aliases (it preserves HANSARD-type) — fine because COMMON aliases are derivable from school data. Adds 1-2 aliases per affected school; current DB has ~1,500 aliases, this brings it to ~1,510. Negligible storage/lookup cost.

**Revisit if:** New token-pair drift emerges (e.g. "Estate" vs "Ladang", "Section" vs "Bahagian" — though we already handle Section via state distribution). At that point extend the bridge logic — same pattern.

## MY-specific phone validation (digit-count), not generic shape regex — Sprint 28, 2026-06-26

**Decision:** `isValidPhone()` enforces Malaysian phone-number digit-count rules (mobile 10-11 digits with `01X` prefix; landline 9-10 digits with `0[2-9]` prefix; `+60` international form normalised to local). The shape-regex (`[\d+\-\s()]{6,20}`) stays as a fast pre-filter but is no longer the validation primary.

**Alternatives considered:**
1. **Pure shape regex** (Sprint 26 status quo) — easy to write, passes truncated numbers.
2. **Full MCMC carrier-prefix lookup** — checks not just digit count but that "012" is a known TM mobile prefix etc. Overkill at our scale; new carriers/prefixes would require code changes.
3. **`libphonenumber` library** — Google's canonical phone-number validation. ~150 KB to the bundle, validates every country in the world. Overkill for a MY-only app where the rules are 4 lines of code.
4. **Domain-specific digit-count rule** (chosen) — encodes the MCMC spec without dragging in a library. Fast, deterministic, 5 lines of code.

**Rationale:** The bug was "truncated numbers passed" — solvable by counting digits after normalisation. MY phone numbers have a stable, well-known structure: mobile starts `01X` and has 10-11 digits; landline starts `0[2-9]` and has 9-10 digits; international form prepends `+60` and drops the leading 0. Encoding this directly is more honest about what we're checking than pulling in a generic library.

**Trade-offs:** New MY area codes or carrier prefixes would require a code change. Last MCMC change to MY mobile prefix structure was ~2010 (introduction of 011 prefix); the rate of change doesn't justify defensive abstraction. International numbers other than +60 are rejected — fine; this is a MY-only product.

**Revisit if:** We need to accept Singapore/Indonesia/Thai phones (would require a real library or per-country lookup), or if MCMC introduces new prefix shapes.
