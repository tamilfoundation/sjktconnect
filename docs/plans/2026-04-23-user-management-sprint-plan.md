# User Management Sprint Plan

**Date**: 2026-04-23
**Branch**: `feat/user-management`
**Goal**: Fix the auth foundation — adopt Cloudflare proxy, restore OAuth security, collapse two identity systems into one, add self-service user management UI. Bundles the Next 14 → 15 upgrade while we're touching auth.

## Context

The 2026-04-22 audit surfaced four high-severity debt items that all share one root cause — the frontend (`tamilschool.org`) and backend (`*.run.app`) are on different origins, forcing a cascade of workarounds:

- **TD-01**: OAuth checks disabled (`frontend/lib/auth.ts:10` has `checks: []`) because Cloud Run's domain mapping drops cookies mid-OAuth-redirect.
- **TD-04**: `SESSION_COOKIE_SAMESITE = "None"` workaround added 2026-04-22 because browser blocks cookies cross-origin.
- **TD-02**: Magic-link auth system dormant but still wired into `SchoolEditView` + `SchoolConfirmView`, making edit flow unusable for every real user.
- **TD-10**: Next 14 on a superseded line (not urgently exploitable but blocking audit hygiene).

Cloudflare proxy fixes TD-01 and TD-04 at the root by making frontend and backend same-origin. Once that's done, the magic-link removal + auto-claim simplification (TD-02) is a self-contained ~1 day of work. Next 15 is bundled because it touches 5+ of the same pages the auth work will anyway.

## Design Decisions (locked)

| # | Decision |
|---|---|
| 1 | Adopt **Cloudflare free tier** as reverse proxy. `tamilschool.org/*` → frontend Cloud Run; `tamilschool.org/api/*` → backend Cloud Run. Cache rules per `docs/proposals/2026-03-11-cloudflare-proxy-proposal.md`. |
| 2 | Keep Cloud Run domain mapping in place (inactive) for instant rollback. |
| 3 | Remove `SESSION_COOKIE_SAMESITE = "None"` + `CSRF_COOKIE_SAMESITE = "None"` once Cloudflare is live. Default `SameSite=Lax` is correct for same-origin. |
| 4 | Restore NextAuth `checks: ["pkce", "state"]`. Remove the `checks: []` workaround. |
| 5 | **Auto-claim on Google sign-in**: in `GoogleAuthView`, if `email.endswith("@moe.edu.my")`, extract moe_code, bind `profile.admin_school` automatically. Verified 2026-04-23 that `moe.edu.my` is on Google Workspace (`dig MX moe.edu.my` → `ASPMX.L.GOOGLE.COM`). |
| 6 | **Delete magic-link system entirely**: `SchoolContact`, `MagicLinkToken`, `IsMagicLinkAuthenticated`, `accounts/services/token.py`, claim pages, ClaimButton/ClaimForm, all magic-link tests. |
| 7 | **Migrate** `SchoolEditView` + `SchoolConfirmView` to `IsProfileAuthenticated` + `profile.admin_school_id == moe_code` check. |
| 8 | **Fallback for inactive MOE accounts**: SUPERADMIN manually sets `admin_school` via Django admin. No UI needed Phase 1. |
| 9 | **`/dashboard/users` page**: SUPERADMIN only. List, search, change role, assign/clear school admin, deactivate. |
| 10 | **Self-service profile page** (already exists at `/profile`): add pending-suggestions section, display points, allow display name edit. |
| 11 | **Next 14 → 15 upgrade** bundled. Breaking: `params`/`cookies()`/`headers()` become async. Migrate ~5 app-router pages. |
| 12 | **Pre-sprint ARCHITECTURE_MAP.md refresh**: full 6-week drift catch-up before Phase 1. |

---

## Phase 0 — Prerequisites (before coding)

