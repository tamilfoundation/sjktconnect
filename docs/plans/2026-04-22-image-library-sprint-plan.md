# Image Library & Community Upload — Sprint Plan

**Date**: 2026-04-22
**Branch**: `feat/image-library` (originally one branch; split into Sprint 13/14/15/16 branches)
**Goal**: Move school images from volatile Google Places URLs into Supabase Storage, and add a community upload flow gated by SUPERADMIN / school admin approval.

## Status (as of 2026-04-26)

| Phase | Sprint | Status |
|---|---|---|
| Phase 1 — Storage Foundation | 13 | ✅ Done — see `docs/retrospective-sprint13.md` |
| Phase 2 — Upload & Moderation API | 14 | ✅ Done — see `docs/retrospective-sprint14.md` |
| Phase 3.3, 3.5, 3.6 — SuggestForm + queue UX | 14 | ✅ Done |
| Phase 3.1, 3.2, 3.4 — Lightbox + gallery + image manager polish | 15 | Queued |
| Phase 4 — Drop legacy `image_url` field | 16 | Queued |

## Context

Investigation on 2026-04-22 found every Google Places photo URL returning `HTTP 400 INVALID_ARGUMENT` — the photo resource IDs had been invalidated by Google. Only the `SATELLITE` source (Static Maps) still rendered. Storing URLs instead of bytes was the root cause; even after re-harvesting, the same class of failure will recur whenever Google rotates resource IDs.

## Design Decisions (agreed)

| # | Decision |
|---|---|
| 1 | Store image bytes in **Supabase Storage** (bucket `school-images`), not Google URLs |
| 2 | **Display policy**: max 5 visible on school page (1 hero + 4 thumbs); "View all N photos" button opens a lightbox modal with the full set |
| 3 | **Hard cap**: 20 APPROVED photos per school — no auto-archive |
| 4 | **Uploaders**: any authenticated user |
| 5 | **Approvers**: SUPERADMIN, or school admin of the specific school. MODERATOR role does NOT approve photos |
| 6 | When slots are full: approver must delete an existing photo to free a slot before approving a new one (API returns 409) |
| 7 | Satellite refresh on GPS change auto-replaces the existing SATELLITE row (same slot, same source) |
| 8 | Duplicate uploads (perceptual-hash match per user) rejected at submission time |
| 9 | No cap on PENDING queue size |
| 10 | Rate limit: 5 uploads / user / day, 20 / school / day |
| 11 | File constraints: ≤5 MB; JPEG/PNG/WebP; ≥640×400; EXIF stripped; auto-resized to 1600px longest edge |

## Ranking (display_score)

```
display_score =
  (is_pinned ? 1000 : 0)
+ source_weight   # OFFICIAL=100, COMMUNITY=50, PLACES=20, SATELLITE=10
+ (upvotes - downvotes) * 5   # phase 2
+ (uploaded < 90 days ? 10 : 0)
- reports_count * 20
```
Tie-break: `position ASC`, then `-created_at`. Satellite is always retained as a fallback if total < 5.

---

## Phase 1 — Storage Foundation (backend-only)

### 1.1 Supabase Storage + Django integration
- Create `school-images` bucket (public read, authenticated write)
- Add `django-storages[boto3]` dependency
- `settings.py`: `DEFAULT_FILE_STORAGE` + Supabase S3-compat credentials
- Cloud Run env vars: `SUPABASE_STORAGE_ACCESS_KEY`, `SUPABASE_STORAGE_SECRET_KEY`, `SUPABASE_STORAGE_BUCKET`, `SUPABASE_STORAGE_ENDPOINT`
- Spike first: verify S3 credentials work from Cloud Run before committing to django-storages

### 1.2 `SchoolImage` model extensions (migration 0003)
```python
image_file       ImageField(upload_to="schools/<moe_code>/")
status           CharField(choices=PENDING/APPROVED/REJECTED/ARCHIVED, default=APPROVED)
caption          CharField(max_length=200, blank=True)
rejected_reason  CharField(max_length=500, blank=True)
moderated_by     FK UserProfile, null
moderated_at     DateTimeField, null
is_pinned        BooleanField(default=False)
reports_count    PositiveIntegerField(default=0)
perceptual_hash  CharField(max_length=64, blank=True, db_index=True)
archived_at      DateTimeField, null
```
- Add `OFFICIAL` to `Source.choices`
- Keep legacy `image_url` nullable (removed in Phase 4)

