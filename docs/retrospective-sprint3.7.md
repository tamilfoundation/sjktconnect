# Sprint 3.7 Retrospective — Map InfoWindow, School Page Polish & Enrolment Filter

**Date**: 2026-03-03
**Duration**: Single session (continuation of Sprint 3.6 deployment)

## What Was Built

1. **Enrolment filter fix**: Schools above the enrolment threshold are now hidden entirely from the map instead of displayed as grey pins. This reduces visual clutter and makes the filter more intuitive.

2. **Map InfoWindow redesign**: Complete overhaul of the map popup when clicking a school pin:
   - School image (or grey placeholder)
   - Assistance type badge (Government-Aided / Government) + location badge (Urban / Rural)
   - 3-stat row: students, teachers, student:teacher ratio
   - Constituency and DUN links (DUN links to dedicated DUN page)
   - Full-width "View School" CTA button
   - New `mapInfoWindow` translation namespace (EN/MS/TA)

3. **School detail page redesign**: Matched Stitch prototype with:
   - 12-column grid layout (7/5 split instead of 3/2)
   - 3 elevated stat cards with SVG icons (students, teachers, grade) replacing 5 flat cards
   - Preschool + Special Ed moved to a compact info bar
   - Top-aligned title (not vertically centred)
   - Metadata styled as a rounded chip/pill
   - Taller photo gallery (400px on desktop) with overlay thumbnails inside the image

## What Went Well

- **Stitch-driven design**: Using Stitch to prototype the InfoWindow and school page meant clear visual targets. The implementation closely matched the designs.
- **Quick iteration cycle**: User feedback → implementation → deployment happened efficiently within a single session.
- **No test regressions**: All 757 tests continued to pass throughout the sprint.
- **N+1 query prevention**: Adding `select_related("dun")` and `prefetch_related("images")` to the list view proactively prevented performance issues from the new serialiser fields.

## What Went Wrong

- **Transient deploy failure**: First frontend deploy failed with `OSError: [Errno 22] Invalid argument`. Retry succeeded — likely a transient Cloud Build issue.
- **Test index confusion**: After changing SchoolPhotoGallery to show all thumbnails (including the active one) as an overlay, the test that clicked "the second thumbnail" was clicking the wrong element. The fix was simple but required understanding the new DOM structure.
- **DUN ID vs code confusion**: Initially used `dun_code` for the DUN page link, but the DUN page uses a numeric `[id]` parameter. Had to add `dun_id` to the serialiser and use that instead.

## Design Decisions

1. **Hide vs grey for enrolment filter**: Hiding schools above the threshold is cleaner than greying them out. Grey pins still create visual noise and confuse the count.
2. **Inline styles in InfoWindow**: Google Maps InfoWindow renders in a shadow DOM that doesn't inherit Tailwind classes. Used inline styles instead.
3. **Overlay thumbnails**: Placing thumbnails inside the hero image (overlaid at bottom-left) saves vertical space and eliminates the gap that existed with a separate thumbnail strip below.
4. **3 cards + info bar**: Preschool and Special Ed enrolment don't warrant their own stat cards. A compact bar below the main stats communicates the same information more efficiently.
5. **DUN in InfoWindow**: PPD (district education office) is not meaningful to most users and has no dedicated page. DUN (state constituency) has a page and is more useful for political context.

## Numbers

| Metric | Value |
|--------|-------|
| Backend tests | 532 |
| Frontend tests | 225 |
| Total tests | 757 |
| Commits | 3 |
| Files changed | ~10 |
| New translation keys | 8 (mapInfoWindow namespace) |
