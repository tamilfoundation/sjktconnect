# Sprint 1.8 Retrospective — Outreach App + School Images + Email Outreach

**Date**: 28 February 2026
**Duration**: 1 session

## What Was Built

1. **`outreach` Django app** — 6th app in the project. Contains `SchoolImage` and `OutreachEmail` models with migration, admin registration, services, management commands, and tests.

2. **Image harvester service** (`outreach/services/image_harvester.py`) — Two image sources:
   - **Satellite**: Constructs Google Static Maps API URL from school GPS coordinates (zoom 18, 640x400, satellite maptype)
   - **Places**: Searches Google Places API for school name with location bias, extracts photo reference and constructs photo URL
   - `harvest_images_for_school()` orchestrates both sources, with satellite as fallback

3. **`harvest_school_images` command** — Flags: `--limit`, `--state`, `--source`, `--dry-run`. Processes schools in order, logs each image created.

4. **Email sender service** (`outreach/services/email_sender.py`) — Brevo API integration for outreach introduction emails. Includes school page link, claim page link, and MOE email instructions. Console fallback in dev (same pattern as Magic Link emails).

5. **`send_outreach_emails` command** — Flags: `--limit`, `--state`, `--dry-run`. Skips already-emailed schools (deduplication by SENT/PENDING status).

6. **API change** — `SchoolDetailSerializer` now includes `image_url` field via `SerializerMethodField` returning the primary `SchoolImage` URL.

7. **Frontend change** — New `SchoolImage` component (responsive hero image with lazy loading). School profile page conditionally renders it above the header when `image_url` is present.

## What Went Well

- **Clean sprint** — No bugs, no blocked tasks, no rework. All 37 tests passed on first run.
- **Consistent patterns** — Followed existing patterns: Brevo email from `accounts/services/email.py`, management command flags from `check_new_hansards`, `SerializerMethodField` from `ConstituencyDetailSerializer.get_scorecard`.
- **Good separation of concerns** — Service layer does the API calls, management commands do orchestration, models are simple data holders. Each is independently testable.
- **Thorough test coverage** — All Google API calls mocked, both dev (no key) and production (with key) paths tested, edge cases covered (no GPS, no candidates, no photos, request errors, idempotent re-runs, primary demotion).

## What Went Wrong

- Nothing significant. This was a well-scoped sprint with clear requirements and established patterns to follow.

## Design Decisions

- **API key fallback chain** — Backend `image_harvester.py` checks `GOOGLE_MAPS_API_KEY` first, then falls back to `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY`. This avoids requiring a new env var for local development since the frontend key already exists.
- **Satellite images as stored URLs** — Rather than constructing satellite URLs on-the-fly in the frontend, we store them as `SchoolImage` records. This makes the data model uniform across all image sources and allows the API to return a simple `image_url` field.
- **Places photo promotes to primary** — When a Places photo is found, it demotes existing satellite primary and becomes the new primary. Real photos are higher quality than satellite views.
- **`update_or_create` for satellite, `create` for Places** — Satellite images are idempotent (same GPS = same URL), so we upsert. Places images could return different photos on subsequent runs, so we create new records.
- **Skip already-emailed schools** — `send_outreach_emails` checks for existing SENT/PENDING records and skips them, preventing duplicate emails.
- **Console fallback for both services** — Same pattern as Magic Link: no API key = log to console. No paid service needed for development or testing.

## Numbers

| Metric | Value |
|--------|-------|
| Backend tests | 375 (+34) |
| Frontend tests | 134 (+3) |
| Total tests | 509 (+37) |
| New backend files | 9 (models, apps, admin, 2 services, 2 commands, 2 test files) |
| New frontend files | 2 (SchoolImage component, SchoolImage test) |
| Modified backend files | 2 (base settings, school serializers) |
| Modified frontend files | 2 (types.ts, school profile page) |
| New migration | 1 (outreach 0001_initial) |
