# SJK(T) Connect — Tech Debt Register

*Living document. Triaged each sprint. First populated 2026-04-22 after full-codebase audit (item 12 in CLAUDE.md pending list).*

Each entry: **what** / **why we accepted the debt** / **what it blocks** / **cost to fix**.

Severity scale: 🔴 high · 🟡 medium · 🟢 low.

---

## ✅ TD-01 — OAuth security checks restored (RESOLVED 2026-04-27, Sprint 16)

- **Status**: Resolved. `checks: ["pkce", "state"]` is back on the Google provider. PKCE + state CSRF protection is enforced on every OAuth callback. User-verified on prod web-00103-phl by `tamiliam` (USER) and `admin` (SUPERADMIN) sign-in cycles.
- **Actual root cause**: `__Host-` cookie prefix on the csrfToken cookie was incompatible with Cloudflare's proxy / Cloud Run header pipeline. The `__Host-` prefix forbids a `Domain` attribute and requires `Path=/` from a secure origin; Cloudflare modifies `Set-Cookie` in ways that violate `__Host-` semantics, silently dropping the cookie at the browser. Auth.js then read back a missing/garbled state value on callback, surfacing as `InvalidCheck: state value could not be parsed`.
- **Fix applied** (Sprint 16): in `frontend/lib/auth.ts`, override `@auth/core`'s default cookie config to use `__Secure-` prefix instead of `__Host-` for csrfToken (the only cookie that defaulted to `__Host-`). Also bumped `next-auth` 5.0.0-beta.30 → beta.31 (pulls in `@auth/core` 0.41.0 → 0.41.2) to stay current with upstream Next 16 support. Restored `checks: ["pkce", "state"]`.
- **Hypotheses falsified**: (a) `@auth/core@0.41` + Turbopack — bumping made no observable difference on its own; (c) bumping past beta.30 — same. Hypothesis (b) `__Host-` + Cloudflare proxy turned out to be the real cause.

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

## ✅ TD-10 — Next.js upgrade (RESOLVED 2026-04-27, Sprint 16)

- **Status (2026-04-23)**: `next-intl` 4.8.3 → 4.9.1+, cleared open-redirect.
- **Status (2026-04-24)**: `next` 14.2.x → **16.2.4** in Sprint 11a Phase 4 (skipped 15 entirely; @latest is 16). The flagged Image Optimizer DoS CVE (GHSA-9g9p-9gw9-jx7f) is cleared. Migration covered: 5 app-router pages updated to async `params` API (`layout.tsx`, `school/[moe_code]`, `constituency/[code]`, `dun/[id]`, plus their `generateMetadata`). Added `frontend/global.d.ts` shim because Next 16's auto-generated `.next/types/validator.ts` references `React.ComponentType` unqualified but `jsx: "react-jsx"` doesn't expose React in global scope. Kept `ignoreBuildErrors: true` (with clearer comment) because pre-existing implicit-any issues in `BoundaryMap` etc. are out of scope for an upgrade sprint.
- **Status (2026-04-27)**: Sprint 16 ran `npm audit fix` (no `--force`); brace-expansion + picomatch + handlebars all bumped at patch level (6 transitive deps moved). Residual cleared.

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

## ✅ TD-14 — Role checks consolidated (RESOLVED 2026-04-27, Sprint 16)

- **Status**: Resolved. Extracted `_can_moderate_or_owns_school(profile, school_id)` helper in `community/api/views.py`. Replaces 4 inline duplications across `pending_suggestions_view` (gate + filter), `approve_suggestion_view`, and `reject_suggestion_view`. Pure refactor; 70 community tests pass. Note: a true permission CLASS refactor wasn't ideal here because the school_id comes from the suggestion object (not the request), so DRF's `has_object_permission` would have needed the suggestion fetched first in the view anyway. Helper function was the right abstraction at this scale.

## ✅ TD-15 — Frontend test flakes deflaked (RESOLVED 2026-04-27, Sprint 16)

- **Status**: Resolved. Investigation found these were never flaky — they were stably broken. `SubscribeForm.test.tsx` was missing the `website: ""` honeypot field added by Sprint 8.6. `EditSchoolLink.test.tsx` and `SuggestButton.test.tsx` (added to the failure list during Sprint 16) didn't mock the `useSession` dependency added by Sprint 15's hotfix. All four fixed; 289/289 frontend tests pass.
- **Lesson** (logged in lessons.md): the Sprint 15 close didn't actually re-run the test suite, so the "285 passing" claim went into MEMORY.md as fact when reality was 282 pass + 3 fail. Sprint-close workflow needs to record actual test output.

