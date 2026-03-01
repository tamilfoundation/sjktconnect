# Implementation Roadmap: SJK(T) Connect

**Version**: 0.6
**Date**: 15 February 2026
**Status**: Draft — Soliciting Feedback
**Author**: Tamil Foundation / Elan
**PRD Reference**: `PRD-SJKTConnect.md` (v0.2)

---

## Context

The PRD (v0.2) defines a 5-phase platform: Intelligence Engine + Advocacy Map + Communications Hub for Malaysia's 528 Tamil schools. The project folder at `SJKTConnect/` exists with data files but no application code yet.

**What we're building first**: Phase 0 — Parliament Watch. Standalone Hansard intelligence pipeline. Zero contacts needed, public data only. This is the cold-start product that builds the audience before the platform launches.

**Stack**: Django REST + Neon (PostgreSQL) + Gemini Flash API, hosted on Cloud Run. Phase 0 is backend-only (Django admin + templates for the review UI). Next.js frontend arrives in Phase 1 for the public-facing map.

**Why Neon, not Supabase**: Both Supabase free-tier slots are taken (HalaTuju + MySkills). Supabase Pro is $25/project/month — steep for Phase 0 which only needs a managed PostgreSQL database. SJKTConnect doesn't use Supabase auth (Django handles it), storage, or realtime. Neon's free tier (0.5 GB, 190 compute hours/month, auto-suspend on idle) is a perfect fit. Django doesn't care where the database lives — it's just a `DATABASE_URL` connection string. If the project later needs Supabase platform features (auth, storage), we can migrate the database then.

**Existing assets**:
- `SenaraiSekolahWeb_Januari2026.xlsx` — MOE official school list (528 SJK(T) schools, with PARLIMEN/DUN labels per school)
- `Political Constituencies.csv` — full constituency reference (222 Parliament, 613 DUN, WKT boundary polygons, Indian demographics, MP/ADUN names)
- `பள்ளிகள் - மாநிலம்.xlsx` — TF school database (529 schools, rich contact data: PIBG chair, headmaster, bank details)
- `school_pin_verification.csv` — GPS verification results (476 confirmed, 25 offset, 28 not on Google Maps)
- `verify_school_pins.py` tool (built and tested)
- `tamilschool.org` domain (owned, Google Workspace configured)
- Cloud Run infrastructure (running 3 other TF projects)
- Neon account (free tier — to be created in Sprint 1)

**Data notes**:
- MOE uses formal names (`SEKOLAH JENIS KEBANGSAAN (TAMIL) X`), TF uses short names (`SJK(T) X`) — actual school names are identical after the prefix
- TF has 529 schools vs MOE's 528 — extra school not yet identified
- MOE Excel GPS columns: KOORDINATXX = longitude, KOORDINATYY = latitude

**Established patterns**: Follows the same conventions as MySkills and HalaTuju — split Django settings (base/dev/prod), managed PostgreSQL (Neon instead of Supabase for this project), pytest, Cloud Run Dockerfile, structured JSON logging.

---

## Completed Phases

- **Phase 0: Parliament Watch** — 6 sprints (0.1-0.6). Hansard pipeline, AI analysis, admin review, deployment. 220 tests.
- **Phase 1: The Seed** — 9 sprints (1.1-1.9). Next.js frontend, school/constituency pages, Magic Link auth, school edit, outreach, full stack deployment. 509 tests.

See `CHANGELOG.md` for detailed sprint-by-sprint changes and `docs/retrospective-sprint*.md` for retrospectives.

---

## Phases 2-4 (High-Level Outline)

Each phase will get its own sprint decomposition when we reach it. Run `_workflows/implementation-planning.md` before starting Phase 2.

### Phase 2: The Value (~4-6 sprints)
- Broadcast tool (filter audiences, compose, send)
- News Watch pipeline (Google Alerts to Gemini analysis to response drafts)
- AI Rapid Response (response matrix from PRD Section 5.6.1)
- Monthly Intelligence Blast email
- Subscription management (subscribe/unsubscribe/preferences)
- Magic Link gating for premium resources

### Phase 3: The Platform (~4-6 sprints)
- AI Review Layer (three-tier automated review of school data)
- Field Partner role (view-only, verified visit reports)
- WhatsApp broadcast channels (state-level)
- PIBG Registration Kit (AGM templates + QR code form)
- Weekly digest automation
- Grant alert service (if access confirmed) or MOE circular monitor (fallback)

