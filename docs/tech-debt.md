# SJK(T) Connect — Tech Debt Register

*Living document. Triaged each sprint. First populated 2026-04-22 after full-codebase audit (item 12 in CLAUDE.md pending list).*

Each entry: **what** / **why we accepted the debt** / **what it blocks** / **cost to fix**.

Severity scale: 🔴 high · 🟡 medium · 🟢 low.

---

## 🔴 TD-01 — OAuth security checks disabled in production (RE-OPENED 2026-04-24)

- **Status**: **REGRESSED** in Sprint 12. Had been resolved in Sprint 11a Phase 2 (Cloudflare + same-site cookies + `checks: ["pkce", "state"]`). During Sprint 12 smoke-test, sign-in started failing with `[auth][error] InvalidCheck: state value could not be parsed`. Reverted to `checks: []` in `frontend/lib/auth.ts` as pragmatic unblock; sign-in works again.
- **Root cause (hypothesised, not confirmed)**: Next 16 + Auth.js v5 beta.30 + `@auth/core@0.41.0` combination breaks the state/PKCE cookie round-trip — cookie is set before Google redirect but is unparseable on callback. Did not regress immediately after Next 16 upgrade (sign-in worked), only after Sprint 12 deploy — so something specific changed between Sprint 11a Phase 4 deploy and Sprint 12 deploy (possibly a transitive dep during `npm ci` in Dockerfile build, though lockfile hasn't changed).
- **Debug attempts (all failed to fix)**: (a) Added `AUTH_SECRET`/`AUTH_URL` env vars alongside legacy `NEXTAUTH_*`. (b) Removed `NEXTAUTH_*` entirely, keeping only v5-native `AUTH_*`. State cookie still unparseable.
- **What it blocks**: Safely shipping community-facing features. OAuth flow lacks PKCE + state protection against CSRF on callback and authorization-code interception.
- **Cost to fix**: ~2–4 hours. Sprint 16 investigation path: (1) bump `next-auth` past beta.30 — check if beta.32+ or stable 5.x exists, (2) try explicit cookie config with `cookies: { state: { options: { ... } } }` in auth.ts, (3) check `__Host-` cookie prefix compat with Cloudflare, (4) add DevTools cookie trace during sign-in flow to see which cookie is missing/corrupted, (5) worst case: downgrade Next to 15 to bisect.

## ✅ TD-02 — Magic-link removed, auto-claim on @moe.edu.my (RESOLVED 2026-04-24)

- **Status**: Resolved in Sprint 11a Phase 3. `_maybe_auto_claim()` helper added to `GoogleAuthView`: when sign-in email ends with `@moe.edu.my`, extract moe_code part, look up School, bind `profile.admin_school`, set `school.claimed_at`. Idempotent + protected against overwriting existing claims. Deleted: `SchoolContact` + `MagicLinkToken` models (migration `accounts/0003`), `IsMagicLinkAuthenticated`, `accounts/services/token.py`, `accounts/services/email.py`, magic-link views + URLs + serializers, `/claim/` pages, `ClaimButton` + `ClaimForm` components, all magic-link tests. `SchoolEditView` + `SchoolConfirmView` migrated to `IsProfileAuthenticated` + `admin_school` check (SUPERADMIN bypass). New inline `EmailClaimIndicator` component — Google-style UX: "Claim this page" link or ✓ Verified pill next to the email field. Edge case: SUPERADMIN sets `admin_school` manually via Django admin if HM has lost password.

## ✅ TD-03 — `DATABASE_URL` in `.env` silently hijacks local tests (RESOLVED 2026-04-23)

- **Status**: Resolved. `backend/manage.py` now prints a warning banner on every invocation when `DATABASE_URL` points to a non-local host, and refuses to run a hardcoded list of destructive commands (`migrate`, `flush`, `import_*`, `seed_*`, `harvest_school_images`, etc.) without `SJKTCONNECT_ALLOW_PROD_DB=1`. Read-only commands (`shell`, `test`, `check`) proceed unchanged. `pytest` still needs `DATABASE_URL=` unset for a pure sqlite run — that's now documented behaviour rather than a silent trap.

## ✅ TD-04 — `SESSION_COOKIE_SAMESITE = "None"` workaround (RESOLVED 2026-04-24)

- **Status**: Resolved in Sprint 11 Phase 2. Cloudflare proxy put frontend + backend on same registrable domain (both subdomains of `tamilschool.org`); default `SameSite=Lax` now handles cross-subdomain cookie delivery correctly. Removed `SESSION_COOKIE_SAMESITE = "None"` and `CSRF_COOKIE_SAMESITE = "None"` from `production.py`. Full CSRF protection restored via `SameSite=Lax` default. The DRF `SessionAuthentication` pin (TD-08) from 2026-04-23 remains as defense-in-depth.

## ✅ TD-05 — School images stored as volatile Google Places URLs (RESOLVED 2026-04-26)

- **Status**: Resolved in Sprint 13. `SchoolImage.image_file` (ImageField → Supabase Storage `school-images` bucket via S3-compat `django-storages`) added. `display_url` property prefers `image_file.url`, falls back to legacy `image_url`. Harvester rewritten to download bytes server-side and persist via `image_file.save()`. Production migration: 1009 PLACES + 528 SATELLITE re-harvested + 1 COMMUNITY migrated; **1534/1534 (100%) on Supabase Storage**. Broken-images sitewide issue is gone — verified on tamilschool.org school pages and map InfoWindow.

## ✅ TD-06 — Supabase egress regression (PROVISIONALLY RESOLVED 2026-04-26 — monitor for 1 week)

- **Status**: Almost certainly resolved by Sprint 13 (TD-05 fix). Hypothesised root cause was Next.js image-optimiser retrying on dead Google Places URLs — those URLs are now gone. Hero images now served from `kafuxsinrbqafvarckxu.storage.supabase.co` (Supabase Storage CDN), bypassing our backend entirely.
- **Verification plan**: Monitor Supabase egress dashboard for 7 days post-2026-04-26; flip from "PROVISIONALLY RESOLVED" to ✅ definitively resolved after one full week shows <100 MB/day. Listed in CLAUDE.md "Small passive items" for Sprint 14 close.

## 🟡 TD-07 — `Suggestion.image` stored in Postgres `BinaryField`

- **What**: `backend/community/models.py:41` — community photo uploads stored as base64-decoded bytes inside a Postgres `BinaryField`, served back by Django. A 3 MB phone photo becomes a ~4 MB Postgres row. DRF's default `DATA_UPLOAD_MAX_MEMORY_SIZE` (2.5 MB) caps larger uploads with 413 errors.
- **Why we accepted**: Sprint 8.2 prioritised shipping the moderation workflow quickly; storage architecture was deferred.
- **What it blocks**: Upload size cap is absurdly low for modern phone photos (typically 5-15 MB). Ingest from real community users would regularly fail. Also makes backups + replication heavier than needed.
- **Cost to fix**: Replaced by Supabase Storage in Sprint 9 (TD-05).

## ✅ TD-08 — No `DEFAULT_AUTHENTICATION_CLASSES` pinned (RESOLVED 2026-04-23)

- **Status**: Resolved. `REST_FRAMEWORK["DEFAULT_AUTHENTICATION_CLASSES"]` in `backend/sjktconnect/settings/base.py` is now pinned to `["rest_framework.authentication.SessionAuthentication"]` with a prominent comment warning against adding `TokenAuthentication` without CSRF compensating controls. This locks in the hidden dependency that TD-04's security posture relies on.

## 🟡 TD-09 — Hardcoded `content_type="image/png"` on suggestion image endpoint

- **What**: `backend/community/api/views.py:130` serves arbitrary uploaded bytes with `content_type="image/png"` regardless of actual format. No magic-byte validation, no Pillow verification on upload.
- **Why we accepted**: MVP shortcut in Sprint 8.2. Unlikely to be exploited at current 1-user scale.
- **What it blocks**: Minor — browsers don't execute scripts inside `<img>` regardless of declared format, so stored XSS is not exploitable. But opens the door to content-type confusion if a future endpoint serves SVG or raw.
- **Cost to fix**: Replaced entirely by Sprint 9 (TD-05) which validates format, strips EXIF, resizes, and stores in typed Supabase Storage.

## 🟢 TD-10 — Next.js upgrade (mostly resolved 2026-04-24)

- **Status (2026-04-23)**: `next-intl` 4.8.3 → 4.9.1+, cleared open-redirect.
- **Status (2026-04-24)**: `next` 14.2.x → **16.2.4** in Sprint 11a Phase 4 (skipped 15 entirely; @latest is 16). The flagged Image Optimizer DoS CVE (GHSA-9g9p-9gw9-jx7f) is cleared. Migration covered: 5 app-router pages updated to async `params` API (`layout.tsx`, `school/[moe_code]`, `constituency/[code]`, `dun/[id]`, plus their `generateMetadata`). Added `frontend/global.d.ts` shim because Next 16's auto-generated `.next/types/validator.ts` references `React.ComponentType` unqualified but `jsx: "react-jsx"` doesn't expose React in global scope. Kept `ignoreBuildErrors: true` (with clearer comment) because pre-existing implicit-any issues in `BoundaryMap` etc. are out of scope for an upgrade sprint.
- **Residual**: 2 transitive deps still flagged by `npm audit` — `brace-expansion` (moderate), `picomatch` (high). Both transitive; will resolve when their parents update. Not exploitable in our usage.
- **Cost to fully clear residual**: 1-2 hours when transitive deps publish patches; mostly waiting.

## 🟢 TD-11 — `accounts/services/google.py` at 25% coverage

- **What**: Google ID token verification has 25% line coverage (most exceptions paths and failure branches unexercised).
- **Why we accepted**: Painful to mock Google's `verify_oauth2_token`. The happy path is covered.
- **What it blocks**: Confidence in edge cases — e.g. what happens if `aud` mismatches unexpectedly? Actual code looks correct, but without tests we'd miss a regression.
- **Cost to fix**: 1 hour. Add tests that mock `id_token.verify_oauth2_token` returning bad issuer, bad audience, expired token, exception.

## 🟢 TD-12 — `hansard/pipeline/extractor.py` at 26% coverage

- **What**: PDF text extraction path has 26% coverage.
- **Why we accepted**: Hard to test without fixture PDFs; current integration tests cover only the easy branch.
- **What it blocks**: Regressions in edge-case PDFs (encrypted, image-only, malformed) would surface only in production.
- **Cost to fix**: 2-3 hours. Add a small fixtures directory with 3-4 edge-case PDFs and matching assertion cases.

## ✅ TD-13 — `uploaded_by` on `SchoolImage` never set by harvester (RESOLVED 2026-04-26)

- **Status**: Resolved as a no-op in Sprint 13. Confirmed semantically correct — harvester images weren't uploaded by any user, so NULL is the right value. Documented in `outreach/services/image_harvester.py` docstring + `SchoolImage.uploaded_by` field help_text. No code change required; closing for clarity.

## 🟢 TD-14 — Inconsistent `role` checks across views

- **What**: Several views duplicate role checks inline, e.g. `if profile.role not in ("MODERATOR", "SUPERADMIN"): ...` appears at least 5 times across `community/api/views.py`. The `IsModeratorOrAbove` permission class already expresses this.
- **Why we accepted**: Per-view checks grew organically. Consolidation wasn't prioritised.
- **What it blocks**: Nothing functional. But it's a place where adding a new role (e.g. `SCHOOL_ADMIN`) requires changes in many places.
- **Cost to fix**: 1-2 hours. Refactor views to use `@permission_classes([IsProfileAuthenticated, IsModeratorOrAbove])` where appropriate.

## 🟢 TD-15 — 2 pre-existing flaky frontend tests

- **What**: `SubscribeForm.test.tsx` (calls subscribe with all fields) and `SchoolEditForm.test.tsx` (confirms data on button click) fail intermittently during `npm test`. Other 288 tests pass consistently.
- **Why we accepted**: Flaky, not known-wrong. Not a blocker.
- **What it blocks**: CI signal quality (once CI exists — currently no `.github/workflows/`).
- **Cost to fix**: 1 hour. Diagnose — likely async `waitFor` timeout tuning.

## 🟡 TD-16 — Frontend dashboard pages render for signed-out users

- **What**: `/dashboard/users` (and likely sibling dashboard pages — `/dashboard/suggestions`, `/dashboard/images`) render the full UI to signed-out users. Root cause: `useEffect(() => fetchMe().then(me => !me && router.push("/")))` in `frontend/app/[locale]/dashboard/users/page.tsx:49-63` has no `.catch()`. If `fetchMe()` throws on 401 (no session), the redirect never fires and the page falls through to render whatever stale state is in `users[]`. Verified on prod 2026-04-26: signed-out tab on `tamilschool.org/en/dashboard/users` shows the full user table with Role/School/Deactivate buttons.
- **Why we accepted**: Discovered post-Sprint-12 close. **Backend is correctly gated** — `AdminUserListView` has `IsSuperAdmin` permission, so no data leaks and every PATCH/DELETE returns 403. Bug is UX/security-cosmetic (signed-out users see admin chrome but cannot mutate anything).
- **What it blocks**: Trust signal — non-technical observers will think the platform is insecure even though backend permissions hold. Also masks the SUPERADMIN-only nature of the page from school admins, who might assume they can see the same UI.
- **Cost to fix**: 30 min. Add `.catch(() => router.push("/"))` to every `fetchMe()` call inside dashboard pages, render `null` (not the page chrome) until `currentProfileId !== null`. Also verify school-admin-scoped pages gate by role correctly, not just by truthy session. **Sprint 14 will apply the fix to `/dashboard/suggestions` as part of its photo-approval UI work** (in-scope file). The `/dashboard/users` and `/dashboard/images` fixes belong in **Sprint 16** (Code-Quality Pass).

---

## Triage for next sprints

| Fix | Debt items | Sprint |
|---|---|---|
| ✅ Pin DRF auth classes | TD-08 | Done 2026-04-23 |
| ✅ Local-dev DATABASE_URL guard | TD-03 | Done 2026-04-23 |
| ✅ Cloudflare proxy + restore OAuth checks | TD-01, TD-04 | Done 2026-04-24 (Sprint 11a Phases 1+2) |
| ✅ Delete magic-link + auto-claim + EmailClaimIndicator | TD-02 | Done 2026-04-24 (Sprint 11a Phase 3) |
| ✅ Next 14 → 16 upgrade | TD-10 | Done 2026-04-24 (Sprint 11a Phase 4); residual cleared in Sprint 16 |
| ✅ Sprint 12 — User Management UI | — | Done 2026-04-24 |
| ✅ Sprint 13 — Image Storage Migration | TD-05 ✅, TD-06 (provisional) ✅, TD-13 ✅ | Done 2026-04-26 |
| 🔴 TD-01 re-opened (Next 16 + Auth.js state cookie regression) | TD-01 | Investigation in Sprint 16 |
| Sprint 14 — Community Photo Uploads | TD-07, TD-09, TD-16 (suggestions page only) | Next |
| Sprint 15 — Image Display Polish | — | After Sprint 14 |
| Sprint 16 — Code-Quality Pass | TD-01 (re-opened), TD-10 residual, TD-11, TD-12, TD-14, TD-15, TD-16 (users + images pages) | Last of 5-sprint roadmap |
