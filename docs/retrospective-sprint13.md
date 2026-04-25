# Retrospective — Sprint 13: Image Storage Migration

**Date**: 2026-04-26 (single session)
**Goal**: Replace volatile Google Places photo URLs with bytes stored in Supabase Storage. Resolves TD-05 (broken images sitewide), TD-06 (Supabase egress regression), TD-13 (uploaded_by NULL semantics). Second sprint of the 5-sprint roadmap (12 → 13 → 14 → 15 → 16).

---

## What Was Built

### Backend
1. **Settings** (`backend/sjktconnect/settings/base.py`) — Supabase Storage block: `STORAGES["default"]` switches between `storages.backends.s3.S3Storage` (when `SUPABASE_STORAGE_ACCESS_KEY` is set) and `FileSystemStorage` (dev/tests). `MEDIA_ROOT = BASE_DIR / "media"` so dev tests don't leak files into source tree. Production override now augments `STORAGES` instead of replacing it (the bug that almost shipped — see "What Tripped Us Up" #1).
2. **Model** (`backend/outreach/models.py`) — `SchoolImage.image_file: ImageField(upload_to=schools/<moe_code>/, blank, null)`. `display_url` property returns `image_file.url` if set, else legacy `image_url`, so callers don't have to branch. Migration `outreach/0004_add_image_file_field.py`.
3. **Harvester rewrite** (`backend/outreach/services/image_harvester.py`) — `_download_bytes()` helper (5 MB cap, streamed). `harvest_satellite_image()` and `harvest_places_images()` now delete-then-create in one transaction, persisting bytes via `image_file.save(filename, ContentFile(data), save=True)`. Tests rewritten to `_mock_byte_response` helper.
4. **One-shot migration command** (`backend/outreach/management/commands/migrate_images_to_storage.py`) — idempotent + resumable. `Q(image_file__isnull=True) | Q(image_file="")` handles nullable FileField empty-state correctly. Closes DB connection every 50 rows to dodge Supabase pooler write-drop on long jobs. `--dry-run` and `--source` filters.
5. **Serializer** (`backend/schools/api/serializers.py`) — `get_image_url` now returns `primary.display_url`, so the frontend gets the storage URL automatically.
6. **Dependencies** (`backend/requirements.txt`) — `django-storages[boto3]>=1.14`, `Pillow>=10.0`.

### Frontend
7. **Lazy fetch in InfoWindow** (`frontend/components/SchoolMarkers.tsx`) — `/api/v1/schools/map/` returns only ~10 fields per school (Sprint 8.3 egress fix), so InfoWindow opened with no `image_url`. Added `useEffect` triggered on `selectedSchool.moe_code` that calls `fetchSchoolDetail()` once and merges. Cancellation flag prevents stale-merge on rapid pin clicks. No re-harvest is triggered because the detail endpoint reads existing `SchoolImage` rows.

### Production migration ops (executed)
- `migrate_images_to_storage --source MANUAL/COMMUNITY/etc.` migrated existing rows where bytes were retrievable.
- 5 stuck rows with permanently-dead URLs deleted manually after triage.
- Re-harvest passes: 1009 PLACES + 528 SATELLITE, using the **frontend Maps API key** (Static Maps + Places enabled). Cost ~US$15.
- Final state: **1534/1534 SchoolImage rows on Supabase Storage (100%)**.

### Tests
- Backend: 1106 → 1117 (+11). Test files: `test_image_harvester.py` rewritten + `test_migrate_command.py` (6 new tests) + `SchoolImageDisplayUrlTest` in `test_models.py`.
- Frontend: 258 unchanged.

### Deployed revisions
- `sjktconnect-api-00100-7x2` and `sjktconnect-web-00093-p8c`. School pages and InfoWindow verified on tamilschool.org.

---

## What Went Well

