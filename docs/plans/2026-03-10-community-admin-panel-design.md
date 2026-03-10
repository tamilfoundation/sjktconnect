# Community Admin Panel — Design Document

**Date:** 2026-03-10
**Status:** Approved
**Goal:** Community-driven school data maintenance with role-based access, building towards reviews, points, and photo uploads.

---

## Problem

The 528 SJK(T) school database needs continuous updating — phone numbers change, headmasters rotate, photos get outdated. Currently only Tamil Foundation staff and school reps (via magic link) can edit data. There's no mechanism for the broader community to contribute, verify, or enrich school information.

## Solution

A four-tier role system integrated into the existing Next.js frontend, where community users can suggest changes and earn points, school admins manage their own school, moderators review contributions, and TF superadmins oversee everything.

---

## Architecture

### Auth: Two Paths, One Profile

**Google Sign-in (general public):**
1. User clicks "Sign in with Google" → NextAuth.js (Next.js 14 App Router)
2. Frontend sends Google token to Django → `POST /api/v1/auth/google/`
3. Backend verifies token, creates/updates `UserProfile`
4. Returns session → user logged in as role=USER

**Magic Link (school admin claiming):**
1. School rep requests magic link (existing @moe.edu.my flow, unchanged)
2. After verification, if signed in with Google → links accounts: sets `admin_school` on their `UserProfile`
3. If not signed in with Google → prompts to connect Google account
4. Magic link is a one-time ownership proof; Google sign-in is the daily auth method

### Data Model

```
UserProfile
├── user (OneToOne → Django User)
├── google_id (CharField, unique) — Google OAuth subject ID
├── display_name (CharField)
├── avatar_url (URLField)
├── role (CharField): SUPERADMIN | MODERATOR | USER (default: USER)
├── admin_school (FK → School, nullable, unique) — set via magic link claim
├── points (PositiveIntegerField, default 0)
├── is_active (BooleanField, default True)
├── created_at, updated_at
```

**Key constraints:**
- `admin_school` is unique — one user per school, one school per user
- `role` is global (SUPERADMIN, MODERATOR, USER). School admin is a relationship, not a role.
- A school admin is a USER (or MODERATOR) who also has `admin_school` set
- SUPERADMIN is set manually in Django admin by TF staff

**Backward compatibility:**
- Existing `SchoolContact` model stays (audit trail of magic link verifications)
- Existing `IsMagicLinkAuthenticated` permission stays for legacy endpoints
- New permission classes added alongside, not replacing

### Roles & Permissions

| Action | USER | MODERATOR | School ADMIN (own school) | SUPERADMIN |
|--------|------|-----------|--------------------------|------------|
| View school pages | Yes | Yes | Yes | Yes |
| Suggest data changes | Yes (+pts) | Yes (+pts) | — | Yes |
| Upload photos (other schools) | Needs approval | Direct | — | Direct |
| Upload photos (own school) | — | — | Direct | Direct |
| Edit own school data | — | — | Direct | Direct |
| Comment/review schools | Yes | Yes | Yes (not own) | Yes |
| Approve suggestions | No | Yes | Own school only | Yes |
| Approve flagged photos | No | Yes | Own school only | Yes |
| Promote users to moderator | No | No | No | Yes |
| Manage all schools | No | No | No | Yes |

### Points System (future sprint)

- Points earned only for contributions to **other** schools (not your own `admin_school`)
- Prevents gaming: a school admin editing their own school gains no points
- Point actions: suggest correction, upload photo (approved), verify data, write review
- At a configurable threshold (e.g. 100 points), user becomes **eligible** for moderator promotion
- Promotion is manual — superadmin approves, not automatic

### Reviews & Comments (future sprint)

- Any signed-in user can review/comment on a school (except their own `admin_school`)
- Automated spam detection on submit — clean reviews publish immediately, suspicious ones queued for moderation
- School admins can moderate reviews on their own school

### Photo Uploads (future sprint)

- School admins: direct upload to their own school
- Moderators: direct upload to any school
- Regular users: upload queued for approval
- Users with sufficient points: direct upload (threshold configurable)

---

## Sprint 1 Scope: Auth + Roles Foundation

**Backend:**
- `UserProfile` model with migration
- `POST /api/v1/auth/google/` — verify Google ID token, create/return profile
- `GET /api/v1/auth/me/` — updated to return UserProfile (role, points, admin_school)
- `POST /api/v1/auth/link-school/` — link magic-link-verified school to Google profile
- Permission classes: `IsAuthenticated` (has UserProfile), `IsModeratorOrAbove`, `IsSuperAdmin`, `IsSchoolAdmin`
- Tests for all endpoints and permissions

**Frontend:**
- NextAuth.js setup with Google provider
- Sign in / Sign out in header (Google avatar + dropdown menu)
- User profile page (`/profile`) — display name, avatar, role badge, points, admin school
- Role-aware navigation — conditional menu items based on role
- Admin panel shell (`/dashboard`) — gated by role, empty sections for future sprints

**Not in Sprint 1:**
- Points earning/spending
- Reviews/comments
- Photo uploads
- Suggestion workflow + moderation queue
- Spam detection
- Moderator promotion flow

---

## Tech Stack Additions

| Component | Technology | Why |
|-----------|-----------|-----|
| Google OAuth | NextAuth.js v5 | App Router native, well-maintained, no new GCP deps |
| Token verification | `google-auth-library` (backend) | Verify Google ID tokens server-side |
| Session | NextAuth.js JWT + Django session | Frontend session via NextAuth, backend via existing Django sessions |

---

## Future Sprints (ordered)

1. **Sprint 1:** Auth + Roles Foundation (this design)
2. **Sprint 2:** Suggestion Workflow — users suggest edits, moderators/admins approve, points awarded
3. **Sprint 3:** Reviews & Comments — per-school reviews, spam detection, moderation
4. **Sprint 4:** Photo Uploads — community photos, approval queue, direct upload for trusted users
5. **Sprint 5:** Moderator Promotion — points thresholds, nomination flow, superadmin approval
