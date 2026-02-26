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
- `tamilschool.org.my` domain (owned, Google Workspace configured)
- Cloud Run infrastructure (running 3 other TF projects)
- Neon account (free tier — to be created in Sprint 1)

**Data notes**:
- MOE uses formal names (`SEKOLAH JENIS KEBANGSAAN (TAMIL) X`), TF uses short names (`SJK(T) X`) — actual school names are identical after the prefix
- TF has 529 schools vs MOE's 528 — extra school not yet identified
- MOE Excel GPS columns: KOORDINATXX = longitude, KOORDINATYY = latitude

**Established patterns**: Follows the same conventions as MySkills and HalaTuju — split Django settings (base/dev/prod), managed PostgreSQL (Neon instead of Supabase for this project), pytest, Cloud Run Dockerfile, structured JSON logging.

---

## Phase 0: Parliament Watch (6 sprints)

**Timeline note**: Each sprint is one focused session, independently shippable. At 1-2 sessions per week, Phase 0 is realistically **3-6 weeks** of calendar time, not "2-3 weeks" as initially estimated in the PRD (now corrected). Sprints are sequenced by dependency — each builds on the previous — so parallelisation is limited.

Parliament Watch is the first product. It monitors Malaysian parliamentary proceedings (Hansard) for Tamil school mentions, produces AI-powered analysis, and queues it for human review before publishing. It requires zero contacts and uses only public data.

### Pre-Requisites (Manual — before Sprint 1)

These must be completed by the user before any coding begins:

1. **GPS cleanup** — Resolve 25 offset pins and 28 missing pins in `school_pin_verification.csv`. Manual task using Google Maps.
2. **529 vs 528 discrepancy** — Identify the extra school in TF's database vs MOE's list. Decide whether to include or exclude it.

---

### Sprint 1: Project Scaffold + Reference Data Import

**Goal**: Django project running locally with 528 schools and constituency data in Neon PostgreSQL.