### 1.3 `migrate_images_to_storage` management command
- Download bytes from each live `image_url` → upload to Supabase → populate `image_file`
- Idempotent, resumable, skips rows with `image_file` already set
- Logs failures; dead Places URLs skipped (re-harvest replaces them)

### 1.4 Hard cap enforcement
- Service-layer check on any `PENDING → APPROVED` transition: raise if school already has ≥20 APPROVED
- No DB CheckConstraint (cross-row not supported)

### 1.5 Update harvesters
- `harvest_places_images` + `harvest_satellite_image`: download bytes → upload to Supabase → save `image_file`
- Places: only insert up to `20 - existing_count` slots
- Satellite: delete old SATELLITE before insert (Decision #7)

### 1.6 One-off ops
- Run `harvest_school_images --source places` (refresh the 400s)
- Run `migrate_images_to_storage` (pull bytes into Supabase)

---

## Phase 2 — Upload & Moderation API

### 2.1 Upload endpoint
- `POST /api/v1/schools/<moe_code>/suggestions/photo/`
- Auth: `IsProfileAuthenticated`
- Multipart: `image`, `caption` (optional)
- Validation: size ≤5 MB, format in {JPEG, PNG, WebP}, dims ≥640×400
- Processing: strip EXIF, resize to max 1600px, compute pHash
- Dedup: reject 409 if same user has PENDING/APPROVED photo with matching hash on same school
- Throttle: 5/user/day, 20/school/day
- Creates `Suggestion(type=PHOTO_UPLOAD, status=PENDING)` + staged `SchoolImage(status=PENDING)`

### 2.2 Approve / reject
- `POST /api/v1/suggestions/<id>/approve/`
- `POST /api/v1/suggestions/<id>/reject/` (body: `reason`)
- New permission class `IsPhotoApprover`:
  ```
  allow if user.role == SUPERADMIN
  OR user.admin_school_id == suggestion.school_id
  ```
- Approve: check <20 APPROVED on school → else 409 "Photo slot full". Transition to APPROVED, stamp moderator, email uploader.
- Reject: transition to REJECTED, store reason, schedule 30-day purge, email uploader.

### 2.3 Delete (soft)
- `DELETE /api/v1/schools/<moe_code>/images/<id>/`
- Auth: `IsPhotoApprover`
- Sets `status=ARCHIVED`, `archived_at=now()`

### 2.4 Restore
- `POST /api/v1/schools/<moe_code>/images/<id>/restore/`
- Checks slot available, transitions ARCHIVED → APPROVED if within 30-day window

### 2.5 Report
- `POST /api/v1/images/<id>/report/`
- Any authenticated user; increments `reports_count`
- At 3+ reports: APPROVED → PENDING (re-moderation)

### 2.6 Purge job
- `purge_archived_images` management command
- Deletes Supabase Storage files + DB rows where `archived_at < now - 30 days`
- Cloud Run job + Cloud Scheduler: daily 3 AM MYT

---

## Phase 3 — Frontend

### 3.1 `SchoolPhotoGallery` rewrite
- Shows 1 hero + 4 thumbs (unchanged)
- If total > 5: overlay "View all N photos" button on hero
- Images ordered by backend-computed `display_score`

### 3.2 Lightbox modal
- `yet-another-react-lightbox` (~15 KB gzipped)
- Full-screen, swipe on mobile, arrow keys on desktop
- Per-photo: attribution, caption, upload date, report button

### 3.3 Upload UI
- Extend `SuggestForm` (`PHOTO_UPLOAD` already an option from Sprint 8.2)
- Add file picker + drag-drop + preview + client-side size/format validation

### 3.4 `/dashboard/images`
- Extend Sprint 8.2 admin view
- Add: pin/unpin toggle, caption editor, archived tab, restore button
- Visibility: school admins for their school only; SUPERADMIN for all

### 3.5 `/dashboard/suggestions` — photo approval
- Photo preview in review queue
- Approve/reject buttons; reject opens reason textarea
- Banner when school at 20/20: "Delete existing photo first"

### 3.6 Moderation queue UX polish (from 2026-04-22 E2E testing)
Feedback from first end-to-end moderation test — carry forward into Image Library sprint:
- **School name as clickable link**: in the queue card, `SJK(T) Ladang Sungai Raya` should link to `/school/<moe_code>` so moderators can open the profile in a new tab to verify context before approving. Currently plain text.
- **Photo preview in queue card**: for `PHOTO_UPLOAD` suggestions, render the image inline in the moderation card (not just the "Photo Upload" badge). Without seeing the photo, a moderator cannot make an informed approve/reject decision.
- **Delete approved image flow**: after a photo is approved, a moderator must have a discoverable way to remove it (e.g. a "Remove" button on each image in `/dashboard/images`, or a back-link from the school page's photo gallery for privileged users). Already covered by Phase 2.3 (soft delete API) + Phase 3.4 (`/dashboard/images` management UI) — make sure the UX is obvious.

---

## Phase 4 — Cleanup

- **4.1** Drop `image_url` field (migration 0004) — after 1 week of stable operation
- **4.2** Remove Google Maps photo-URL logic from frontend
- **4.3** Retire `harvest_school_images` from weekly cron; keep as manual command only

---

## Tests

- **Backend**: ~40 new tests — upload validation, hash dedup, cap enforcement, permission matrix (SUPERADMIN / school admin / MODERATOR / regular user), approve/reject/restore/purge, rate limits, satellite auto-replace
- **Frontend**: ~10 new tests — upload form, lightbox open/close, pin toggle, 20/20 warning banner

## Deployment Order

1. Merge backend → deploy (new endpoints, migration, Supabase bucket)
2. Run `harvest_school_images --source places` (refresh 400s)
3. Run `migrate_images_to_storage` (pull bytes into Supabase)
4. Deploy frontend (new gallery + lightbox + upload UI)
5. Enable purge scheduler
6. After ~1 week stable: drop `image_url` field (migration 0004)

## Risks

| Risk | Mitigation |
|---|---|
| Supabase free-tier egress (2 GB/month) | `next/image` caching; monitor after deploy |
| Places re-harvest cost (~US$14 for 403 calls at $0.035/call) | Verify within RM10 GCP monthly budget; spread over two cycles if needed |
| S3-compat credentials unproven from Cloud Run | Spike in Phase 1 before committing to django-storages |
| Moderation backlog if community uploads spike | 20/school/day rate limit caps inflow; MODERATOR role excluded from photo approval keeps queue accountable to school admins |

## Files Expected to Change (~25)

**Backend**
- `outreach/models.py` (extensions)
- `outreach/migrations/0003_image_library.py`, `0004_drop_image_url.py`
- `outreach/services/image_harvester.py` (bytes, not URLs)
- `outreach/services/image_storage.py` (NEW — Supabase upload helper)
- `outreach/services/image_processor.py` (NEW — resize, EXIF strip, pHash)
- `outreach/management/commands/migrate_images_to_storage.py` (NEW)
- `outreach/management/commands/purge_archived_images.py` (NEW)
- `outreach/api/views.py` (upload/approve/reject/delete/restore/report)
- `outreach/api/serializers.py`
- `outreach/api/permissions.py` (NEW — `IsPhotoApprover`)
- `community/models.py` (if Suggestion extension needed)
- `config/settings.py` (storage config)
- `requirements.txt` (django-storages, boto3, Pillow already present, imagehash)
- Tests: `outreach/tests/test_image_upload.py`, `test_image_moderation.py`, `test_cap_enforcement.py`, `test_migration_command.py`, `test_purge_command.py`

**Frontend**
- `components/SchoolPhotoGallery.tsx` (rewrite)
- `components/PhotoLightbox.tsx` (NEW)
- `components/SuggestForm.tsx` (photo-upload extension)
- `app/[locale]/dashboard/images/page.tsx` (pin, caption, archived tab, restore)
- `app/[locale]/dashboard/suggestions/page.tsx` (photo approval UI + slot warning)
- `lib/api.ts` (new endpoints)
- `package.json` (`yet-another-react-lightbox`)
- Tests: ~10 new

**Ops**
- `docs/plans/2026-04-22-image-library-sprint-plan.md` (this doc)
- `CHANGELOG.md`
- `CLAUDE.md` (update Apps table for outreach + update Next Sprint)
