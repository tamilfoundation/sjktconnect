# Sprint 1.3 Retrospective — Next.js Frontend + School Map

**Date**: 2026-02-27
**Duration**: ~45 minutes

## What Was Built

Next.js 14 frontend with interactive Google Maps showing all 528 Tamil school locations:

- **Project scaffold**: Next.js 14 + App Router + Tailwind CSS + TypeScript
- **Layout**: Responsive header with mobile hamburger menu, footer
- **Map page** at `/` — full-width Google Maps with AdvancedMarker + MarkerClusterer
- **Info window**: Click a school pin to see name, code, state, enrolment, teachers, constituency
- **State filter**: Dropdown narrows map pins by state, displays "Showing X of Y schools"
- **Search box**: 300ms debounced typeahead, calls `/api/v1/search/`, shows schools + constituencies
- **API client**: Automatically paginates through all 528 schools (11 pages at 50/page)
- **Dockerfile**: Multi-stage build, standalone output, port 8080 for Cloud Run
- **26 tests**: API client (8), Header (4), Footer (3), StateFilter (5), SearchBox (6)

## What Went Well

1. **Clean separation** — API client in `lib/api.ts` handles all pagination logic. Components just consume data.
2. **vis.gl/react-google-maps** — Modern React wrapper for Google Maps. AdvancedMarker + useMap hook made clustering integration straightforward.
3. **Build succeeds** — 107 kB first load JS. Next.js standalone output works for Docker deployment.
4. **All tests pass first time** after fixing jest config (see What Went Wrong).

## What Went Wrong

1. **Jest config option names** — Used `setupFilesAfterSetup` (not a valid Jest option) and `testPathPattern` (CLI-only). Correct config options: `setupFiles` and `testMatch`.
2. **Jest setupFiles runs before framework** — `@testing-library/jest-dom` needs `expect` global, which isn't available in `setupFiles`. Fixed by importing `@testing-library/jest-dom` directly in each test file.
3. **ts-jest JSX transform** — tsconfig.json has `jsx: "preserve"` (Next.js convention). ts-jest needs `jsx: "react-jsx"` to transform JSX. Fixed by passing inline tsconfig to ts-jest instead of referencing the file.

## Design Decisions

1. **Client-side data loading** — All 528 schools fetched client-side via paginated API. 11 requests at 50/page. Acceptable for initial load; can add server-side caching or a bulk endpoint later if needed.
2. **@vis.gl/react-google-maps over @react-google-maps/api** — vis.gl is Google's official React wrapper, actively maintained, supports AdvancedMarker natively.
3. **Clustering via @googlemaps/markerclusterer** — Google's own clustering library, integrates with useMap hook. Automatically groups nearby pins.
4. **No SSR for map page** — Map is purely client-rendered (`"use client"` throughout). Google Maps JS API requires browser environment. SSR would add complexity with no benefit.
5. **Search triggers on 2+ characters** — Matches backend API validation. 300ms debounce prevents excessive API calls while typing.
6. **State filter from data** — States extracted dynamically from fetched schools rather than hardcoded. Adapts automatically if school data changes.

## Numbers

| Metric | Value |
|--------|-------|
| Frontend tests added | 26 |
| Backend tests | 276 (unchanged) |
| Total tests | 302 |
| Files created | 25 (19 source + 6 test) |
| Files modified | 1 (.gitignore) |
| First load JS | 107 kB |
| Build time (Next.js) | ~15 seconds |