### 0.1 Full ARCHITECTURE_MAP.md refresh (~30 min)
Map has ~6 weeks of drift. Sections needing attention:
- `community` app beyond today's targeted update (models.py field-level, Suggestion lifecycle diagram)
- `feedback` app (models, services, scheduler cadence)
- Frontend routes added since Mar 7 (profile, dashboard, news, donate)
- Frontend components added since Mar 7 (~15 components — SuggestForm, ModerationQueue, ImageManager, UserMenu, AuthProvider, etc.)
- Sprint 5.x additions (MP model, MeetingIllustration, QualityLog)
- Sprint 6.x (context_builder, report context JSON v2.0)
- Sprint 7.x (evaluator, corrector, learner, name_repairer)
- Sprint 8.x Cloud Run jobs + schedulers (urgent-alerts, fortnightly-digest, resume-sending, process-feedback, Brevo webhook endpoint)
- Recent egress mitigations (`defer("boundary_wkt")`, middleware IP blocking, `minScale=1`)

### 0.2 Cloudflare dry-run subdomain (~30 min)
Create `test.tamilschool.org` subdomain in current DNS (awedns.com) pointing via Cloudflare to the Cloud Run frontend. Exercise:
- Sign-in with restored PKCE checks works
- API POSTs (suggestion submit) carry the session cookie
- No new CORS errors

Validates the plan before we touch the main domain.

---

## Phase 1 — Cloudflare Adoption

### 1.1 Set up Cloudflare (free tier)
- Create Cloudflare account (if not existing)
- Add `tamilschool.org` as a site; Cloudflare auto-detects current DNS records
- **Document existing nameservers** for rollback before switching
- Update registrar (awedns.com) nameservers to Cloudflare's two NS addresses
- Wait for propagation (5–30 min typical, up to 24h)

### 1.2 DNS + routing config
| Host | Routes to | Purpose |
|---|---|---|
| `tamilschool.org` (apex) | `sjktconnect-web-748286712183.asia-southeast1.run.app` (via CNAME flattening) | Frontend |
| `api.tamilschool.org` | `sjktconnect-api-748286712183.asia-southeast1.run.app` | Backend |

**Alternative**: path-based routing (`tamilschool.org/api/*` via Cloudflare Worker) — but subdomain is simpler. Subdomain still shares the root domain cookie, so same-origin cookie behaviour is preserved.

### 1.3 Cloudflare settings
- SSL mode: **Full (strict)**
- Cache rules:
  - `*/api/*` — bypass cache
  - `*/_next/static/*` — cache everything, long TTL
  - `*.js, *.css, *.png, *.jpg, *.ico, *.woff2` — cache everything
  - Everything else (HTML) — bypass cache (because ISR pages may contain user-specific content)

### 1.4 Backend env var updates
- `ALLOWED_HOSTS` — add `api.tamilschool.org`
- `CSRF_TRUSTED_ORIGINS` — add `https://api.tamilschool.org` + `https://tamilschool.org`
- `CORS_ALLOWED_ORIGINS` — add `https://tamilschool.org`; keep old entries until frontend redeploy

### 1.5 Frontend env var updates
- `NEXT_PUBLIC_API_URL` — change from `https://sjktconnect-api-748286712183.asia-southeast1.run.app` to `https://api.tamilschool.org`
- `NEXTAUTH_URL` — confirm `https://tamilschool.org`

### 1.6 Keep Cloud Run domain mapping in place (inactive)
Don't delete the existing `tamilschool.org` domain mapping in Cloud Run. Rollback = nameserver switch back to original, with zero re-verification delay.

### 1.7 Smoke tests
Post-deploy verification:
- Sign in as `tamiliam@gmail.com` on `https://tamilschool.org`
- Submit a Note suggestion — confirm it lands in DB (no 403)
- Submit a photo — confirm preview renders, submission succeeds
- Approve a suggestion as `admin@tamilfoundation.org` — confirm DB update

---

## Phase 2 — Remove Auth Workarounds

