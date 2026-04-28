# Retrospective — Sprint 20: Leader Inline CRUD

**Date**: 2026-04-28 evening (single ~3-hour session immediately after Sprint 19 close)
**Goal**: Replace Sprint 19's read-only LeadersTab with full inline CRUD. School admins maintain the headmaster / board chairman / PTA chairman / alumni chairman records themselves — these change yearly and only the school knows the details.

---

## What Was Built

### Backend (commit boundary 1)
1. **`SchoolLeaderAdminSerializer`** in `schools/api/serializers.py` — admin-shape (id + role + role_display + name + phone + email). Role immutable on PATCH (overrode `update()` to pop role from validated_data).
2. **`POST /api/v1/schools/<moe_code>/leaders/`** (`school_leader_create_view`) — creates a SchoolLeader. Returns 201 with the full admin shape. Returns **409 `slot_taken`** if the school already has an active leader for that role (delete the existing first; the DB constraint would catch it but a friendly 409 beats a generic 500).
3. **`PATCH/DELETE /api/v1/schools/<moe_code>/leaders/<leader_id>/`** (`school_leader_detail_view`) — update or soft-delete. DELETE sets `is_active=False`; the model's unique constraint is conditional on `is_active=True` so delete-then-recreate-same-role works correctly.
4. **`_can_edit_school_leaders(profile, school_pk)`** permission helper. Mirrors `community._is_photo_approver`: SUPERADMIN OR bound admin of THIS school. **MODERATOR is NOT special-cased** — leadership is school-internal, not platform moderation.
5. **`_resolve_school_or_404(moe_code)`** helper — drops the duplication between create/detail views.
6. **URL routes** in `schools/api/urls.py`.
7. **`SchoolEditSerializer.get_leaders()`** switched from public `SchoolLeaderSerializer` to admin `SchoolLeaderAdminSerializer`. The endpoint is gated by `IsProfileAuthenticated` AND the page-level role check, so private fields (phone, email) are safe to expose. Single round-trip serves the entire tabbed edit page.
8. **17 new backend tests** in `schools/tests/test_leader_crud_api.py`:
   - **6 permission matrix tests** — anonymous, regular user, MODERATOR, admin-of-different-school, admin-of-this-school, SUPERADMIN.
   - **11 behaviour tests** — happy path with phone+email, 409 slot_taken, 400 invalid role, 400 missing name, 404 unknown school, PATCH name/phone/email, role-immutable-on-PATCH, 204 soft-delete, delete-then-recreate-same-role, 404 unknown leader, 404 leader-belongs-to-different-school.
9. Schools+accounts test count: 203 → **220** (+17). Full backend suite: 1174 → **1191** (delta matches).

### Frontend (same commit)
10. **`frontend/components/edit_tabs/LeadersTab.tsx`** rewritten as inline CRUD orchestrator. Fixed `ROLE_ORDER` array drives slot rendering. Per-slot state: `{id?, name, phone, email, removed, freshlyAdded}`.
11. **Slot UX**: existing leader → editable row (name + phone + email + Remove); empty role → "+ Add {role}" button that swaps in an empty editor.
12. **Single Save button** at tab footer, disabled when no pending changes (computed via `computePendingChanges` which diffs the current slot state against `initialLeaders`).
13. **Save flow**: sequential. Deletes commit before creates so the unique-active-role constraint doesn't trip on a delete-then-recreate-same-role flow within one save.
14. **Soft-delete UX shortcut**: blanking the name on an existing leader = treated as delete. Reduces clicks for the common "I made a typo, let me start over" case.
15. **`createSchoolLeader` / `updateSchoolLeader` / `deleteSchoolLeader`** helpers + `LeaderRole` type + `LeaderUpsertPayload` interface in `frontend/lib/api.ts`.
16. **`SchoolLeaderAdminData`** type in `frontend/lib/types.ts`. `SchoolEditData.leaders` retyped from public to admin.
17. **`SchoolEditForm.tsx`** wires the new LeadersTab signature (moeCode + initialLeaders + onLeadersChange callback to lift updates back to the orchestrator).
18. **Translations en/ta/ms** updated — replaced `leadersComingSoon` with `leadersIntro`; added `addLeader` (with `{role}` interpolation), `leaderName/Phone/Email/Remove/RemoveConfirm`, 4 role labels, `leadersSlotTaken`, `leadersSaving/Saved/FailedSave`. The `noLeadersYet` copy updated to point at the + Add buttons.

### Frontend tests
19. **`__tests__/components/LeadersTab.test.tsx`** — 8 new tests: 4-slot rendering, Save disabled at rest, edit-existing-name → updateSchoolLeader, click +Add then save → createSchoolLeader, click +Add without name → Save stays disabled, Remove + confirm → deleteSchoolLeader, backend `role_taken` → friendly slot-taken message, blank-name on existing → treated as delete.
20. **`__tests__/components/SchoolEditForm.test.tsx`** updated — replaced the 1 read-only "coming soon" assertion from Sprint 19 with 2 new tests confirming the editable layout (existing leader appears in input, "+ Add" buttons appear for empty roles).
21. Frontend test count: 288 → **297** (+9 net).

### Deployed
- Backend: `sjktconnect-api-00110-r6l` → **`sjktconnect-api-00111-mrq`**.
- Frontend: `sjktconnect-web-00106-dd6` → **`sjktconnect-web-00107-wd9`**.

---

## What Went Well

