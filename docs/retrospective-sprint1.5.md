# Sprint 1.5 Retrospective — Constituency + DUN Pages

## What Was Built
- Constituency detail page `/constituency/[code]` with ISR — MP info, scorecard, boundary map (GeoJSON overlay), demographics, school table, DUN list
- DUN detail page `/dun/[id]` with ISR — ADUN info, demographics, boundary map, school table, parent constituency link
- Constituencies index `/constituencies/` — browsable table with client-side state filter, school counts, MP/party display
- 5 new reusable components: BoundaryMap, ScorecardCard, DemographicsCard, SchoolTable, ConstituencyList
- 7 new API functions covering constituencies, DUNs, and GeoJSON
- 7 new TypeScript types (ConstituencyDetail, Scorecard, DUN, DUNDetail, GeoJSON types)
- Header nav updated with "Constituencies" link
- Loading skeletons for constituency and DUN pages
- SEO metadata (title, description, Open Graph) for all new pages
- 36 new frontend tests (374 total: 276 backend + 98 frontend)

## What Went Well
- Component reuse from Sprint 1.4 saved time — StatCard, Breadcrumb already existed
- The API client pattern (auto-pagination) applied cleanly to constituencies and DUNs
- ISR decision from Sprint 1.4 carried forward with no friction
- All 98 frontend tests passed first time — no configuration issues this sprint
- The existing backend API had all endpoints needed — no backend changes required

## What Went Wrong
- Sprint close workflow was not followed completely — retrospective, lessons check, workspace cleanup, and Mission Control update were skipped. Had to go back and add them after committing.

## Design Decisions
- **ISR over SSG** (carried from Sprint 1.4): Avoids build-time API dependency in Docker/Cloud Run
- **Client-side state filter on index page**: Server renders all constituencies, client filters — works because total count (~122 with Tamil schools) is small enough for a single page load
- **Map centre estimated from school GPS**: Rather than geocoding constituency names, averaged GPS coordinates of schools within the constituency — good enough for boundary display
- **GeoJSON boundary as Google Maps Data Layer**: Used `map.data.addGeoJson()` rather than custom polygon rendering — cleaner API, built-in styling
- **DUN pages by numeric ID**: DUN codes aren't unique nationally (N01 exists in all states), so the route uses database ID `/dun/[id]` not code

## Numbers
- Files created: 14
- Files modified: 6
- Lines added: ~1,519
- Tests: 36 new (374 total)
- Components: 5 new reusable
- Pages: 3 new routes (constituency detail, DUN detail, constituencies index)