## ✅ TD-17 — Brief-generator LLM flake fixed (RESOLVED 2026-04-27, Sprint 16)

- **Status**: Resolved. Class-level `@patch.dict(os.environ, {"GEMINI_API_KEY": ""}, clear=False)` on `GenerateBriefTests` forces the brief generator down the template-fallback path, removing the non-deterministic LLM dependency. The tests verify wiring (title, mention count, HTML containing fixture summaries, social post length); prose-quality tests live elsewhere and mock genai directly. 24/24 brief generator tests pass deterministically.

## ✅ TD-16 — Dashboard signed-out chrome leak fixed (RESOLVED 2026-04-27, Sprint 16)

- **What**: `/dashboard/users` (and likely sibling dashboard pages — `/dashboard/suggestions`, `/dashboard/images`) render the full UI to signed-out users. Root cause: `useEffect(() => fetchMe().then(me => !me && router.push("/")))` in `frontend/app/[locale]/dashboard/users/page.tsx:49-63` has no `.catch()`. If `fetchMe()` throws on 401 (no session), the redirect never fires and the page falls through to render whatever stale state is in `users[]`. Verified on prod 2026-04-26: signed-out tab on `tamilschool.org/en/dashboard/users` shows the full user table with Role/School/Deactivate buttons.
- **Why we accepted**: Discovered post-Sprint-12 close. **Backend is correctly gated** — `AdminUserListView` has `IsSuperAdmin` permission, so no data leaks and every PATCH/DELETE returns 403. Bug is UX/security-cosmetic (signed-out users see admin chrome but cannot mutate anything).
- **What it blocks**: Trust signal — non-technical observers will think the platform is insecure even though backend permissions hold. Also masks the SUPERADMIN-only nature of the page from school admins, who might assume they can see the same UI.
- **Status (2026-04-27)**: Sprint 16 added `.catch(() => router.push("/"))` to the SUPERADMIN gate in `/dashboard/users` (the page that was actually leaking the table chrome on signed-out tabs). `/dashboard/images` and `dashboard/page.tsx` already render a "please sign in" fallback when profile is null — acceptable UX, no chrome leak. `/dashboard/suggestions` was already gated by useSession status (Sprint 14 hotfix). Backend was correctly gated by `IsSuperAdmin` throughout, so no data ever leaked.

## ✅ TD-18 — Sign-in CTA race fixed (RESOLVED 2026-04-27, Sprint 16)

- **What**: After signing in via the UserMenu on a school page (`/school/<moe>`), the Edit School Data button (SUPERADMIN/bound admin) and Suggest button (other authenticated users) do not appear until the user manually refreshes. Sign-out reactivity works (Sprint 15 hotfix `80b51a0`); sign-in reactivity does not. Both `EditSchoolLink` and `SuggestButton` already subscribe to `useSession()` status and re-fetch `/me` on transition — confirmed by user testing on prod 2026-04-26 web revision `sjktconnect-web-00102-v4f`.
- **Why we accepted**: Minor UX papercut, not a security issue (backend remains correctly gated). One extra page refresh after sign-in is the workaround.
- **What it blocks**: Nothing functional. UX polish only.
- **Actual root cause**: hypothesis (a) was right. Race between two effects that both fire when `useSession()` flips to `"authenticated"`: UserMenu's `syncGoogleAuth(idToken)` POST writes the Django session cookie, while EditSchoolLink/SuggestButton's `fetchMe()` reads it. The fetch frequently arrived at the backend before the POST committed, returning null and hiding the CTA. Manual refresh "fixed" it because the cookie from the prior round was now in place at mount.
- **Fix applied** (Sprint 16): new `frontend/lib/auth-events.ts` (~30-line module-scoped pub/sub emitter). UserMenu fires `emitProfileReady()` after `syncGoogleAuth()` resolves; EditSchoolLink + SuggestButton subscribe via `onProfileReady()` and re-fetch on signal. No polling, no setTimeout. User-verified on prod 2026-04-27 (`web-00104-d4n`) by both `tamiliam` (USER) and `admin` (SUPERADMIN).

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
| ✅ Sprint 14 — Community Photo Uploads | TD-07, TD-09, TD-16 (suggestions page only) | Done 2026-04-26 |
| ✅ Sprint 15 — Image Display Polish | — | Done 2026-04-26 |
| ✅ Sprint 16 — Code-Quality Pass | TD-01 ✅, TD-10 ✅, TD-14 ✅, TD-15 ✅, TD-16 (users page) ✅, TD-17 ✅, TD-18 ✅. TD-11 + TD-12 deferred (test-coverage padding). | Done 2026-04-27 — final of 5-sprint roadmap |
