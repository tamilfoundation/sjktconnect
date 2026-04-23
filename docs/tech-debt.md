# SJK(T) Connect — Tech Debt Register

*Living document. Triaged each sprint. First populated 2026-04-22 after full-codebase audit (item 12 in CLAUDE.md pending list).*

Each entry: **what** / **why we accepted the debt** / **what it blocks** / **cost to fix**.

Severity scale: 🔴 high · 🟡 medium · 🟢 low.

---

## ✅ TD-01 — OAuth security checks disabled in production (RESOLVED 2026-04-24)

- **Status**: Resolved in Sprint 11 Phase 2. Cloudflare reverse proxy adopted 2026-04-23 — frontend (`tamilschool.org`) and backend (`api.tamilschool.org`) now same-site subdomains. OAuth redirect cookies survive the round-trip, `checks: ["pkce", "state"]` restored in `frontend/lib/auth.ts`. End-to-end smoke test passed: sign-in with `tamiliam@gmail.com` + suggestion submission succeed with PKCE+state verification enabled.

## 🔴 TD-02 — Magic-link auth redundant with Google Workspace sign-in

- **What**: The `SchoolContact` + `MagicLinkToken` models, `IsMagicLinkAuthenticated` permission, `accounts/services/token.py`, claim pages, and associated views cover ~400 LOC but have **0 usage in production** (0 contacts, 0 tokens ever issued — not because the design failed, but because the claim flow has never been publicised to schools). Meanwhile `SchoolEditView` + `SchoolConfirmView` still require `IsMagicLinkAuthenticated`, making the "Edit school" and "Confirm data" buttons unusable for every real user.
- **Why we accepted**: Magic-link shipped first (Sprint 1.6, Feb 2026), Google OAuth came later (Sprint 8.1, Mar 2026). Never reconciled. The original magic-link design (send a token to `<moe_code>@moe.edu.my`, click link to log in) is sound — it proves the user has access to the school's official inbox.
- **What made it redundant (discovered 2026-04-23)**: `moe.edu.my` is on Google Workspace (`dig MX moe.edu.my` → `ASPMX.L.GOOGLE.COM`). This means every `<moe_code>@moe.edu.my` inbox IS a Google account that can sign in via OAuth directly. The magic-link round-trip (click button → open email → click link) is strictly redundant with signing in via the same Google account — OAuth gives the same proof of inbox access in one click.
- **What it blocks**: The school-edit UX is visibly broken. Two parallel identity systems in the codebase.
- **Cost to fix**: ~1 day. In `GoogleAuthView`, after the `UserProfile` is created, check if `email.endswith("@moe.edu.my")` and if so extract the moe_code part and set `profile.admin_school`. ~10 LOC. Then delete `SchoolContact`, `MagicLinkToken`, `IsMagicLinkAuthenticated`, `accounts/services/token.py`, `RequestMagicLinkView`, `VerifyMagicTokenView`, `/claim/` and `/claim/verify/[token]/` pages, `ClaimButton` + `ClaimForm` components, and all magic-link tests. Migrate `SchoolEditView` + `SchoolConfirmView` to `IsProfileAuthenticated + profile.admin_school_id == moe_code` check. Edge case (inactive MOE account, lost password): SUPERADMIN sets `admin_school` manually via Django admin; no UI needed Phase 1.

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

## 🟢 TD-10 — Next.js 14 on a superseded version (partially resolved 2026-04-23)

- **Status**: `next-intl` upgraded from 4.8.3 → 4.9.1+ on 2026-04-23, clearing the open-redirect advisory. Remaining items:
  - `next` still on 14.2.x. The flagged Image Optimizer DoS (GHSA-9g9p-9gw9-jx7f) only triggers when `remotePatterns` is configured in `next.config.js`. **We don't use `remotePatterns`**, so we're not currently exploitable. Still worth upgrading for routine hygiene and to clear the audit report.
  - `picomatch` (<2.3.2) is a transitive of Next 14; resolves with Next upgrade.
- **Why we accepted**: Next 14 → 15 is a major version bump with breaking async API changes (`params`, `cookies()`, `headers()` are now promises). At least 5 app-router pages would need updates. Not worth a rushed upgrade when we're not exploitable.
- **What it blocks**: Clean `npm audit` output at launch.
- **Cost to fix**: ~4-6 hours for a proper Next 15 migration (test + deploy + regression check). Recommended: fold into Sprint 11 (User Management) since that sprint is already touching auth + frontend.

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
| ✅ next-intl upgrade | TD-10 (partial) | Done 2026-04-23 |
| Adopt Cloudflare proxy + restore OAuth checks + Next 15 upgrade | TD-01, TD-04, TD-10 (remainder) | **Sprint 11 (User Management)** |
| Delete magic-link system + migrate school-edit to OAuth | TD-02 | **Sprint 11 (User Management)** |
| Move images to Supabase Storage + validate format | TD-05, TD-07, TD-09, TD-06 | **Sprint 9 (Image Library)** |
| Resolve egress regression | TD-06 | Investigated; resolves with Sprint 9 |
| Coverage gaps | TD-11, TD-12 | Absorb into relevant feature sprints |
| Code polish | TD-13, TD-14, TD-15 | Low priority |
