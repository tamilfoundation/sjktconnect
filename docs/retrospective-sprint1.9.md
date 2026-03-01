# Sprint 1.9 Retrospective — Full Stack Deployment + Phase 1 Close

**Date**: 2026-02-28
**Duration**: 1 session
**Type**: Deployment / Infrastructure

## What Was Built

1. **New GCP project** `sjktconnect` under `tamilfoundation.org` organisation — billing linked, APIs enabled
2. **Backend deployment** (`sjktconnect-api`) — Django + DRF on Cloud Run, all 6 apps, Supabase PostgreSQL
3. **Frontend deployment** (`sjktconnect-web`) — Next.js 14 standalone on Cloud Run, first ever frontend deploy
4. **Google Maps API key** — created and restricted to Maps JS + Static Maps + Places APIs
5. **CORS configuration** — frontend origin whitelisted on backend
6. **Cloud Run job** — `sjktconnect-check-hansards` recreated in new project
7. **Cloud Scheduler** — `sjktconnect-daily-check` recreated (daily 8am MYT)
8. **528 satellite images** harvested into production database

## What Went Well

- **Backend deployed on first try** after fixing ALLOWED_HOSTS
- **Smoke tests all passed** — health check, schools API (528), search, constituencies (222), all frontend pages
- **Satellite image harvest** — all 528 schools processed in one run
- **Zero code changes needed** for the backend deploy — everything just worked

## What Went Wrong / Blockers

- **Frontend build failed first time** — `NEXT_PUBLIC_API_URL` was undefined during Docker build. Cloud Build's `--set-build-env-vars` sets env vars in the Cloud Build environment, NOT as Docker `--build-arg`. Fixed by using `ENV` with production defaults in the Dockerfile.
- **GCP project name** — parentheses in "SJK(T) Connect" were rejected. Used "SJKT Connect" instead.
- **gcloud auth expired** — `admin@tamilfoundation.org` token had expired. Required manual re-auth.
- **Domain verification** — `tamilschool.org` not yet verified in Google Webmaster Central. Custom domain mapping deferred.
- **BREVO_API_KEY** — not yet available. Email outreach deferred.
- **Accidental deploy to old project** — first backend deploy went to `gen-lang-client-0871147736` (personal account) before the user flagged it should be under tamilfoundation. Cost: 1 extra Cloud Build.

## Design Decisions

1. **Separate GCP project per org product** — SJK(T) Connect gets its own project under tamilfoundation.org, not shared with personal projects
2. **ENV over ARG in Dockerfile** — for `NEXT_PUBLIC_*` vars that Cloud Build can't pass as build args, bake production defaults into the Dockerfile
3. **One Maps API key** — shared between frontend (JS API) and backend (Static Maps + Places), restricted to those 3 services only
4. **Satellite-first images** — harvested satellite images for all 528 schools immediately. Places API photos deferred (optional upgrade later).

## Phase 1 Summary

Phase 1 "The Seed" is now complete. Over 8 sprints (1.1-1.8) plus this deployment sprint:

- **6 Django apps**: core, schools, hansard, parliament, accounts, outreach
- **Next.js 14 frontend**: interactive map, school/constituency/DUN pages, claim flow, edit flow
- **509 tests** (375 backend + 134 frontend)
- **528 schools** with satellite images, GPS coordinates, constituency/DUN links
- **222 constituencies** with boundary maps, scorecards, demographics
- **Magic Link auth** for school representatives
- **Automated Hansard pipeline** running daily on Cloud Scheduler
- **Email outreach infrastructure** ready (needs BREVO_API_KEY to activate)

## Post-Sprint Follow-ups (2026-03-01)

All deferred items from sprint 1.9 resolved in a follow-up session:
- `tamilschool.org` custom domain mapped and verified (auto-verified via domain provider)
- `BREVO_API_KEY` set on backend; Brevo sender domain authenticated (DKIM + DMARC)
- `GEMINI_API_KEY` set on backend
- Upgraded `Marker` to `AdvancedMarker` + `Pin` (indigo styling) in MiniMap and SchoolMarkers
- Added Google Maps Map ID to Dockerfile
- Fixed outreach email encoding bug (literal em dashes rendered as diamonds in email clients)
- Deleted old `sjktconnect-api` from personal GCP project
- Removed stale `tamilschool.org.my` domain mapping
- Test outreach email sent successfully via Brevo

## Numbers

| Metric | Value |
|--------|-------|
| Cloud Run services | 2 (api + web) |
| Cloud Run jobs | 1 (hansard check) |
| Cloud Schedulers | 1 (daily 8am MYT) |
| Satellite images harvested | 528 |
| Backend deploys | 3 revisions (sprint) + 2 (follow-up env vars) |
| Frontend deploys | 1 revision (sprint) + 1 (follow-up AdvancedMarker) |
| Build failures | 1 (Dockerfile ARG issue) |
| Total sprints in Phase 1 | 9 (1.1 through 1.9) |
