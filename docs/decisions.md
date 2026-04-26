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

## TD-11 + TD-12 (test-coverage padding) deferred indefinitely — Sprint 16, 2026-04-27

**Decision:** TD-11 (`accounts/services/google.py` 25% coverage) and TD-12 (`hansard/pipeline/extractor.py` 26% coverage) are marked deferred — no scheduled sprint. They'll be picked up if and when the underlying code changes or starts producing bugs.

**Alternatives considered:**
1. **Sprint 17 dedicated to test-coverage** — would honour the "every TD eventually closes" pattern but adds a sprint of low-leverage work for coverage on stable, well-exercised paths.
2. **Roll into Sprint 16 (chosen at sprint-start)** — would have stretched a Code-Quality Pass into a Test-Coverage Pass too. Different in flavour; would have lost focus.
3. **Defer indefinitely (final choice at close)** — the code in question (Google ID token verification, PDF extraction) hasn't changed in 8 sprints and hasn't produced a single bug since the modules were written. Coverage as a number doesn't mean these paths are correct; it means certain branches aren't exercised by tests. Adding tests now costs time without reducing real risk.

**Rationale:** Test coverage is a means, not an end. The 25% and 26% numbers come from large try/except branches and dead-code-via-environment paths (e.g. SQLite vs Postgres) that are intentionally untested in the local suite — they'd require fixture proliferation to exercise. The actual user-facing flows (sign in works, hansard PDFs extract correctly) are tested via integration / end-to-end paths. Marking these "deferred indefinitely" is more honest than "Sprint 17" if there's no real plan to do them.

**Trade-offs:** If the underlying code ever DOES break in an untested branch, the regression won't be caught by the suite. Acceptable: those branches are well-isolated (Google's verify_oauth2_token error paths; pdfplumber's encrypted-PDF path), and a real failure surfaces visibly on prod before silently corrupting data.

**Revisit if:** Either module starts producing bugs in production, OR a refactor of either module is on the table (in which case adding tests around the change is the right move).
