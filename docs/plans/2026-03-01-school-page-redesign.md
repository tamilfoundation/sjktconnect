# School Page Redesign — Fix & Enrich (Sprint 1.10)

**Date**: 2026-03-01
**Approach**: A (Fix & Enrich now, full redesign later when book content + news pipeline are ready)
**Sprint label**: 1.10 (Phase 1 gap fill, before continuing Phase 2)

## Context

The school detail page at `/school/[moe_code]` exists but has two critical issues: broken photos (old API key deleted) and a missing Parliament Watch endpoint (frontend silently gets empty data). The page also lacks sections needed to tell the complete story of each school — its needs, political context, and history.

The user has a published book with school histories that will eventually be scanned and processed. Until then, placeholder CTAs invite contributions.

## Design Decisions

1. **Approach A first, Approach B later** — fix and enrich the existing page now. A full storytelling redesign (Stitch prototype, tabbed hub) happens later when book content and News Watch data are available.

2. **Photo priority**: Google Places photo (first choice) > satellite image (fallback) > placeholder CTA. Harvest up to 3 Places photos per school, mark the best as primary.

3. **History section**: placeholder with call to action ("Help us tell this school's story") — not AI-generated, not empty/hidden.

4. **Claim button**: move from prominent mid-page position to a smaller banner at the bottom.

## What Gets Built

### Section 1: Photo Fix + Gallery

**Problem**: School images were harvested with an API key that has since been deleted. All image URLs are dead.

**Backend**:
- Update `image_harvester.py` to fetch up to 3 Google Places photos per school (currently fetches 1)
- Management command to re-harvest all schools with the new API key (`reharvest_school_images`)
- New serializer field: return all images for a school (not just primary `image_url`)

**Frontend**:
- Replace single `SchoolImage` component with a photo component that handles the fallback chain: Places photo > satellite > placeholder
- Thumbnail row when multiple photos exist
- "Know this school? Share a photo" CTA when only satellite/no images

### Section 2: Parliament Watch Endpoint

**Problem**: Frontend calls `GET /api/v1/schools/{moe_code}/mentions/` but the endpoint was never built. Returns 404, caught silently.

**Backend**:
- New view: `SchoolMentionsView` in `parliament/api/views.py`
- Query: `HansardMention.objects.filter(matched_schools__school__moe_code=moe_code, review_status='APPROVED')`
- Serializer: sitting date, MP name/party/constituency, mention type, significance, sentiment, AI summary, verbatim quote
- URL: wire into `schools/api/urls.py`

**Frontend**:
- No changes needed — `MentionsSection` component already renders mention data when present.

### Section 3: New Sections + Layout

**New sections**:
- **History & Story**: placeholder card — "Help us tell this school's story — if you have information about this school's history, contact us at info@tamilfoundation.org"
- **News Watch**: empty section wired for Phase 2. Shows "No news articles yet." Will auto-populate when Sprint 2.5-2.6 delivers NewsWatch via `affected_schools` M2M.
- **Photo upload CTA**: for schools without Places photos

**Layout improvements**:
- Better visual hierarchy: hero photo > school name + Tamil name > stats > political context > map > Parliament Watch > News Watch > History > Claim
- Show `name_tamil` prominently under school name when available
- Move "Claim This Page" to a smaller banner at the bottom

**Not in scope**:
- Book content processing (future — requires scanning + OCR/extraction)
- Photo upload functionality (future — requires file storage infrastructure)
- AI-generated content
- Tab navigation or modular hub (Approach B territory)
- Full visual redesign (Approach B)

## Testing

- Backend: tests for SchoolMentionsView, image harvester changes
- Frontend: existing tests should still pass; no new frontend test framework changes needed
- Manual: verify photos display on live site after re-harvest

## Dependencies

- New Google Maps API key (done — `AIzaSyAx7HROyUT0aAp8jNQ-oWUMZsllr3fwF4A`)
- Google Places API enabled on the key (done — confirmed in key restrictions)