### 2.1 Restore OAuth checks (`frontend/lib/auth.ts`)
```diff
 Google({
   clientId: process.env.GOOGLE_OAUTH_CLIENT_ID!,
   clientSecret: process.env.GOOGLE_OAUTH_CLIENT_SECRET!,
-  checks: [],
+  checks: ["pkce", "state"],
 }),
```

### 2.2 Remove SameSite=None workaround (`backend/sjktconnect/settings/production.py`)
```diff
 SESSION_COOKIE_SECURE = True
 CSRF_COOKIE_SECURE = True
-# Required for cross-domain cookies...
-SESSION_COOKIE_SAMESITE = "None"
-CSRF_COOKIE_SAMESITE = "None"
```
Default `SameSite=Lax` now applies, which is correct for same-origin.

### 2.3 Update tech-debt register
- TD-01 → RESOLVED
- TD-04 → RESOLVED

---

## Phase 3 — Delete Magic-Link, Add Auto-Claim

### 3.1 Add auto-claim logic (`backend/accounts/api/views.py`, `GoogleAuthView.post`)
```python
# After UserProfile is created/fetched, before set session:
email = google_info["email"]
if email.endswith("@moe.edu.my") and not profile.admin_school_id:
    moe_code = email.split("@")[0].upper()
    try:
        school = School.objects.get(moe_code=moe_code, is_active=True)
        profile.admin_school = school
        profile.save(update_fields=["admin_school", "updated_at"])
    except School.DoesNotExist:
        pass  # email format matches but not a real school code
```
~10 LOC. Idempotent — only sets `admin_school` if unset.

### 3.2 Migrate `SchoolEditView` + `SchoolConfirmView` (`backend/schools/api/views.py`)
```diff
-from accounts.permissions import IsMagicLinkAuthenticated
+from accounts.permissions import IsProfileAuthenticated

 class SchoolEditView(APIView):
-    permission_classes = [IsMagicLinkAuthenticated]
+    permission_classes = [IsProfileAuthenticated]

     def _get_school(self, moe_code, request):
         ...
-        if request.school_moe_code != moe_code:
+        profile = request.user_profile
+        if profile.role != "SUPERADMIN" and profile.admin_school_id != moe_code:
             return None, Response(
                 {"error": "You can only edit your own school."},
                 status=status.HTTP_403_FORBIDDEN,
             )
         return school, None
```
Same pattern on `SchoolConfirmView`. Also update `AuditLog.detail` to record `profile.user.email` instead of `request.school_contact.email`.

### 3.3 Delete magic-link code
Files to remove entirely:
- `backend/accounts/services/token.py`
- `backend/accounts/services/email.py` (confirm no non-magic-link callers first)
- `backend/accounts/tests/test_api.py` (magic-link tests — keep OAuth tests)
- `backend/accounts/tests/test_models.py` (MagicLinkToken + SchoolContact tests)
- `backend/accounts/tests/test_link_school.py` (if magic-link-specific)
- `frontend/app/[locale]/claim/page.tsx`
- `frontend/app/[locale]/claim/verify/[token]/page.tsx`
- `frontend/components/ClaimButton.tsx`
- `frontend/components/ClaimForm.tsx`
- `frontend/lib/api.ts` functions: `requestMagicLink`, `verifyMagicLink` (if OAuth-only elsewhere)
- Translation keys: `claim.*`, `magicLink.*` in `messages/{en,ta,ms}.json`

Models to remove via migration:
- `accounts.MagicLinkToken`
- `accounts.SchoolContact`
- `accounts.UserProfile` — no change (keep)

Permissions to remove from `backend/accounts/permissions.py`:
- `IsMagicLinkAuthenticated`

URLs to remove from `backend/accounts/api/urls.py`:
- `path("request-magic-link/", RequestMagicLinkView, ...)`
- `path("verify-magic-link/", VerifyMagicTokenView, ...)`

