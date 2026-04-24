# SJK(T) Connect — Tech Debt Register

*Living document. Triaged each sprint. First populated 2026-04-22 after full-codebase audit (item 12 in CLAUDE.md pending list).*

Each entry: **what** / **why we accepted the debt** / **what it blocks** / **cost to fix**.

Severity scale: 🔴 high · 🟡 medium · 🟢 low.

---

## ✅ TD-01 — OAuth security checks disabled in production (RESOLVED 2026-04-24)

- **Status**: Resolved in Sprint 11 Phase 2. Cloudflare reverse proxy adopted 2026-04-23 — frontend (`tamilschool.org`) and backend (`api.tamilschool.org`) now same-site subdomains. OAuth redirect cookies survive the round-trip, `checks: ["pkce", "state"]` restored in `frontend/lib/auth.ts`. End-to-end smoke test passed: sign-in with `tamiliam@gmail.com` + suggestion submission succeed with PKCE+state verification enabled.

## ✅ TD-02 — Magic-link removed, auto-claim on @moe.edu.my (RESOLVED 2026-04-24)

- **Status**: Resolved in Sprint 11a Phase 3. `_maybe_auto_claim()` helper added to `GoogleAuthView`: when sign-in email ends with `@moe.edu.my`, extract moe_code part, look up School, bind `profile.admin_school`, set `school.claimed_at`. Idempotent + protected against overwriting existing claims. Deleted: `SchoolContact` + `MagicLinkToken` models (migration `accounts/0003`), `IsMagicLinkAuthenticated`, `accounts/services/token.py`, `accounts/services/email.py`, magic-link views + URLs + serializers, `/claim/` pages, `ClaimButton` + `ClaimForm` components, all magic-link tests. `SchoolEditView` + `SchoolConfirmView` migrated to `IsProfileAuthenticated` + `admin_school` check (SUPERADMIN bypass). New inline `EmailClaimIndicator` component — Google-style UX: "Claim this page" link or ✓ Verified pill next to the email field. Edge case: SUPERADMIN sets `admin_school` manually via Django admin if HM has lost password.

## ✅ TD-03 — `DATABASE_URL` in `.env` silently hijacks local tests (RESOLVED 2026-04-23)

- **Status**: Resolved. `backend/manage.py` now prints a warning banner on every invocation when `DATABASE_URL` points to a non-local host, and refuses to run a hardcoded list of destructive commands (`migrate`, `flush`, `import_*`, `seed_*`, `harvest_school_images`, etc.) without `SJKTCONNECT_ALLOW_PROD_DB=1`. Read-only commands (`shell`, `test`, `check`) proceed unchanged. `pytest` still needs `DATABASE_URL=` unset for a pure sqlite run — that's now documented behaviour rather than a silent trap.

## ✅ TD-04 — `SESSION_COOKIE_SAMESITE = "None"` workaround (RESOLVED 2026-04-24)

- **Status**: Resolved in Sprint 11 Phase 2. Cloudflare proxy put frontend + backend on same registrable domain (both subdomains of `tamilschool.org`); default `SameSite=Lax` now handles cross-subdomain cookie delivery correctly. Removed `SESSION_COOKIE_SAMESITE = "None"` and `CSRF_COOKIE_SAMESITE = "None"` from `production.py`. Full CSRF protection restored via `SameSite=Lax` default. The DRF `SessionAuthentication` pin (TD-08) from 2026-04-23 remains as defense-in-depth.

## 🟡 TD-05 — School images stored as volatile Google Places URLs

- **What**: `outreach/services/image_harvester.py` stores `places.googleapis.com/.../photos/...` URLs in `SchoolImage.image_url`. All such URLs on SJK(T) schools now return HTTP 400 (`INVALID_ARGUMENT`) — Google has invalidated the photo resource IDs. Every school page on tamilschool.org currently shows broken hero images + 3 broken Places thumbnails; only the satellite fallback renders. Also: every page load triggers browser requests to these dead URLs, bloating egress (see TD-06).
- **Why we accepted**: Storing URLs was cheap; re-harvesting ~monthly was presumed sufficient. Turns out Google rotates resource IDs on a shorter and unpredictable cycle.
- **What it blocks**: Visible product quality (broken images on every school page). Community trust. And it's the likely driver of TD-06.
- **Cost to fix**: 1 full sprint. Plan in `docs/plans/2026-04-22-image-library-sprint-plan.md` — store bytes in Supabase Storage, add community upload flow, 20-photo cap, moderation. Sprint 9.

## 🟡 TD-06 — Supabase egress regression

- **What**: Target was <100 MB/day after the March 29 egress fix. Actual on 2026-04-21 dashboard: 500 MB–1 GB/day, with a 1014 MB spike on 11 Apr. `defer("boundary_wkt")` fix is still in place (6 defers in `schools/api/views.py`), so a new egress source has emerged.
- **Why we accepted**: Not intentionally — unnoticed drift since the March fix.
- **What it blocks**: Cost risk. Supabase free tier cap is 5 GB/month. At 1 GB/day we'd blow the cap by day 5 every billing cycle. Next.js image-optimiser retries on the dead Places URLs (TD-05) are the prime suspect.
- **Cost to fix**: Likely resolves automatically when TD-05 ships. Until then, run a 2-4 hour investigation to confirm hypothesis via Cloud Run access logs. Already tracked as item #4 in CLAUDE.md pending list.

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

## 🟢 TD-13 — `uploaded_by` on `SchoolImage` never set by harvester

- **What**: `SchoolImage.uploaded_by` FK to `UserProfile` exists (added Sprint 8.2) but is never set by `harvest_satellite_image` or `harvest_places_images` — only populated when community uploads approve. So for the vast majority of images the field is NULL.
- **Why we accepted**: Semantically correct — harvester images weren't uploaded by any user.
- **What it blocks**: Nothing. Flagged only because reading the code you might expect it to always be set.
- **Cost to fix**: No fix needed — could add a comment explaining that NULL means harvester-sourced.

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

---

## Triage for next sprints

| Fix | Debt items | Sprint |
|---|---|---|
| ✅ Pin DRF auth classes | TD-08 | Done 2026-04-23 |
| ✅ Local-dev DATABASE_URL guard | TD-03 | Done 2026-04-23 |
| ✅ Cloudflare proxy + restore OAuth checks | TD-01, TD-04 | Done 2026-04-24 (Sprint 11a Phases 1+2) |
| ✅ Delete magic-link + auto-claim + EmailClaimIndicator | TD-02 | Done 2026-04-24 (Sprint 11a Phase 3) |
| ✅ Next 14 → 16 upgrade | TD-10 | Done 2026-04-24 (Sprint 11a Phase 4); 2 transitive residuals |
| Move images to Supabase Storage + validate format | TD-05, TD-07, TD-09, TD-06 | **Sprint 9 (Image Library)** |
| Resolve egress regression | TD-06 | Investigated; resolves with Sprint 9 |
| Coverage gaps | TD-11, TD-12 | Absorb into relevant feature sprints |
| Code polish | TD-13, TD-14, TD-15 | Low priority |
