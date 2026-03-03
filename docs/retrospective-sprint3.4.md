# Sprint 3.4 Retrospective — Homepage, About, Data Provenance & UX

**Date**: 2026-03-03
**Duration**: ~1 session (continuation from Sprint 3.3)

## What Was Built

10 UX and content improvements to make the platform more credible, navigable, and user-friendly:

1. **Favicon & site metadata** — apple-touch-icon, favicon.ico, Open Graph tags, manifest icons
2. **National summary statistics endpoint** — `GET /api/v1/schools/national-stats/` returning aggregate counts
3. **Homepage hero section** — Mission statement + NationalStats bar (schools, students, constituencies)
4. **About page** — `/about/` with mission, methodology, team, and data sources
5. **Footer About link** — Quick navigation alongside Subscribe and Contact
6. **MOE jargon translation** — `translations.ts` converts Malay labels to English (enrolment categories, grade levels)
7. **Claim This Page CTA reframe** — Emphasises community benefit over claiming
8. **Parliament Watch & empty states** — Better messaging when no data available (mentions, news, constituencies)
9. **Zero-school constituency filter** — Hides constituencies with no SJK(T) schools from the list; hides boundary map when no GeoJSON
10. **Data provenance** — Source attribution on SchoolProfile and Footer, social proof on subscribe form

## What Went Well

- **Quick execution** — All 10 tasks completed in a single session
- **No new models or migrations** — Pure frontend + 1 API endpoint, low risk
- **Test coverage maintained** — 215 frontend + 532 backend = 747 total, all passing
- **Consistent i18n** — All new strings added to all three language files (EN/TA/MS)
- **Clean separation** — `translations.ts` utility keeps MOE jargon mapping separate from components

## What Went Wrong

- **Session crash at ~85% context** — Lost progress mid-sprint, had to recover from conversation log. This is the second time a crash has happened during a large sprint (Sprint 3.3 had the same issue).
- **Build memory limits** — Next.js build continues to fail at page data collection on 8GB RAM. Compilation succeeds but the worker process runs out of memory. Tests are the only verification available locally.
- **Supavisor holding test DB connections** — Stale Supabase connection pooler sessions prevented `test_postgres` from being dropped. Required manual `pg_terminate_backend` before tests could run.

## Design Decisions

- **National stats as separate endpoint** — Rather than embedding in the school list, a dedicated `/national-stats/` endpoint keeps the homepage request lightweight
- **Translation utility pattern** — `translations.ts` uses simple key-value maps rather than i18n integration, since these are data transformations not UI strings
- **Data provenance as static text** — "Data source: MOE, January 2026" is hardcoded rather than dynamic, since the MOE data file is updated infrequently (annually)
- **Zero-school filtering in frontend** — Constituencies with no SJK(T) schools are filtered client-side rather than server-side, keeping the API response complete for other consumers

## Numbers

| Metric | Value |
|--------|-------|
| Tasks completed | 10 |
| Files changed | 33 |
| Lines added | ~1,037 |
| New frontend tests | 25 |
| New backend tests | 1 |
| Total tests | 747 (532 backend + 215 frontend) |
| New components | 2 (HeroSection, NationalStats) |
| New pages | 1 (About) |
| New API endpoints | 1 (national-stats) |
| Translation keys added | ~30 (across 3 languages) |
