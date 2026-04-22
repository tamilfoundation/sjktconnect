# SJK(T) Connect — Tech Debt Register

*Living document. Triaged each sprint. First populated 2026-04-22 after full-codebase audit (item 12 in CLAUDE.md pending list).*

Each entry: **what** / **why we accepted the debt** / **what it blocks** / **cost to fix**.

Severity scale: 🔴 high · 🟡 medium · 🟢 low.

---

## 🔴 TD-01 — OAuth security checks disabled in production

- **What**: `frontend/lib/auth.ts:10` has `checks: []` on the NextAuth Google provider, disabling PKCE, state, and nonce verification.
- **Why we accepted**: Cloud Run domain mapping drops cookies during the OAuth redirect chain. Six attempted fixes in March 2026 all failed; the `checks: []` workaround was merged (`570dea3`, 2026-03-11) to unblock sign-in and has been live since.
- **What it blocks**: Safely shipping community-facing features. Without PKCE + state, the flow is vulnerable to CSRF on callback and authorization-code interception. Acceptable at 1-user scale; not acceptable at community launch.
- **Cost to fix**: ~½ sprint. Adopt Cloudflare proxy per `docs/proposals/2026-03-11-cloudflare-proxy-proposal.md` to make cookies same-origin, then restore `checks: ["pkce", "state"]`. Part A of Sprint 11 (User Management).

## 🔴 TD-02 — Magic-link authentication system is dead code

- **What**: The `SchoolContact` + `MagicLinkToken` models, `IsMagicLinkAuthenticated` permission, `accounts/services/token.py`, and associated views cover ~400 LOC but have **0 usage in production** (0 contacts, 0 tokens ever issued). Meanwhile `schools/api/views.py` still requires `IsMagicLinkAuthenticated` on `SchoolEditView` and `SchoolConfirmView` — making the "Edit school" and "Confirm data" buttons on every school page unusable by every real user.
- **Why we accepted**: Magic-link shipped first (Sprint 1.6, Feb 2026), Google OAuth came later (Sprint 8.1, Mar 2026). The community admin panel design was approved but the migration of school-edit endpoints to OAuth was never completed.
- **What it blocks**: The school-edit UX is visibly broken on the live site. Also makes the codebase hard to navigate (two auth paths for the same use case, neither obviously canonical).
- **Cost to fix**: ~1 day. Either (a) migrate `SchoolEditView` + `SchoolConfirmView` to `IsProfileAuthenticated` + `profile.admin_school_id == school.pk` check, then delete magic-link models, services, views, tests, and frontend pages; or (b) keep magic-link and explicitly decide it's the "school-staff claim" path, OAuth is the "community" path. Strong recommendation: (a).

## 🔴 TD-03 — `DATABASE_URL` in `.env` silently hijacks local tests

