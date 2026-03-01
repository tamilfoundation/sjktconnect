# Sprint 1.10 Retrospective — School Page Redesign + Image Fix

## What Was Built
- School mentions API endpoint (`GET /api/v1/schools/<moe_code>/mentions/`)
- Multi-photo image harvester (3 Google Places photos per school, was 1)
- School detail API returns `images[]` array alongside legacy `image_url`
- `SchoolPhotoGallery` component (hero + thumbnails + fallback chain)
- `SchoolHistory` CTA component (placeholder for future book scanning)
- `NewsWatchSection` placeholder component
- Redesigned school page layout (photo → name → stats → details → map → Parliament Watch → News Watch → History → sidebar → Claim)
- "View School" link in map pin popups
- "View" link in search results + constituency results now clickable
- Fixed 528 broken image URLs (API key rotation via SQL UPDATE)

## What Went Well
- SQL key replacement was instant — 528 URLs fixed in one UPDATE
- Existing test suite caught no regressions (437 passing)
- Subagent-driven development kept tasks focused and isolated

## What Went Wrong
- **API key baked into stored URLs**: Sprint 1.8 stored the API key directly in image URLs. When the key was deleted, all 528 images broke. Should have stored coordinates/photo_reference only and constructed URLs at serve time.
- **Cloud Run job couldn't find management command**: Spent time debugging a harvest job that failed with "Unknown command". Root cause was using an old container image, but the real fix was the SQL UPDATE approach.
- **No navigation to school pages**: The main map page had no links to school pages — a fundamental UX gap that went unnoticed for 6 sprints.

## Design Decisions
- **SQL UPDATE over re-harvest**: Replacing the key substring in stored URLs was faster and more reliable than re-running the harvest pipeline.
- **Placeholder sections**: History and News Watch added as placeholders with clear CTAs, avoiding empty pages while signalling future features.
- **Backwards-compatible API**: `image_url` field kept for any consumers; new `images[]` array added alongside it.

## Numbers
- Backend tests: 437 passing
- Commits: 6 (mentions API, harvester, serializer, types, page redesign, nav links)
- Image URLs fixed: 528
- New components: 3 (SchoolPhotoGallery, SchoolHistory, NewsWatchSection)
- New API endpoints: 1 (school mentions)
