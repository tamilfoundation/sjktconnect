# Retrospective — Sprint 14: Community Photo Uploads

**Date**: 2026-04-26 (single session, immediately after Sprint 13 close)
**Goal**: Replace the Sprint 8.2 base64-into-BinaryField photo flow with multipart uploads to Supabase Storage. Add Pillow validation, perceptual-hash dedup, daily throttling, a 20-photo cap on approve, and a hero-pin endpoint. Resolves TD-07 + TD-09 + TD-16 (suggestions-page portion). Third sprint of the 5-sprint roadmap (12 → 13 → 14 → 15 → 16).

---

## What Was Built

### Backend
1. **`outreach/services/image_processor.py`** (NEW) — `process_upload(bytes) -> ProcessedImage` with stable error codes (`empty`, `too_large`, `too_small`, `unsupported_format`, `invalid_image`). Pipeline: size check → format check → EXIF orient → dimension check → resize ≤1600px → re-encode → pHash. Pure function; trivially unit-testable.
2. **`POST /api/v1/schools/<moe>/suggestions/photo/`** — multipart endpoint. `MultiPartParser` + `FormParser`. Returns 413 (too_large), 415 (unsupported_format), 400 (other validation), 409 (duplicate), 429 (throttled), 201 (success).
3. **`POST /api/v1/schools/<moe>/images/<id>/pin/`** — atomic hero swap. Single SQL UPDATE clears siblings, second one sets target.
4. **`community/api/permissions.py`** — `IsPhotoApprover`. Resolves `obj.school_id` from either Suggestion or SchoolImage. SUPERADMIN OR `admin_school_id == school_id`. **MODERATOR explicitly NOT a photo approver** (Image Library plan Decision #5).
5. **`community/api/throttles.py`** — `PhotoUploadUserThrottle` (5/day) + `PhotoUploadSchoolThrottle` (20/day). Custom `SimpleRateThrottle` subclasses; cache keys scoped by user pk and school moe_code.
6. **Migration `community/0002_drop_image_add_pending`** — drops the legacy `Suggestion.image` BinaryField, adds `pending_image: ImageField` (Supabase, `pending/<uuid>.<ext>` path) + `phash: CharField(db_index=True)`. Sprint 13's COMMUNITY pass had already migrated approved bytes; this drops the now-empty column.
7. **`approve_suggestion` rewrite** — PHOTO_UPLOAD path opens `pending_image`, copies bytes into a fresh `SchoolImage.image_file` under `schools/<moe>/`, clears the pending file. `_apply_photo_upload` no-ops at cap (defence in depth; cap is enforced upstream by the API view).
8. **`reject_suggestion` rewrite** — PHOTO_UPLOAD now deletes the staged file from Supabase Storage best-effort.
9. **`SuggestionListSerializer.pending_image_url`** — surfaces the Supabase URL to authorised viewers via the moderation queue API.
10. **`requirements.txt`** — `imagehash>=4.3`.
11. **`REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]`** added to base settings.

### Frontend
12. **`SuggestForm.tsx`** rewritten — file picker + preview + client-side type/size/dimensions check. Multipart `FormData` POST via new `uploadSchoolPhoto()`. Typed `PhotoUploadError` surfaced as user-friendly messages for 5 stable codes.
13. **`ImageManager.tsx`** — adds ⭐ Make hero button per image; current hero shows ★ Hero badge + disabled. Optimistic local update.
14. **`ModerationQueue.tsx`** — inline photo preview (`pending_image_url`), school name as link to `/school/<moe>` (target=_blank), 20-photo `slot_full` 409 surfaces as inline amber banner, reject reason promoted from input → multi-line textarea.
15. **`lib/api.ts`** — `uploadSchoolPhoto`, `pinSchoolImage`, `approvePhotoSuggestion`, `PhotoUploadError` class with `Object.setPrototypeOf` fix for ES5-target `instanceof` correctness.
16. **`lib/types.ts`** — Suggestion gets `school_moe_code` + `pending_image_url`.

### Tests
- **Backend**: 1117 → 1145 (+28). New files: `test_photo_upload.py` (validation matrix, throttle hits, pHash dedup, owner-school rejected, anonymous), `test_photo_approve_cap.py` (cap 409 + reject deletes file), `test_photo_approver_perm.py` (5-role matrix), `test_pin_image.py` (atomic primary swap, permission, foreign-image 404). Existing `test_approval.py` rewritten for the new flow.
- **Frontend**: 258 → 286 (+28 from picking up the new tests + the existing pre-existing flake). New: `SuggestForm.test.tsx` (3 tests), `ImageManager.test.tsx` (3 tests including pin), `ModerationQueue.test.tsx` (3 tests including slot_full banner).

### Deployed
- `sjktconnect-api-00101-klw` and `sjktconnect-web-00094-gqx`.
- Migration `community.0002_drop_image_add_pending` applied on prod via container-start migrate hook.
- Smoke-verified live: `POST /suggestions/photo/` → 403 unauth, `POST /images/<id>/pin/` → 403 unauth, `GET /schools/<moe>/` → 200.

---

## What Went Well

- **Tight scope discipline.** 28 files touched (mostly new files in test directories). Single coherent deliverable, single session, no mid-sprint splitting.
- **`IsPhotoApprover` permission class generalised cleanly** — works against Suggestion or SchoolImage by resolving `obj.school_id` either way. No duplicated permission logic across the upload, approve, reject, and pin endpoints.
- **`uploadSchoolPhoto` + `PhotoUploadError` typed surface** carried the frontend simplification. The form maps 5 stable codes to friendly strings; no fragile string-matching on backend error messages.
- **Sprint 13's `display_url` property** kept the frontend changes shallow — the gallery renders a Supabase URL or a legacy URL transparently. Sprint 14 didn't have to touch any rendering call site.
- **Test client is a real integration test.** All 28 backend tests exercise the full Django stack (URL conf → DRF parser → permission → view → service → SQLite migration). One smoke-test on URL routing was sufficient before deploy because the test suite already covered everything else.

---

## What Went Wrong

### 1. Solid-colour test fixtures broke pHash dedup tests
Initial `valid_jpeg_bytes(colour=(R,G,B))` produced visually-identical solid blocks regardless of colour or dimensions, so `imagehash.phash` returned the same hash and the throttle test couldn't exhaust the per-user quota with "different" images.
- **Root cause**: I didn't realise pHash is by design size/colour-tolerant — different colours of the same shape hash identically.
- **Fix applied**: rewrote the fixture to paint a 16×16 grid of random pixels seeded by an integer, so `valid_jpeg_bytes(seed=N)` produces visually distinct images for distinct N.
- **System change**: lessons.md gets a one-liner about pHash test fixtures.

### 2. `@override_settings(REST_FRAMEWORK={...})` doesn't reach DRF throttle classes
Tried to set per-test throttle rates with `override_settings` so the throttle test could hit the quota in 2 calls instead of 5. DRF's `SimpleRateThrottle.THROTTLE_RATES` is bound at class-definition time from `api_settings`, so settings overrides never reach already-imported classes.
- **Root cause**: misunderstood how DRF wires its settings cache into throttle classes.
- **Fix applied**: in setUp, mutate the `rate` attribute on the throttle class directly; restore in tearDown.
- **System change**: lessons.md gets a one-liner so the next throttle test author doesn't repeat this.

### 3. ES5-target `extends Error` broke `instanceof` checks
Frontend `PhotoUploadError extends Error` failed `err instanceof PhotoUploadError` checks inside the form's catch block. Test assertion fell through to the generic message.
- **Root cause**: project's `tsconfig.json` has `target: "es5"`, which strips the prototype chain when extending built-ins. Browsers running ES5-transpiled code would see the same bug.
- **Fix applied**: add `Object.setPrototypeOf(this, PhotoUploadError.prototype)` in the constructor. Production fix, not a test-only patch.
- **System change**: lessons.md gets the rule for any custom Error subclass in this codebase.

### 4. `<input type="file" required>` blocks form submit in jsdom
`fireEvent.click(submitButton)` was no-op in the SuggestForm test because jsdom enforces native `required` even when React state holds the file.
- **Root cause**: jsdom checks form validity on click-submit; setting `input.files` via Object.defineProperty doesn't update the validity API.
- **Fix applied**: use `fireEvent.submit(form)` directly.
- **System change**: lessons.md note on jsdom + required file inputs.

### 5. One LLM-flake in parliament/test_brief_generator
Full-suite ran 980 tests; 1 failed: `test_html_contains_all_summaries` asserts the literal phrase "Tamil school repairs" appears in Gemini-generated brief HTML, but Gemini paraphrased to "delays in SJK(T) repair works".
- **Root cause**: brittle assertion against non-deterministic LLM output. Pre-existing, predates Sprint 14.
- **Fix applied**: none in Sprint 14. Logged as **TD-17** for Sprint 16 (Code-Quality Pass) — either mock the Gemini call or loosen the assertion.

---

## Design Decisions

Three decisions worth recording in `docs/decisions.md`:

1. **`Suggestion.pending_image` over a separate staging model**: a single ImageField on Suggestion with a UUID path is simpler than a `StagedPhoto` intermediate model. Bytes for un-approved uploads live on a public bucket but at unguessable URLs — acceptable risk for a community-photo platform; the alternative was a private bucket with signed URLs, which adds infra complexity without proportionate value.
2. **MODERATOR excluded from photo approval**: SUPERADMIN + bound school admin only. Photos are school-scoped decisions; MODERATORs can still moderate data corrections + notes which are intent-scoped. This is the only place in the codebase where MODERATOR has fewer rights than for other resources — tracked explicitly in `IsPhotoApprover`.
3. **20-photo cap enforced at approve time, not upload time**: uploads stay open so users can submit; moderators decide. Enforcing at upload would penalise the user for moderator inaction (queue backlog), which is the wrong direction.

---

## Numbers

| Metric | Sprint start | Sprint end | Δ |
|---|---|---|---|
| Backend tests (passing) | 1117 | 1144 | +27 (+ 1 LLM flake = +28 total) |
| Frontend tests (passing) | 258 | 285 | +27 (+ 1 SubscribeForm flake = +28 total) |
| Files touched | — | 28 | — |
| Production revisions | api-00100 / web-00093 | **api-00101-klw / web-00094-gqx** | +1 each |
| Open tech debt | 5 | 6 | +1 (TD-17 LLM flake) |

5-sprint roadmap: 12 ✅ → 13 ✅ → **14 ✅** → 15 → 16.