- **The IsPhotoApprover permission pattern was reusable as-is.** I copied the `_can_edit_school_leaders` helper structure from `community._is_photo_approver` (Sprint 14) verbatim — same SUPERADMIN-OR-bound-admin logic, same MODERATOR-explicitly-excluded comment. ~5 lines of code, identical semantics.
- **The conditional unique constraint on `(school, role) WHERE is_active=True` was already there** from the original SchoolLeader model (Sprint 3.1). I didn't have to migrate. Soft-delete + recreate-same-role works correctly with no extra logic.
- **The Sprint 16 `_can_moderate_or_owns_school` helper extraction precedent paid off.** Sprint 20's helper for leader edit fits the same mental model — view-level permission via a small typed function, not a full DRF permission class. Easier to read at the call site.
- **`SchoolEditSerializer.get_leaders()` switch from public to admin shape is two lines.** Single endpoint serves the entire tabbed edit page now (Core read-only MOE fields + Editable details + Leaders with private contact details + Support + Images metadata) — one round trip.
- **Sequential save flow is correct AND simple.** I considered parallel `Promise.all` for the create/update/delete bursts, but the constraint that "deletes must commit before recreates of the same role" makes parallel error-prone. Sequential adds maybe 200ms wall-time for 4 edits — negligible vs the round-trip cost itself.
- **Translations across en/ta/ms stayed consistent.** Added all keys to all three files in one pass; the test mock auto-loads English so tests stayed green without separate fixture wiring.

---

## What Went Wrong

### 1. First two LeadersTab tests assumed `Save` would show "No changes" on click
I wrote the LeadersTab with `disabled={saving || !hasChanges}` — correct UX (disabled buttons signal "nothing to do"). But my tests assumed the button was enabled and clicking it would render an inline error. Both tests timed out looking for `/No changes/i` text that was never shown.
- **Root cause**: I wrote the test expectations from memory of the SchoolEditForm pattern, which DOES show "No changes" inline (because its Save button is enabled at all times). LeadersTab is stricter — disabled-when-empty.
- **Fix applied**: rewrote the tests to assert `toBeDisabled()` instead of looking for an error string. Both tests passed on the second try.
- **System change**: when writing component tests, the assertion should match the COMPONENT's actual behaviour as documented in its render logic, not the assumed convention from a sibling component. Sprint 17 lesson "test against actual render output, not assumed convention" applies — but it's a testing-discipline lesson rather than a system fix.

### 2. The `gcloud` auth expired again mid-deploy
Both deploys (backend + frontend) aborted on auth ("There was a problem refreshing your current auth tokens: Reauthentication failed"). Same issue as Sprint 18 + Sprint 19. User had to `gcloud auth login` interactively again; deploys retried and landed.
- **Root cause**: `gcloud`'s auth refresh requires an interactive prompt that the Bash tool can't satisfy. Token TTL appears to be ~1-2 hours. Sprints 18, 19, and 20 have all hit this on the deploy step.
- **System change**: documented in lessons.md from Sprint 17 already; no new entry needed. The accepted workaround is "user runs `! gcloud auth login admin@tamilfoundation.org` when asked." A more permanent fix would require a service account with longer-lived credentials, but that's its own infra-shaped scope and adds permission-leak surface.

### 3. The Sprint 19 retro flagged this as "Future work: Sprint 20 (or backlog)" — and we did it the same evening
Not a problem per se, but worth noting that "future work" items from one sprint can become next-sprint items on the same day if the user prioritises them. The retro entry "Leaders tab shipping read-only as a feature gap" was logged at 2026-04-28 ~6pm; Sprint 20 closed at ~10pm. Useful pattern: future-work items aren't deferred forever, they're explicitly visible in the retro and can be picked up immediately.

---

## Design Decisions

Two worth recording in `docs/decisions.md`:

1. **Role is immutable on PATCH** — to change a leader's role, delete and recreate. Alternative: allow role swap via PATCH but enforce uniqueness. Chose immutability because (a) "the same person held two different roles over time" is an anti-pattern in our model — they're separate role records with separate `name`/`phone`/`email`; (b) PATCH mutating role would silently change which "slot" a leader occupies in the tabbed UI which is confusing; (c) one less thing for the validator to handle. Trade-off: a typo in the role at create time costs one delete + one create instead of one PATCH. Acceptable.

2. **Sequential save flush, not parallel** — when the LeadersTab saves N pending changes, we await each one in turn rather than `Promise.all`. Pros: deletes always commit before any create that depends on the freed slot; error handling is one-at-a-time and surfaces the right slot's error message; total wall time = N × ~200ms which is fine for N ≤ 4. Cons: technically slower than parallel for the all-create case. Trade-off accepted — 4 leaders max means worst case ~800ms which the user perceives as a single button-click.

---

## Numbers

| Metric | Sprint start | Sprint end | Δ |
|---|---|---|---|
| Backend tests (passing) | 1174 | **1191** | +17 (all in test_leader_crud_api.py) |
| Frontend tests (passing) | 288 | **297** | +9 net (8 new LeadersTab + 2 SchoolEditForm updates -1 removed read-only assertion) |
| Files touched | — | 13 | — |
| New backend endpoints | — | 3 (POST + PATCH + DELETE) | — |
| Production revisions (frontend) | web-00106-dd6 | **web-00107-wd9** | +1 |
| Production revisions (backend) | api-00110-r6l | **api-00111-mrq** | +1 |
| Open tech debt | 1 (TD-12) | 1 (TD-12, unchanged) | 0 |

**Wall-clock time**: ~3 hours from sprint-start to sprint-close (matches the original estimate).

**No outstanding follow-up work from Sprint 20.** The Sprint 19 future-work item "Leader inline CRUD" is closed by this sprint.
