# Retrospective — Sprint 12: User Management UI

**Date**: 2026-04-24 (single session)
**Goal**: SUPERADMIN-only `/dashboard/users` for managing UserProfiles + self-service profile enhancements. First sprint of the 5-sprint roadmap approved earlier the same day.

---

## What Was Built

### Backend (accounts/api)
1. `AdminUserListView` — paginated SUPERADMIN-only list at `GET /api/v1/auth/admin/users/`. Filters: `role`, `has_admin_school`, `is_active`, `search` (matches display_name + email + moe_code + school short_name).
2. `AdminUserDetailView` — PATCH updates `role` / `admin_school` (by moe_code or null) / `is_active`. DELETE does soft delete.
3. Assigning a school to user B automatically unassigns user A from the same school (one school, one admin).
4. Self-demotion safety checks: SUPERADMIN cannot change own role away from SUPERADMIN, cannot deactivate own account via PATCH or DELETE.
5. `MeView.patch` — self-service display_name update. Only the one field is exposed; other fields ignored at serializer level.
6. New serializers: `UserProfileUpdateSerializer`, `UserProfileAdminListSerializer`, `UserProfileAdminUpdateSerializer`.
7. 30 new tests in `accounts/tests/test_admin_users.py` — permission matrix (4 roles × 4 operations), filter combinations, self-demotion in both directions, display-name validation, school reassignment side-effects.

### Frontend
8. `/dashboard/users` page — client-side-rendered; fetches `/me` first to gate SUPERADMIN before loading the list; filter controls + table; live refresh after mutations.
9. `UserManagementTable` — per-row actions (Role modal / School modal / Deactivate toggle); self-row has Role + Deactivate disabled via `isSelf` prop.
10. `RoleChangeModal` — radio buttons for the 3 roles.
11. `SchoolAssignModal` — searchable school picker using the existing `searchEntities()` API; inline unassign affordance.
12. `UserMenu` — "User Management" link visible only for `role === "SUPERADMIN"`.
13. `/profile` — editable display name (inline edit + save/cancel + error surfacing); removed broken `/claim` CTA (magic-link era, deleted in Sprint 11a Phase 3), replaced with `noSchoolHint` text explaining auto-claim via `@moe.edu.my` sign-in.
14. `lib/api.ts` — new functions: `fetchAdminUsers`, `updateAdminUser`, `deactivateAdminUser`, `updateMyProfile`.
15. i18n: en/ta/ms `userManagement.*` section + `auth.*` additions (edit / save / saving / cancel / userManagement / noSchoolHint).

### Production incidental discoveries
- UserProfile count on prod has grown from 2 to 5 since Sprint 11a close — three community sign-ups (khathijah123mohamedrasul, deneshkumaar@mitra.gov.my, rinishhaa@tamilfoundation.org) happened without any outreach. Auto-claim mechanism has already been exercised for real.

### Tests
- Backend: 1076 → 1106 (+30). Frontend: 258 unchanged.

---

## What Went Well

- **Sprint size discipline worked.** 13 files touched, inside the 20-file solo budget. One session, one coherent deliverable. No "split midway" anti-pattern.
- **Existing foundations carried the sprint.** `IsSuperAdmin` permission class (Sprint 8.1), UserProfile model (Sprint 8.1), `searchEntities()` API (Sprint 1.2). No new plumbing needed — this was mostly composition.
- **Self-demotion safety tested deliberately** — one lesson from the sprint plan that actually landed in the test file with 3 dedicated test cases (role demote, is_active deactivate, DELETE self).
- **Community sign-ups appeared during the sprint itself.** Proves the Sprint 11a auto-claim + Cloudflare work is being used. Gave immediate real data to populate the new management UI during smoke-testing.

---

## What Went Wrong

### 1. Duplicate `fetchMySuggestions` function

**What happened**: Added a new `fetchMySuggestions` to `lib/api.ts` for the new `/me/suggestions/` endpoint. Build failed — `fetchMySuggestions` was already defined at line 308, pointing at the existing community app `/suggestions/mine/` endpoint. Had to remove both my duplicate and the backend endpoint I'd just written.

**Why it happened**: Didn't grep `lib/api.ts` for existing functions before adding a new one with a name matching a well-established domain pattern ("my suggestions"). The plan doc mentioned `My Suggestions list` on the profile page; I interpreted that as "new endpoint" without checking whether it already existed.