### Phase 4: The Asset (ongoing)
- One-click Ministry/Parliament briefings
- Historical trend analysis (enrolment over time, parliamentary attention)
- Annual MOE import pipeline
- Published annual MP Scorecard
- Election-ready constituency report cards
- Annual State of Tamil Schools report

---

## Key Assumptions

1. **Phase 0 is Django-only** — no Next.js frontend. Review UI uses Django templates. Public-facing web comes in Phase 1.
2. **Neon free-tier PostgreSQL** for SJKTConnect (Supabase free slots are full; Neon provides managed PostgreSQL without the platform overhead we don't need).
3. **English-only content** for Phase 0. Multilingual support (Tamil/Malay) deferred.
4. **E7 (video clips)** and **E9 (historical baseline)** are "Should" priority in the PRD — deferred to after Phase 0 exit criteria are met.
5. **Project folder**: `SJKTConnect/` (already exists with data files).
6. **Parlimen.gov.my** Hansard PDFs are text-based (no OCR needed).

---

## Total Sprint Count

| Phase | Sprints | Description |
|-------|---------|-------------|
| Phase 0 | 6 | Parliament Watch — standalone intelligence pipeline |
| Phase 1 | ~6-8 | Public map + school pages + Magic Links |
| Phase 2 | ~4-6 | Broadcasts + News Watch |
| Phase 3 | ~4-6 | AI review + partners + WhatsApp |
| Phase 4 | ongoing | Reports, historical analysis, election tools |
| **Total** | **~20-26** | Each sprint = one session, independently shippable, tested, documented |

---

## Verification (Phase 0)

**After each sprint**:
- All tests pass (`pytest`)
- Manual verification of the sprint's deliverable
**Phase 0 complete (Sprint 6 done)**:
- End-to-end pipeline is live: Hansard discovery + download + extract + search + match + AI analysis + admin review + publish
- Cloud Scheduler triggers daily at 8:00 AM MYT
- Admin reviews at https://sjktconnect-api-90344691621.asia-southeast1.run.app/review/
- Remaining: first 5 Parliament Watch reports published (Sprint 0.7 content task)

---

## Change Log

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 0.1 | 2026-02-15 | Elan / TF | Initial roadmap — Phase 0 detailed, Phases 1-4 outlined |
| 0.2 | 2026-02-15 | Elan / TF | Engineer review: repo hygiene pre-step (Sprint 1), variant cataloguing before matching (Sprint 2), public /parliament-watch/ page (Sprint 5) |
| 0.3 | 2026-02-15 | Elan / TF | Data source corrections: constituency data from `Political Constituencies.csv` (not MOE Excel), GPS from verification CSV, detailed data file inventory in Context, manual pre-requisites section (GPS cleanup + 529/528 discrepancy) |
| 0.4 | 2026-02-15 | Elan / TF | Timeline clarification: 6 sprints = 3-6 weeks calendar time. PRD duration updated to match. |
| 0.5 | 2026-02-15 | Elan / TF | Second engineer review — 6 changes: (1) Sprint 1: defer WKT polygon import to Phase 1 — GeoDjango/PostGIS/GDAL not needed until the map is built, avoids dependency pain on Windows/Docker/Cloud Run; (2) Sprint 1: add AuditLog middleware for auto-logging model changes; (3) Sprint 2: add text normalization step before keyword search — MPs use colloquial forms like "SJKT" or "Sekolah Tamil"; store ±500 chars context per mention for downstream entity linking and AI analysis; (4) Sprint 3: add stop word list ("Sekolah", "Tamil", "Jalan", etc.) to prevent false positive fuzzy matches; (5) Sprint 4: explicit token budgeting — send only mention + context to Gemini, not full Hansard (deterministic search is free, AI only classifies); (6) Sprint 5: render snippet + context in review UI instead of full Hansard text — link to original PDF for deep dives. |
| 0.6 | 2026-02-15 | Elan / TF | Database switch: Supabase → Neon (free-tier PostgreSQL). Both Supabase free slots are taken by HalaTuju and MySkills. Supabase Pro is $25/project/month — too steep for Phase 0 which only needs a database (no auth, storage, or realtime). Neon free tier: 0.5 GB, 190 compute hours/month, auto-suspend on idle. Django connects via `DATABASE_URL` — same as Supabase. `pg_trgm` supported. RLS verified via SQL instead of Supabase security advisor. |
