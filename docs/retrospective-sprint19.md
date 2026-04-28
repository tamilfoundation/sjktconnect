# Retrospective — Sprint 19: Edit Page Tabs

**Date**: 2026-04-28 (single session)
**Goal**: Redesign `/school/[moe_code]/edit` as a 5-tab layout (Core / Contact / Leaders / Support / Images). Remove the Confirm Data flow entirely (button + endpoint + model fields + admin verification dashboard) — MOE data is the source of truth, nothing for school admins to confirm. GPS edit gated to SUPERADMIN.

---

## What Was Built

### Stitch prototype (mandatory before code, per CLAUDE.md rule)
- Project `10588652759232271161`, screen `9d4cd7350e2648f9a0be8321f295df11`. Academy Arc design system with primary `#2c3e50` + secondary `#3498db`. User-approved before any code was written.

### Backend (commit before frontend)
- **Migration `schools/0010_drop_last_verified_and_verified_by.py`** — drops both columns from the `schools_school` Postgres table. Applied on prod via Cloud Run container-start hook on deploy (revision `sjktconnect-api-00110-r6l`).
- **`schools/api/views.py`** — entire `SchoolConfirmView` class deleted; `SchoolEditView.put()` no longer sets `last_verified` / `verified_by`.
- **`schools/api/urls.py`** — `SchoolConfirmView` import + `/schools/<moe>/confirm/` URL deleted.
- **`schools/api/serializers.py`** — both fields removed from `SchoolDetailSerializer` and `SchoolEditSerializer`. `SchoolEditSerializer` then **extended** with read-only MOE metadata (`ppd`, `grade`, `assistance_type`, `skm_eligible`, `location_type`, `gps_lat`, `gps_lng`, `gps_verified`, `claimed_at`) and a nested `leaders` array so the tabbed page renders from a single API call.
- **`schools/views.py`** + **`schools/urls.py`** + **`templates/schools/verification_dashboard.html`** + the `schools.urls` include in `sjktconnect/urls.py` + the "Verification" nav link in `templates/base.html` — Sprint 1.7 admin Verification Dashboard removed entirely.
- **`schools/tests/test_dashboard.py`** deleted; `SchoolConfirmViewTest` (6 tests) + `test_put_sets_verification_timestamp` removed from `test_edit_api.py`.

### Frontend
- **`frontend/components/edit_tabs/`** (new directory):
  - `TabBar.tsx` — pill-button nav with `aria-selected`, URL-hash persistence (deep-link + browser back works).
  - `FieldRow.tsx` — `ReadOnlyField` (muted bg, lock icon, optional badge) + `EditableField` (clean white input, blue focus, optional `fullWidth`) shared primitives.
  - `CoreTab.tsx`, `ContactTab.tsx`, `LeadersTab.tsx`, `SupportTab.tsx`, `ImagesTab.tsx` — one component per tab.
- **`frontend/components/SchoolEditForm.tsx`** rewritten as orchestrator. Delegates field rendering to the per-tab components; owns the formData state + save flow + tab id (synced to URL hash).
- **`frontend/app/[locale]/school/[moe_code]/edit/page.tsx`** — passes `isSuperAdmin` to the form; new "Claimed by HM since {date}" badge in the header when `claimed_at` is set.
- **`frontend/lib/types.ts`** — `SchoolEditData` extended with the new read-only MOE fields + a `SchoolLeaderData` interface + a `leaders` array. `SchoolConfirmResponse` interface deleted.
- **`frontend/lib/api.ts`** — `confirmSchool()` helper deleted (with a comment marking the removal).
- **`messages/en.json` + `ta.json` + `ms.json`** — all three updated with tab labels, section captions, GPS notice, "Claimed by HM since {date}" badge format, "Editing leaders coming soon" notice, and the field labels for newly-surfaced read-only MOE fields.

### Tests
- **`__tests__/components/SchoolEditForm.test.tsx`** rewritten — 10 new tests replacing 11 old ones: tab navigation (5 tabs render, Core active by default, click swaps content), no-Confirm regression, leaders read-only listing + "coming soon" notice, images tab launchpad link, GPS gating both ways (read-only for non-admins, editable for SUPERADMIN), save filter excludes GPS for non-admins.
- **`__tests__/lib/api-edit.test.ts`** — `confirmSchool` describe block deleted (test count -2).
- Test isolation fix: `beforeEach` resets `window.location.hash` because the form persists tab state via `history.replaceState`, which leaks between tests in the same jsdom instance.
- Final tally: **1174 backend + 288 frontend tests** pass.

### Deployed
- Backend: `sjktconnect-api-00109-hjm` → **`sjktconnect-api-00110-r6l`** (migration applied via container-start hook).
- Frontend: `sjktconnect-web-00105-vhx` → **`sjktconnect-web-00106-dd6`**.

---

## What Went Well

- **Stitch-first paid off again.** Sprint 15 retro called this out as a pattern after the visual-regression deploy storm; Sprint 19 honoured it from the start. ~10 min of prototype + 1 user approval prevented an unknowable number of "iterate the layout on prod" deploys.
- **Backend cleanup is naturally Sprint-shaped.** Removing Confirm Data + verified fields + verification dashboard touched 9 files but each touch was small and testable. 1174 backend tests pass after dropping ~10 obsolete ones — a clean diff.
- **Reusing `SchoolDetailSerializer`'s leaders pattern in `SchoolEditSerializer` was 5 lines.** Single endpoint serves both detail and edit pages; no second API call from the edit page.
- **The Stitch screen captured the visual hierarchy precisely** — read-only Identity section with muted background + lock icons vs editable details with clean white inputs + blue focus. The `FieldRow.tsx` primitives implement this directly with no design re-interpretation.
- **`useTranslations` mock auto-loads from `messages/en.json`** so the test suite picks up new translation keys without any fixture wiring. Just kept adding translations + renamed labels in code; tests stayed green.