### 3.4 Migration 0003 (accounts)
Django autogenerated migration to drop `MagicLinkToken` + `SchoolContact` tables. Also updates `AuditLog.tracked_models` in `base.py`:
```diff
 AUDIT_LOG_MODELS = [
     ...
-    "accounts.SchoolContact",
-    "accounts.MagicLinkToken",
 ]
```

### 3.5 Frontend simplification
- `EditSchoolLink` component: render only when `profile?.admin_school?.moe_code === moe_code` (check already fetched on every page via UserMenu's `syncGoogleAuth`).
- Add a simple `AdminBadge` on the school page for admins: "You manage this school" with an Edit button.
- Remove all references to `IsMagicLinkAuthenticated` / magic-link in tests.

### 3.6 Update tech-debt register
- TD-02 → RESOLVED

---

## Phase 4 — Next 14 → 15 Upgrade

### 4.1 Dependency upgrade
```bash
cd frontend
npm install next@latest
npm install react@latest react-dom@latest  # Next 15 prefers React 19; verify @testing-library compat first
```

### 4.2 Breaking changes — async request APIs
Pages using `params`, `searchParams`, `cookies()`, `headers()` need `await`:

| File | Change |
|---|---|
| `app/[locale]/school/[moe_code]/page.tsx` | `params` → `await params` |
| `app/[locale]/constituency/[code]/page.tsx` | `params` → `await params` |
| `app/[locale]/dun/[id]/page.tsx` | `params` → `await params` |
| `app/[locale]/donate/thank-you/page.tsx` | `searchParams` → `await searchParams` |
| `app/[locale]/layout.tsx` | may use `cookies()`; audit and await |

Grep for these patterns in Phase 4 kick-off to confirm scope.

### 4.3 ignoreBuildErrors cleanup
`next.config.js:9` has:
```js
typescript: {
  ignoreBuildErrors: true,  // workaround for Next 14 auto-generated types
},
```
Next 15 + TypeScript 5.9 likely fixes this. Remove the flag and let build errors surface. If they do, address before merging.

### 4.4 Re-run npm audit
```bash
npm audit --omit=dev
```
Expect clean (or at most transitive moderate) after Next 15 picks up patched picomatch.

### 4.5 Update tech-debt register
- TD-10 → RESOLVED

---

## Phase 5 — `/dashboard/users` UI

### 5.1 Backend endpoint
- `GET /api/v1/admin/users/` — SUPERADMIN only. Returns paginated list with filters `?role=&search=&has_admin_school=`.
- `PATCH /api/v1/admin/users/<id>/` — update `role`, `admin_school`, `is_active`.
- `DELETE /api/v1/admin/users/<id>/` — soft-delete (sets `is_active=False`).

Permissions: `IsProfileAuthenticated` + `IsSuperAdmin`.

### 5.2 Frontend page `/dashboard/users/page.tsx`
- Table: avatar, display name, email, role, admin_school, points, is_active, created_at
- Filter controls: role dropdown, "has school admin" toggle, search input
- Per-row actions: Change role, Assign/Clear school admin (modal with searchable school picker), Deactivate/Reactivate
- Pagination (50/page matching backend default)

### 5.3 Permissions in UserMenu
Add "User Management" link under Dashboard for SUPERADMIN only (already has role-based rendering).

### 5.4 Self-service `/profile` additions (page already exists)
- Show points count + all-time rank
- Show "My Suggestions" list (paginated): status, school, type, submitted date
- Editable: display_name (push to backend; updates `UserProfile.display_name`)

---

## Tests

**Backend** (~25 new tests):
- Auto-claim logic: `@moe.edu.my` email matches School → admin_school set; non-moe email → unset; moe email without matching school → unset; already-assigned profile → not overwritten
- Migrated `SchoolEditView` permission matrix (SUPERADMIN / matching school admin / non-matching admin / regular user / anonymous)
- New `/api/v1/admin/users/` endpoints — permission matrix, filtering, pagination, role change audit, deactivation

**Backend deletions** (~30 tests removed):
- All magic-link tests retired

**Frontend** (~10 new tests):
- `/dashboard/users` list render, filter, role change modal, school assignment modal
- Auto-claim UX: after sign-in with `@moe.edu.my`, UserMenu shows Admin Dashboard link immediately
- Regression: EditSchoolLink renders iff `profile.admin_school.moe_code === moe_code`

**Frontend deletions** (~8 tests removed):
- ClaimForm, ClaimButton, claim page flow tests

**Net**: ~1145 backend (was 1109) + ~275 frontend (was 271).

---

## Deployment Sequence

1. **Cloudflare setup on test subdomain** — validate proxy + smoke-test OAuth round-trip
2. **Merge backend changes first** — new admin endpoints shipped but dormant (no frontend caller yet)
3. **Cloudflare main domain** — nameserver switch; wait for propagation
4. **Remove SameSite=None, restore OAuth checks** — requires Cloudflare live first
5. **Merge frontend changes** — Next 15 upgrade + magic-link UI deletion + new user management page
6. **Delete magic-link code + migration** — requires all magic-link code paths dead (no frontend caller)
7. **Run migration 0003** via `gcloud run jobs execute` or post-deploy — drops SchoolContact + MagicLinkToken tables
8. **Verify in prod**: sign-in flow, edit school as school admin, moderation queue, `/dashboard/users`
9. **Retire old ClaimButton/EditSchoolLink permission checks** — if any remaining after Phase 5

---

## Risks & Mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| Cloudflare nameserver switch + propagation breaks live site | Low (subdomain-tested first) | Rollback = switch nameservers back; Cloud Run domain mapping kept alive |
| Auto-claim extracts wrong `moe_code` | Low | All 528 school moe_codes are 7 chars uppercase; email prefix guaranteed to match one if it's a legitimate school inbox. Test covers non-matching formats. |
| Next 15 upgrade breaks ISR / caching | Medium | Next 15 changed cache defaults. Test on all 5 migrated pages before merging. |
| Someone signs in with personal `@gmail.com` claiming they're school admin | Not a risk | Auto-claim only fires on `@moe.edu.my`. Personal emails get role=USER, no admin_school. Fallback is SUPERADMIN manual assignment. |
| Dropping SchoolContact breaks a live user's session | **Zero users affected** (0 contacts ever) | — |
| Admin accidentally locks themselves out via `/dashboard/users` | Medium | Prevent SUPERADMIN from demoting themselves via a check in the PATCH handler: `if profile.id == request.user_profile.id and new_role != "SUPERADMIN": refuse`. |

---

## Files Expected to Change (~40)

**Backend — deletions** (~12 files)
- `accounts/services/token.py` (delete)
- `accounts/services/email.py` (delete if no non-magic callers)
- `accounts/tests/test_api.py` (delete magic-link sections, keep OAuth)
- `accounts/tests/test_models.py` (delete magic-link model tests)
- `accounts/tests/test_link_school.py` (delete)
- Various URL + view references to magic-link removed

**Backend — additions/changes** (~10 files)
- `accounts/api/views.py` (auto-claim in GoogleAuthView + new admin user views)
- `accounts/api/serializers.py` (UserProfileAdminSerializer)
- `accounts/api/urls.py` (admin user URLs + magic-link URLs removed)
- `accounts/permissions.py` (remove IsMagicLinkAuthenticated)
- `accounts/migrations/0003_drop_magic_link.py` (NEW)
- `accounts/tests/test_auto_claim.py` (NEW)
- `accounts/tests/test_admin_users.py` (NEW)
- `schools/api/views.py` (SchoolEditView + SchoolConfirmView permission migration)
- `schools/tests/test_edit_api.py` (updated assertions)
- `sjktconnect/settings/base.py` (AUDIT_LOG_MODELS + CORS_ALLOWED_ORIGINS)
- `sjktconnect/settings/production.py` (remove SameSite=None)

**Frontend — deletions** (~10 files)
- `app/[locale]/claim/page.tsx`
- `app/[locale]/claim/verify/[token]/page.tsx`
- `components/ClaimButton.tsx`
- `components/ClaimForm.tsx`
- Related tests

**Frontend — additions/changes** (~15 files)
- `lib/auth.ts` (restore checks)
- `app/[locale]/dashboard/users/page.tsx` (NEW)
- `components/UserManagementTable.tsx` (NEW)
- `components/RoleChangeModal.tsx` (NEW)
- `components/SchoolAssignModal.tsx` (NEW)
- `components/AdminBadge.tsx` (NEW)
- `app/[locale]/profile/page.tsx` (additions: points, my suggestions, editable name)
- `components/UserMenu.tsx` (User Management link for SUPERADMIN)
- `components/EditSchoolLink.tsx` (simplify to profile.admin_school check)
- `lib/api.ts` (admin user endpoints, remove magic-link functions)
- `messages/{en,ta,ms}.json` (remove claim.* / magicLink.*, add userManagement.*)
- Various page files (Next 15 `await params` migration)
- `next.config.js` (remove ignoreBuildErrors)
- `package.json` (Next 15, React 19, testing-library updates)

**Ops/docs**
- `docs/plans/2026-04-23-user-management-sprint-plan.md` (this file)
- `docs/tech-debt.md` (TD-01, TD-02, TD-04, TD-10 → resolved)
- `CHANGELOG.md`
- `CLAUDE.md` (Apps table, Next Sprint rewrite)
- `.claude/ARCHITECTURE_MAP.md` (magic-link removal reflected)

---

## Rollback Plan

### Cloudflare rollback (if DNS switch breaks)
1. Switch registrar nameservers back to awedns original (documented pre-switch)
2. Cloud Run domain mapping still active — serves traffic within 5–30 min
3. Re-apply `SESSION_COOKIE_SAMESITE = "None"` + `checks: []` if needed

### Full sprint rollback
1. `git revert` the merge commit on main
2. `gcloud run services update-traffic` to previous healthy revisions
3. Magic-link DB rows are gone after migration — if rollback needed, restore from Supabase point-in-time backup (daily cadence available on free tier)

### Partial rollback
If only one phase breaks, each phase's commits can be reverted independently (phases designed to be orthogonal).

---

## Success Criteria

- [ ] `tamilschool.org` served through Cloudflare (`curl -I` shows `cf-ray` header)
- [ ] Incognito sign-in with `tamiliam@gmail.com` works; session cookie is first-party
- [ ] OAuth `checks` restored without breaking sign-in
- [ ] `SESSION_COOKIE_SAMESITE` removed from production.py
- [ ] Headteacher signing in with `kbd6019@moe.edu.my` immediately sees Admin Dashboard + can edit KBD6019
- [ ] Edit-school + confirm-school work for admin@tamilfoundation.org (as SUPERADMIN) and for any @moe.edu.my account (as their own school's admin)
- [ ] `/dashboard/users` accessible by admin@tamilfoundation.org only; lists 2+ users; role change + school assignment persist
- [ ] `npm audit` clears next, next-intl, picomatch
- [ ] All magic-link code removed from codebase; migrations 0003 applied
- [ ] All 4 tech debt items closed (TD-01, TD-02, TD-04, TD-10)
- [ ] Next 15 running in prod; 5 migrated pages render correctly
- [ ] Retrospective written, ARCHITECTURE_MAP refreshed

## Estimated Size

~½ sprint for Cloudflare + auth restoration (Phases 0–2), ½ sprint for the rest (Phases 3–5). Total ~1 working sprint. Can split if context gets tight: merge Phase 0–2 first, ship, then Phase 3–5 in a follow-on.