- **`display_url` property** carried the migration. Callers didn't need to know whether a row had migrated yet — the property hid the legacy fallback. Made the rollout boring.
- **Idempotent + resumable migration command** meant it was safe to re-run after the first abort. The `Q(image_file__isnull=True) | Q(image_file="")` filter took two attempts to get right, but once correct, ~1500 rows migrated without re-doing finished work.
- **Supabase Storage S3-compat worked first time** with `django-storages[boto3]`. `path` addressing + `default_acl=None` + `querystring_auth=False` + `custom_domain` for the public CDN URL. No surprises.
- **5 MB byte cap** prevented one outsize Places photo from killing the harvester. Saw it trigger once during re-harvest; logged and moved on.
- **Test isolation via `MEDIA_ROOT`** — once we set it explicitly to `BASE_DIR / "media"` and gitignored that directory, the leak (see #2 below) became impossible to repeat.

---

## What Tripped Us Up

### 1. Production STORAGES override almost replaced the entire dict
The first version of `production.py` had `STORAGES = { "staticfiles": ... }` which silently wiped the carefully configured `default` key from `base.py`. Caught when the first deploy returned `FileSystemStorage` errors trying to write to a read-only Cloud Run filesystem. Fixed by augmenting (`STORAGES["staticfiles"] = ...`) instead. **Lesson**: in Django settings, when a parent module builds a dict, the child must mutate it, not reassign. (Already a known gotcha for `INSTALLED_APPS`, just hadn't been internalised for `STORAGES`.)

### 2. FileSystemStorage leaked test artifacts into source tree
With `MEDIA_ROOT` undefined, Django defaults to whatever `default_storage.location` resolves to — turned out to be `backend/`. Tests using `image_file.save()` created `backend/schools/<moe_code>/<filename>` directories. Caught only after `git status` showed unexpected files. Fix: explicit `MEDIA_ROOT = BASE_DIR / "media"` + `backend/media/` in `.gitignore` + delete leaked files. **Lesson**: never trust default storage paths in dev — always set `MEDIA_ROOT` explicitly.

### 3. `filter(image_file="")` matched 0 rows
First migration run reported "Migrating 0 images". Cause: `image_file` is a nullable FileField, so empty rows are NULL, not `""`. The fix `Q(image_file__isnull=True) | Q(image_file="")` covers both. **Lesson**: nullable FileFields can be either NULL or empty string depending on how the row was written; OR them.

### 4. Places-only Maps API key returned 403 on Static Maps
First re-harvest attempt failed every SATELLITE row with HTTP 403. Cause: the backend `GOOGLE_MAPS_API_KEY` env var was set to a Places-only restricted key, but Static Maps is a separate API in the key restrictions panel. Fix: re-ran with the frontend key (`AIzaSyAx...`) which had both APIs enabled. **Lesson**: when a single command needs multiple Google APIs, verify each is enabled on the key's restriction list, not just the obvious one.

### 5. InfoWindow placeholder despite migrated images
Hero photos rendered fine on `/school/<moe>/` pages but the map's InfoWindow still showed a placeholder. Cause: the Sprint 8.3 egress optimisation trimmed `/api/v1/schools/map/` to ~10 fields (no `image_url`). Fix: lazy-fetch detail in `SchoolMarkers.tsx` when an InfoWindow opens. Critically, this does not retrigger the harvester — it reads the existing primary `SchoolImage`. **Lesson**: when an endpoint is trimmed for egress, downstream UIs need a graceful "fetch full detail on interaction" path.

---

## What's Left for Sprint 14

- Drop `Suggestion.image` `BinaryField`.
- Direct upload from `SuggestForm` (`PHOTO_UPLOAD` type) to `SchoolImage.image_file` — no more BinaryField round-trip.
- Pillow validation pipeline (size/format/dimensions/EXIF/perceptual hash dedup).
- 20-photo cap enforced at APPROVE time.
- DRF throttling on upload endpoint.

---

## Tech Debt Status After Sprint 13

- ✅ TD-05 (volatile Places URLs) — RESOLVED
- ✅ TD-06 (Supabase egress) — PROVISIONALLY RESOLVED, monitoring 7 days
- ✅ TD-13 (uploaded_by NULL) — RESOLVED (no-op, semantically correct)
- 🔴 TD-01 (re-opened Auth.js state cookie) — Sprint 16
- 🟡 TD-07 (Suggestion.image BinaryField) — Sprint 14
- 🟡 TD-09 (hardcoded image/png content_type) — Sprint 14
- 🟢 TD-10 residual / TD-11 / TD-12 / TD-14 / TD-15 — Sprint 16

5-sprint roadmap on track: 12 ✅ → 13 ✅ → **14 next** → 15 → 16.