- **What**: Repo-root `.env` auto-loads a Supabase prod DSN. Every local `manage.py test` / `pytest` attempts to run against production unless `DATABASE_URL` is explicitly unset. During the audit, running `pytest` produced 968 failures + 714 errors because tests hit prod Supabase; unsetting `DATABASE_URL` restored 1,107 passing tests.
- **Why we accepted**: Convenience — `.env` makes `manage.py shell` hit prod for quick data checks (e.g. today's `SchoolImage` patch).
- **What it blocks**: Correct test runs. Also invites accidental writes against prod from any local command.
- **Cost to fix**: ~1 hour. Options: (a) guard in `manage.py` that prints target DB + requires `--confirm-prod` for writes, (b) remove `DATABASE_URL` from local `.env` (revert to sqlite) + use an explicit `.env.prod` for ops work, (c) provision a Supabase dev branch. Already tracked as item #7 in CLAUDE.md pending list. Pick (b) — operationally simplest.

## 🟡 TD-04 — `SESSION_COOKIE_SAMESITE = "None"` workaround

- **What**: Today's fix (`backend/sjktconnect/settings/production.py:36-39`) sets `SESSION_COOKIE_SAMESITE = "None"` and `CSRF_COOKIE_SAMESITE = "None"` so session cookies survive cross-origin fetch from `tamilschool.org` to `sjktconnect-api-*.run.app`.
- **Why we accepted**: Browser third-party cookie handling blocked sign-in for anyone signing up after OAuth went live. `SameSite=None` is the minimum change that restores function.
- **What it blocks**: `SameSite=None` expands CSRF surface (browser attaches cookie to cross-origin POSTs). Mitigated today by `Secure` flag + CORS allowlist + DRF `SessionAuthentication`'s CSRF enforcement. But the mitigation is implicit — a future change adding `TokenAuthentication` to DRF defaults would silently remove CSRF protection. Also, Chrome's third-party cookie phase-out will block these entirely some time in 2026.
- **Cost to fix**: Same as TD-01 — Cloudflare proxy makes cookies same-origin, allowing `SameSite=Lax` and removing both risks. Until then, pin `REST_FRAMEWORK["DEFAULT_AUTHENTICATION_CLASSES"] = ["rest_framework.authentication.SessionAuthentication"]` explicitly (15 min) to prevent silent regressions.

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

## 🟡 TD-08 — No `DEFAULT_AUTHENTICATION_CLASSES` pinned

- **What**: `REST_FRAMEWORK` in `backend/sjktconnect/settings/base.py:118-121` doesn't set `DEFAULT_AUTHENTICATION_CLASSES`. DRF falls back to `(SessionAuthentication, BasicAuthentication)`. This happens to work with the existing session flow + provides CSRF protection, but it's an implicit dependency that a future change could break.
- **Why we accepted**: Set-and-forget defaults worked at the time of Sprint 8.1.
- **What it blocks**: Hidden dependency of TD-04's security posture. A developer adding `TokenAuthentication` wouldn't realise they're removing CSRF protection.
- **Cost to fix**: 15 minutes. Explicitly set `DEFAULT_AUTHENTICATION_CLASSES = ["rest_framework.authentication.SessionAuthentication"]`. Add a unit test verifying it hasn't been relaxed.

## 🟡 TD-09 — Hardcoded `content_type="image/png"` on suggestion image endpoint

- **What**: `backend/community/api/views.py:130` serves arbitrary uploaded bytes with `content_type="image/png"` regardless of actual format. No magic-byte validation, no Pillow verification on upload.
- **Why we accepted**: MVP shortcut in Sprint 8.2. Unlikely to be exploited at current 1-user scale.
- **What it blocks**: Minor — browsers don't execute scripts inside `<img>` regardless of declared format, so stored XSS is not exploitable. But opens the door to content-type confusion if a future endpoint serves SVG or raw.
- **Cost to fix**: Replaced entirely by Sprint 9 (TD-05) which validates format, strips EXIF, resizes, and stores in typed Supabase Storage.

## 🟢 TD-10 — 3 moderate npm vulnerabilities

- **What**: `npm audit` reports:
  - `next` (<15.5.10) — DoS via Image Optimizer `remotePatterns`. We're on Next 14.
  - `next-intl` (<4.9.1) — Open redirect
  - `picomatch` (<2.3.2) — Glob injection (transitive)
- **Why we accepted**: Not intentional — just haven't upgraded.
- **What it blocks**: Nothing urgent, but clean `npm audit` is a launch hygiene item.
- **Cost to fix**: ~30 min to upgrade, re-run tests, verify UI doesn't regress. Possibly more if Next 14→15 introduces breaking changes (check their upgrade guide).

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
| Adopt Cloudflare proxy + restore OAuth checks + pin DRF auth | TD-01, TD-04, TD-08 | **Sprint 11 (User Management)** |
| Delete magic-link system + migrate school-edit to OAuth | TD-02 | **Sprint 11 (User Management)** |
| Local-dev DATABASE_URL guard | TD-03 | Quick fix (1 hr) — do before Sprint 11 |
| Move images to Supabase Storage + validate format | TD-05, TD-07, TD-09, TD-06 | **Sprint 9 (Image Library)** |
| Resolve egress regression | TD-06 | Investigated; resolves with Sprint 9 |
| npm audit upgrades | TD-10 | Quick fix (30 min) — do before Sprint 11 |
| Coverage gaps | TD-11, TD-12 | Absorb into relevant feature sprints |
| Code polish | TD-13, TD-14, TD-15 | Low priority |