**Scope**:
- **Pre-step (repo hygiene)**: `.gitignore` (exclude Excel/CSV data files, `.env`, `__pycache__`, etc.), `README.md`, project-level `CLAUDE.md` — created before any Django code
- Django project structure with split settings (base, development, production)
- Models: `School`, `Constituency`, `DUN`, `AuditLog`
- Management command: `import_schools` (reads `SenaraiSekolahWeb_Januari2026.xlsx` → School table, with GPS from `school_pin_verification.csv`)
- Management command: `import_constituencies` (reads `Political Constituencies.csv` → Constituency + DUN tables — **metadata only**: MP/ADUN names, Indian demographics, income/poverty stats. **WKT boundary polygons are deferred to Phase 1** when the map is built, to avoid pulling in GeoDjango + PostGIS + GDAL/GEOS dependencies that Phase 0 doesn't need.)
- AuditLog middleware — auto-log all School/Constituency model changes from Day 1
- Create Neon project (free tier), apply migrations
- Requirements, Dockerfile, environment config, test setup

**Acceptance**: `.gitignore` in place. `import_schools` loads 528 schools. `import_constituencies` loads 122 constituencies (metadata, no geometry). All tests pass. Data visible in Neon console.

**Complexity**: Medium (~15 files) — **this is the densest sprint** (four categories: repo setup, project scaffold, school data, constituency data). If MOE Excel parsing is tricky, it may consume the full session. That's acceptable.

---

### Sprint 2: Hansard Download + Text Extraction + Keyword Search

**Goal**: Pipeline that downloads a Hansard PDF, extracts text, and finds Tamil school mentions.

**Scope**:
- Models: `HansardSitting`, `HansardMention`
- Pipeline module with functions for:
  - Downloading Hansard PDFs from parlimen.gov.my
  - Extracting text using pdfplumber
  - **Text normalization** before search: lowercase, normalize variants (`sjk(t)`, `sjkt`, `s.j.k.(t)`, `sekolah tamil`). MPs speak colloquially — rigid string matching will miss mentions.
  - Keyword search against normalized text
  - Storing extracted mentions with verbatim quotes, page numbers, and **±500 characters of surrounding context** (the context window is needed for entity linking in Sprint 3 and AI analysis in Sprint 4)
- Management command: `process_hansard <url>` — orchestrates the full pipeline for one PDF
- Tests with sample Hansard text fixtures

**Acceptance**: Run against 2-3 real Hansard PDFs. Mentions extracted and stored in database with verbatim quotes and page numbers. **Catalogue school name variants** actually found in real Hansard text (output a list of raw name strings) — this evidence informs Sprint 3's matching design.

**Complexity**: Medium (~12 files)

---

### Sprint 4: Gemini AI Analysis + MP Scorecard

**Goal**: AI classifies each mention and scorecard tracks MP engagement over time.

**Scope**:
- Gemini Flash API integration (**token budgeting**: send only the `verbatim_quote` + ±500 chars context per mention, not the full Hansard. The deterministic keyword search in Sprint 2 does the finding for free — Gemini only classifies what's already found.):
  - Classify mention type (budget / question / policy / throwaway)
  - Assess significance (1-5), sentiment, change indicator
  - Extract MP name, constituency, party
  - Generate AI summary of each mention
- Model: `MPScorecard` — aggregated per MP (total mentions, substantive mentions, questions asked, last mention date)
- Management command: `update_scorecards` — recalculate from all stored mentions
- Constituency context linking: auto-attach school counts when an MP speaks ("Port Dickson has 15 SJK(T)s")
- Content generation: per-sitting brief template (Markdown rendered to HTML)
- Tests: mock Gemini responses, scorecard aggregation logic, template rendering

**Acceptance**: Run against real mentions. AI analysis stored. Scorecard populated with correct aggregations. Per-sitting brief renders cleanly.

**Complexity**: High (~12 files)

---

### Sprint 5: Admin Review Queue + Content Publishing — DONE

8 views, MentionReviewForm, highlight_keywords templatetag, 7 templates, CSS, login/logout. 49 new tests (198 total).

---

### Sprint 6: Deployment + Cloud Scheduler + Documentation

**Goal**: Live on Cloud Run with automated daily Hansard checks during sitting periods.

**Scope**:
- Cloud Run deployment (backend)
- PostgreSQL RLS policies on all tables (applied via Django migration — no Supabase security advisor, so verify manually with `SELECT tablename, rowsecurity FROM pg_tables WHERE schemaname = 'public'`)
- Cloud Scheduler job: daily check for new Hansard PDFs (during sitting periods only)
- Management command: `check_new_hansards` — checks parlimen.gov.my for PDFs not yet processed
- End-to-end test: trigger pipeline on real Hansard, review in admin, approve
- Documentation: `CLAUDE.md` (architecture, deploy commands, env vars), `README.md`
- Retrospective

**Acceptance**: Pipeline runs automatically on Cloud Run. Admin reviews at deployed URL. Phase 0 exit criteria: first 5 Parliament Watch reports published.

**Complexity**: Medium (~10 files)

---

## Phases 1-4 (High-Level Outline)

These are outlined for visibility, not commitment. Each phase will get its own sprint decomposition when we reach it. The roadmap is a living document — re-plan remaining phases at each phase boundary.

### Phase 1: The Seed (~6-8 sprints)
- Import WKT boundary polygons from `Political Constituencies.csv` (deferred from Phase 0 Sprint 1 — requires GeoDjango + PostGIS, only needed when the map is built)
- Next.js frontend setup + public school map (Google Maps JS API, 528 pins)
- School profile pages (SSR for SEO) + constituency pages (122 + 222 DUN)
- Magic Link authentication (MOE email to passwordless verification)
- School data confirm/edit flow
- School image harvest (Google Places/Street View APIs)
- Admin dashboard (verification status, contact management)
- Email outreach to 526 schools (batched 50/day via Brevo)
- Parliament Watch integration with school/constituency pages

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
- RLS enabled on all tables (verified via SQL query)

**After Sprint 6 (Phase 0 complete)**:
- End-to-end: Hansard PDF downloaded, pipeline extracts mentions, AI analyses, admin reviews split-screen, approves, content generated
- Cloud Scheduler triggers daily during sitting periods
- Admin can access review queue at deployed URL
- Exit criteria from PRD: first 5 Parliament Watch reports published, at least 3 receive engagement

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
