# Suggestion Workflow — Design Document

**Date:** 2026-03-11
**Status:** Approved
**Sprint:** 8.2
**Prerequisite:** Sprint 8.1 (Auth + Roles Foundation) — complete

---

## Problem

School data goes stale — phone numbers change, headmasters rotate, photos get outdated. Only Tamil Foundation staff and school reps (via magic link) can edit. The broader community (donors, members, public) has no way to contribute corrections, photos, or notes.

## Solution

Any signed-in user can suggest data corrections, upload photos, or leave notes for any school (except their own admin_school). Moderators and school admins review and approve suggestions. Approved contributions earn points.

---

## Data Model

### Suggestion

```
Suggestion
├── school (FK → School)
├── user (FK → UserProfile)
├── type: DATA_CORRECTION | PHOTO_UPLOAD | NOTE
├── status: PENDING | APPROVED | REJECTED
├── field_name (CharField, blank) — e.g. "phone", "address", "leadership"
├── current_value (TextField, blank) — snapshot of existing value at time of suggestion
├── suggested_value (TextField, blank) — proposed new value
├── note (TextField, blank) — free-text for NOTE type or explanation
├── image (BinaryField, blank) — for PHOTO_UPLOAD type
├── reviewed_by (FK → UserProfile, nullable)
├── review_note (TextField, blank) — moderator's reason for rejection
├── points_awarded (PositiveIntegerField, default 0)
├── created_at, updated_at
```

### SchoolImage changes

- Add `position` (PositiveIntegerField, default 0) — admin-controlled display order
- Add `uploaded_by` (FK → UserProfile, nullable) — track contributor

### Suggestible fields

**Yes:** phone, fax, address, postcode, city, GPS, grade, bank details, leadership (name/role), school images, free-text notes.

**No (system/MOE data):** enrolment, preschool enrolment, special ed enrolment, email address.

**Extensible:** new fields added to School in future sprints automatically become suggestible by adding to the allowed-fields list.

---

## API Endpoints

```
POST   /api/v1/schools/<moe_code>/suggestions/     — create suggestion
GET    /api/v1/schools/<moe_code>/suggestions/     — list suggestions for a school
GET    /api/v1/suggestions/pending/                 — moderation queue
POST   /api/v1/suggestions/<id>/approve/           — approve + apply + award points
POST   /api/v1/suggestions/<id>/reject/            — reject with reason

GET    /api/v1/schools/<moe_code>/images/           — list images with position
PUT    /api/v1/schools/<moe_code>/images/reorder/   — update positions
DELETE /api/v1/schools/<moe_code>/images/<id>/      — delete image
```

### Permissions

| Action | USER | MODERATOR | School ADMIN (own school) | SUPERADMIN |
|--------|------|-----------|--------------------------|------------|
| Create suggestion | Yes (not own school) | Yes (not own school) | No (edit directly) | Yes |
| View own suggestions | Yes | Yes | Yes | Yes |
| View moderation queue | No | Yes | Own school only | Yes |
| Approve/reject | No | Yes (any school) | Own school only | Yes |
| Manage images | No | No | Own school only | Yes |

### Points

| Action | Points |
|--------|--------|
| Photo upload approved | 3 |
| Data correction approved | 2 |
| Free-text note approved | 1 |
| Suggestion to own admin_school | 0 (not allowed) |

---

## Approval Flow

1. User submits suggestion → status=PENDING
2. Moderator or school admin reviews → APPROVED or REJECTED (with reason)
3. On APPROVED:
   - **DATA_CORRECTION:** field value updated on School model automatically
   - **PHOTO_UPLOAD:** image added to SchoolImage, position after existing images
   - **NOTE:** stored as-is, moderator acts manually
   - Points awarded to submitter
4. On REJECTED: user sees rejection reason on profile page

---

## Frontend

### All signed-in users
- **Suggest button** on school page — form with field picker, value input, photo upload, or free-text
- **My suggestions** on profile page — list with status badges (pending/approved/rejected)

### Moderators
- **Moderation queue** on dashboard (`/dashboard/suggestions`) — pending suggestions, filters, approve/reject, side-by-side current vs suggested

### School admins
- **Manage images** on dashboard — reorder (drag-and-drop or arrows), delete, upload new
- **Approve/reject** suggestions for own school (filtered queue)

### Public
- No suggestion visibility — internal workflow only

---

## Image Constraints

- Max **3 images per suggestion**
- Max **10 images per school** total (harvested + community)
- Display order: school admin photos first → community (newest first) → harvested last
- School admin can reorder, delete, replace any image on their school

---

## Future Extensions

- School needs/grants fields (suggestible once added to model)
- Trust threshold: auto-approve for high-point users
- Moderator promotion at configurable points threshold