**System change to prevent recurrence**: Added to `docs/lessons.md`: "Before adding a new named function/endpoint to a file that already has similar functionality, grep the file for the concept (not just the exact name) — `grep -E 'mySuggest|MySuggest|/me/suggest|/suggestions/mine'` would have caught this. Especially applies to composition sprints where existing surface is being extended."

### 2. TD-01 regressed during Sprint 12 deploy

**What happened**: Sign-in started failing with `InvalidCheck: state value could not be parsed` after the Sprint 12 frontend deploy. Sign-in was known to work after Sprint 11a Phase 4 (Next 16 upgrade). The Sprint 12 deploy, which didn't touch `auth.ts`, somehow regressed the OAuth state cookie round-trip.

**Why it happened**: Most likely: a Docker rebuild during `gcloud run deploy --source .` resolved npm lockfile differently or picked up a different transitive version of `@auth/core`. This combined with Next 16 + `next-auth@5.0.0-beta.30` produced a real Auth.js bug that I couldn't root-cause in-session. Two attempted fixes (adding `AUTH_SECRET`/`AUTH_URL`, then removing legacy `NEXTAUTH_*`) didn't help.

**System change to prevent recurrence**: Added to `docs/lessons.md`: "Beta-version dependencies are acceptable but compat-fragile — lockfile drift from a rebuild can surface previously-hidden regressions. For any beta-version lib (e.g. `next-auth@5.0.0-beta.*`), verify the critical flow (sign-in, auth callback, webhook) after every container rebuild, not just after code changes. Consider pinning lockfile more aggressively (exact transitive pins) for auth-critical deps."

Accepted this debt pragmatically: reverted `checks: []` as Sprint 11a Phase 2 did, re-opened TD-01 with detailed hypotheses for Sprint 16. Shipping features on top of a beta lib is always this fragile.

### 3. Sign-in debug loop cost ~1 hour

**What happened**: Diagnosing the sign-in regression took 4 separate deploys (`00090-5mp`, `00091-8bl`, `00092-7ts`) and three env-var configurations before settling on the `checks: []` workaround. Each deploy cost 3–5 minutes.

**Why it happened**: No explicit "give up and rollback to the working config" budget. I kept trying incremental fixes hoping one would land, rather than time-boxing diagnosis.

**System change to prevent recurrence**: For any auth regression on prod, time-box diagnosis to 30 minutes; beyond that, rollback to the last known-good config immediately. Deeper diagnosis belongs in a dedicated debugging sprint with local repro, not ad-hoc on prod deploys.

---

## Design Decisions

1. **Separate `UserProfileAdminListSerializer` + `UserProfileAdminUpdateSerializer` over re-using `UserProfileSerializer`** — list serializer is read-only with more fields (created_at, updated_at), update serializer has a narrow whitelist (role/admin_school/is_active). Prevents accidental mass-assignment of `points` or `google_id` via the admin endpoint.

2. **Assign-school auto-unassigns the previous admin** — chose "one school, one admin" over allowing multiple. Keeps semantics clear; covered by a dedicated test (`test_patch_school_reassignment_strips_old_admin`).

3. **Client-side role gate on `/dashboard/users`** — the page fetches `/me` first and redirects if not SUPERADMIN. Backend returns 403 regardless, so the client-side gate is UX (not security), but preserves clean URLs for non-admins.

4. **`checks: []` reinstated as pragmatic unblock** — over continuing to debug on prod. Documented the exact rollback reasoning in `auth.ts` comment + TD-01 re-opened in register + queued for Sprint 16 proper investigation.

---

## Numbers

| Metric | Sprint Start | Sprint Close |
|---|---|---|
| Backend tests | 1076 | 1106 (+30) |
| Frontend tests | 258 | 258 (no new component tests — self-correction: should have added at least a few) |
| UserProfile rows in prod | 2 | 5 (3 community sign-ups during sprint) |
| Files touched | — | 13 (inside 20 budget) |
| Cloud Run revisions shipped | api-00097, web-00088 | api-00098, web-00092 (4 frontend revs during sign-in debug) |
| Tech debt items resolved | 0 | 0 |
| Tech debt items re-opened | — | 1 (TD-01) |
| Open branches | 0 | 0 (feat/sprint-12-user-management merged at close) |

## Next Sprint

**Sprint 13 — Image Storage Migration** is queued. Pre-sprint tasks for user: create Supabase Storage bucket `school-images`, confirm Places API re-harvest budget. Plan ref: `docs/plans/2026-04-22-image-library-sprint-plan.md` Phase 1.