---

## What Went Wrong

### 1. `window.location.hash` leak between tests (caught in test, not prod)
The new tabbed form persists active tab in the URL hash via `history.replaceState`. In jsdom, `window.location` is shared across tests in the same module, so test #5 (Leaders tab) left `#leaders` in the URL — test #9 (GPS gating, default tab = Core) then started on Leaders and couldn't find the Tamil-name input.
- **Root cause**: jsdom's window is module-scoped, not test-scoped. URL hash isn't part of the auto-cleanup that `@testing-library/react` does in `afterEach`.
- **System change**: lessons.md gets a one-liner — any component that writes to `window.location.hash` (or any other window-level state) needs a `beforeEach` reset in its test file. Not just `mockClear()` for jest mocks.

### 2. The verification dashboard had a nav link in `base.html` I almost missed
After deleting `schools/urls.py`, the full backend test suite blew up with 25 failures — every Django template render was crashing because `templates/base.html` had `{% url 'schools:verification-dashboard' %}` referring to the now-removed namespace.
- **Root cause**: deleted the URL conf without grepping templates for the namespace. The local schools-only test pass (203 passed) didn't catch it because those tests don't render the template chrome.
- **System change**: when removing a URL or app-level URL include, **always grep `templates/` for the namespace before claiming the cleanup is complete**. Add to lessons.md.

### 3. `last_verified` was in *two* serializers, not one
Initial pass removed `last_verified` from `SchoolEditSerializer` only — `SchoolDetailSerializer` (line 161) still had it. Caught by the literal `grep -rnE "last_verified" --include="*.py"` walk before the migration was generated. Would have been a confusing AttributeError on the public school detail page after the migration applied.
- **Root cause**: I trusted the first finding instead of grepping exhaustively before editing.
- **System change**: when dropping a model field, the cleanup pattern is `grep -rnE "fieldname" --include="*.py"` — not "find the obvious serializer and edit it." Already a Sprint 15 lesson ("half-applied fallback patterns are worse than no fallback") — Sprint 19 adds a second instance of the same class of mistake.

### 4. Leaders tab shipped read-only — feature gap
The Stitch prompt asked for "leader sub-rows" with inline edit. The Leaders tab in this sprint shows the existing 4 rows but **cannot edit them** — that needs new permission-scoped backend endpoints (POST/PATCH/DELETE on `SchoolLeader` with school-admin gating) which is its own ~1-hour scope.
- **Root cause**: Sprint 19's "one coherent deliverable" is the tab structure. Adding Leader CRUD inflates the sprint scope and breaks the deploy pattern (backend would need its own deploy with new endpoints + permissions tests).
- **System change**: amber notice on the Leaders tab tells school admins to email feedback@tamilschool.org for now. Logged for a future sprint as "Sprint 20: Leader CRUD" or similar. No tech-debt entry — this is feature-gap scope, not debt.

---

## Design Decisions

Three worth recording in `docs/decisions.md`:

1. **5-tab layout over collapsible sections or a multi-step wizard.** Tabs are scannable, tab-switching is cheap, and deep-linking via URL hash is trivial. Collapsible sections require accordion state management AND don't support deep links well; wizards imply a sequential flow that doesn't apply here (school admins typically want to edit one specific thing).
2. **Single endpoint serves both detail and edit pages.** `SchoolEditSerializer` was extended with read-only MOE metadata + leaders rather than fetching `SchoolDetailSerializer` separately. Pros: one round trip, no two-call coordination. Cons: the edit serializer is now 80% of the detail serializer (duplication risk). Trade-off accepted — they may diverge later, at which point the duplication becomes intentional.
3. **GPS edit gated to SUPERADMIN, not "school admin if claimed."** Sprint 5.4 batch-verified 519 school pins via Google Places. A school admin overriding their pin to a wrong value would silently break the map. SUPERADMIN-only edit assumes that any GPS correction goes through a human-reviewed channel.

---

## Numbers

| Metric | Sprint start | Sprint end | Δ |
|---|---|---|---|
| Backend tests (passing) | 1184 | **1174** | -10 (removed Confirm + dashboard tests) |
| Frontend tests (passing) | 289 | **288** | -1 net (removed confirmSchool block; SchoolEditForm test rewritten with 10 new tests replacing 11 old ones) |
| Files touched | — | 25 | — |
| New components | — | 7 (TabBar, FieldRow, 5 tabs) | — |
| Production revisions (frontend) | web-00105-vhx | web-00106-dd6 | +1 |
| Production revisions (backend) | api-00109-hjm | **api-00110-r6l** | +1 |
| Open tech debt | 1 (TD-12) | 1 (TD-12, unchanged) | 0 |

**Wall-clock time**: ~3 hours from sprint-start to sprint-close. Well within the 4-5 hour estimate.

**Pending follow-up** (no scheduled sprint): Leader inline CRUD. Needs new backend endpoints (POST/PATCH/DELETE `/api/v1/schools/<moe>/leaders/<id>/`), school-admin gating via `IsPhotoApprover`-style permission, and a richer Leaders tab UI. Logged as future-work.
