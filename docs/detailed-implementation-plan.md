# SJK(T) Connect — Detailed Implementation Plan

## Context

SJK(T) Connect is an intelligence and advocacy platform for Malaysia's 528 Tamil schools. The PRD defines 5 phases. We have an approved roadmap (v0.6) with Phase 0 broken into 6 sprints at goal/scope level, but lacking task-level detail. Phase 1 has only a high-level outline.

**This plan provides**: Sprint-by-sprint task breakdowns for Phase 0 (6 sprints) and Phase 1 (8 sprints), with model definitions, file lists, test cases, and acceptance criteria. Total: 14 sprints, ~186 files.

**Stack**: Django + Neon PostgreSQL (free tier) + Gemini Flash API on Cloud Run. Phase 0 is Django-only (templates for review UI). Phase 1 adds Next.js for the public-facing map/pages.

**Pre-requisites** (user's manual tasks, in progress):
- GPS cleanup: 25 offset + 28 missing pins
- School count discrepancy: RESOLVED (526 match, 2 closed, 1 relocated, 1 new)

---

## Phase Overview

| Phase | Sprints | Goal |
|-------|---------|------|
| **Phase 0** | 0.1 – 0.6 | Parliament Watch — standalone Hansard intelligence pipeline |
| **Phase 1** | 1.1 – 1.8 | The Seed — public map, school/constituency pages, Magic Link auth, outreach |
| Phase 2 | ~4-6 | Broadcasts + News Watch (plan later) |
| Phase 3 | ~4-6 | AI review + WhatsApp + partners (plan later) |
| Phase 4 | ongoing | Reports, elections, historical analysis (plan later) |

---

## Key Model Definitions

### `core` app

**AuditLog** (replicates MySkills pattern)
- `timestamp` DateTimeField(auto_now_add, db_index)
- `user` FK(AUTH_USER_MODEL, null, SET_NULL)
- `action` CharField(100, db_index) — "create", "update", "delete", "import"
- `target_type` CharField(50) — "School", "HansardMention"
- `target_id` CharField(100)
- `detail` JSONField — old/new values, context
- `ip_address` GenericIPAddressField(null)

### `schools` app

**School**
- `moe_code` CharField(10, primary_key) — e.g. "JBD0050"
- `name` CharField(200) — full MOE name
- `short_name` CharField(150) — "SJK(T) Ladang Bikam"
- `name_tamil` CharField(200, blank)
- `address` TextField(blank)
- `postcode` CharField(10, blank)
- `city` CharField(100, blank)
- `state` CharField(50, db_index)
- `ppd` CharField(100, blank)
- `constituency` FK(Constituency, null, SET_NULL)
- `dun` FK(DUN, null, SET_NULL)
- `email` EmailField(blank) — pattern: [CODE]@moe.edu.my
- `phone`, `fax` CharField(30, blank)
- `gps_lat` DecimalField(10,7, null)
- `gps_lng` DecimalField(10,7, null)
- `gps_verified` BooleanField(False)
- `enrolment`, `preschool_enrolment`, `special_enrolment`, `teacher_count` IntegerField
- `grade` CharField(10, blank)
- `assistance_type` CharField(50, blank)
- `session_count` IntegerField(1)
- `session_type` CharField(20, blank)
- `skm_eligible` BooleanField(False)
- `location_type` CharField(50, blank)
- `is_active` BooleanField(True)
- `last_verified` DateTimeField(null)
- `verified_by` CharField(100, blank)
- `created_at`, `updated_at` auto timestamps

**Constituency**
- `code` CharField(10, primary_key) — e.g. "P140"
- `name` CharField(100)
- `state` CharField(50, db_index)
- `mp_name`, `mp_party`, `mp_coalition` CharField
- `indian_population` IntegerField(null)
- `indian_percentage` DecimalField(5,2, null)
- `avg_income` IntegerField(null)
- `poverty_rate`, `gini`, `unemployment_rate` DecimalField(null)
- `created_at`, `updated_at` auto timestamps

**DUN**
- `code` CharField(10, primary_key) — e.g. "N01"
- `name` CharField(100)
- `constituency` FK(Constituency, CASCADE)
- `state` CharField(50, db_index)
- `adun_name`, `adun_party`, `adun_coalition` CharField
- `indian_population` IntegerField(null)
- `indian_percentage` DecimalField(5,2, null)
- `created_at`, `updated_at` auto timestamps

### `hansard` app

**HansardSitting**
- `sitting_date` DateField(unique, db_index)
- `session`, `meeting_number` CharField
- `pdf_url` URLField(500)
- `pdf_filename` CharField(200)
- `total_pages` IntegerField(null)
- `mention_count` IntegerField(0)
- `processed_at` DateTimeField(null)
- `status` CharField — PENDING / PROCESSING / COMPLETED / FAILED
- `error_message` TextField(blank)
- `created_at` auto

**HansardMention**
- `sitting` FK(HansardSitting, CASCADE)
- `page_number` IntegerField(null)
- `verbatim_quote` TextField
- `context_before`, `context_after` TextField(blank) — ~500 chars each
- `keyword_matched` CharField(100, blank)
- AI fields (populated in Sprint 0.4): `mp_name`, `mp_constituency`, `mp_party`, `mention_type` (BUDGET/QUESTION/POLICY/THROWAWAY/OTHER), `significance` (1-5), `sentiment` (ADVOCATING/DEFLECTING/PROMISING/NEUTRAL/CRITICAL), `change_indicator` (NEW/REPEAT/ESCALATION/REVERSAL), `ai_summary`, `ai_raw_response` JSONField
- Review fields (Sprint 0.5): `review_status` (PENDING/APPROVED/EDITED/REJECTED), `reviewed_by`, `reviewed_at`, `review_notes`
- `created_at`, `updated_at` auto

**SchoolAlias**
- `school` FK(School, CASCADE)
- `alias` CharField(200, db_index)
- `alias_normalized` CharField(200, db_index) — lowercase, stripped
- `alias_type` CharField — OFFICIAL / SHORT / MALAY / COMMON / HANSARD
- unique_together: (school, alias_normalized)

**MentionedSchool** (bridge table)
- `mention` FK(HansardMention, CASCADE)
- `school` FK(School, CASCADE)
- `confidence_score` DecimalField(5,2) — 0-100
- `matched_by` CharField — EXACT / TRIGRAM / MANUAL
- `matched_text` CharField(200, blank)
- `needs_review` BooleanField(False)
- unique_together: (mention, school)

### `parliament` app

**MPScorecard**
- `mp_name` CharField(100)
- `constituency` FK(Constituency, null, SET_NULL)
- `party`, `coalition` CharField
- `total_mentions`, `substantive_mentions`, `questions_asked`, `commitments_made` IntegerField(0)
- `last_mention_date` DateField(null)
- `school_count`, `total_enrolment` IntegerField(0) — cached from constituency
- unique_together: (mp_name, constituency)

**SittingBrief**
- `sitting` OneToOneField(HansardSitting, CASCADE)
- `title` CharField(300)
- `summary_html` TextField
- `social_post_text` TextField(blank)
- `email_draft_html` TextField(blank)
- `is_published` BooleanField(False)
- `published_at` DateTimeField(null)

---

## Phase 0: Parliament Watch (6 Sprints)

### Sprint 0.1: Project Scaffold + Reference Data Import

**Goal**: Django project running locally with 528 schools and constituency data in Neon PostgreSQL.

**Tasks**:
1. Create `.gitignore` (exclude `*.xlsx`, `*.csv`, `*.kml`, `.env`, `__pycache__`, `db.sqlite3`, `staticfiles/`, scratch scripts)
2. Create `README.md`, `CLAUDE.md` (following MySkills pattern)
3. Create Django project `sjktconnect` inside `SJKTConnect/backend/`
4. Split settings: `base.py` (en-gb, Asia/Kuala_Lumpur, JSON logging), `development.py` (SQLite fallback), `production.py` (WhiteNoise, dj-database-url, Cloud Run SSL)
5. Create `core` app with `AuditLog` model + AuditLog middleware (post_save/post_delete signals)
6. Create `schools` app with `School`, `Constituency`, `DUN` models
7. Create `import_schools` management command:
   - Read `SenaraiSekolahWeb_Januari2026.xlsx`, filter SJK(T) by JENIS/LABEL
   - Read `school_pin_verification.csv` for verified GPS (override MOE where confirmed)
   - Compute `short_name` by replacing "SEKOLAH JENIS KEBANGSAAN (TAMIL)" with "SJK(T)"
   - Parse PARLIMEN/DUN columns (e.g. "P140 Segamat" -> code + name) to link FKs
   - `--dry-run`, `update_or_create`, `transaction.atomic()`, stats tracking
8. Create `import_constituencies` management command:
   - Read `Political Constituencies.csv` (note: header has typo "Parliment")
   - Parse DUN code/name, Parliament code/name from each row
   - Store MP/ADUN names, party, coalition, demographics
   - Skip WKT column (deferred to Phase 1)
   - Parse "Indians %" ranges and currency amounts ("RM6,399" -> 6399)
   - `--dry-run`, idempotent
9. Create Neon project (free tier), configure `.env`
10. Create `requirements.txt`, `Dockerfile`, `pytest.ini`, `.env.example`
11. Run migrations, import data, verify counts in Django admin

**Files** (~30): `.gitignore`, `README.md`, `CLAUDE.md`, `manage.py`, `sjktconnect/` (5 settings files + urls + wsgi), `core/` (models, middleware, admin), `schools/` (models, admin, 2 management commands), `tests/` (3 test files), `requirements.txt`, `Dockerfile`, `pytest.ini`, `.env.example`

**Tests**:
- School creation, short_name computation, Constituency/DUN FK relationship
- `import_schools`: mock Excel fixture, assert 528 created, GPS override, `--dry-run` no-op, idempotent re-run
- `import_constituencies`: CSV fixture, Constituency + DUN created, demographics parsed, `--dry-run`

**Acceptance**: 528 schools loaded. Constituency + DUN records linked. All tests pass. Data visible in Django admin.

---

### Sprint 0.2: Hansard Download + Text Extraction + Keyword Search

**Goal**: Pipeline that downloads a Hansard PDF, extracts text, and finds Tamil school mentions with context.

**Tasks**:
1. Create `hansard` app with `HansardSitting`, `HansardMention` models
2. Create pipeline modules:
   - `downloader.py`: `download_hansard(url, dest_dir)` — HTTP download with retries
   - `extractor.py`: `extract_text(pdf_path)` — pdfplumber, returns `[(page_number, text)]`
   - `normalizer.py`: `normalize_text(raw)` — lowercase, normalize variants (sjk(t), sjkt, s.j.k.(t), sekolah tamil)
   - `searcher.py`: `search_keywords(pages, keywords)` — find matches, extract verbatim quote + +/-500 chars context
   - `keywords.py`: keyword list + school names from DB
3. Create `process_hansard <url>` management command — orchestrates full pipeline
4. Create sample text fixtures for testing
5. Add `pdfplumber` to requirements

**Files** (~18): `hansard/` (models, admin, pipeline/ with 5 modules, management command, 4 test files, fixture)

**Tests**:
- Normalizer: "SJK(T)", "SJKT", "S.J.K.(T)" all normalize correctly
- Searcher: finds matches, extracts context, handles multiple/zero matches
- `process_hansard`: mock download, use fixture, verify Sitting + Mention records created

**Acceptance**: Run against 2-3 real Hansard PDFs. Mentions extracted with verbatim quotes and page numbers. Catalogue of real name variants printed.

---

### Sprint 0.3: School Name Matching

**Goal**: Link Hansard mentions to specific School records using alias table + trigram matching.

**Tasks**:
1. Add `SchoolAlias`, `MentionedSchool` models to `hansard/models.py`
2. Migration to enable `pg_trgm` extension (TrigramExtension)
3. Create `seed_aliases` command — auto-generate aliases per school (official, short, without prefix, SJKT variant)
4. Create `stop_words.py` — high-frequency words to exclude ("sekolah", "tamil", "jalan", "ladang", etc.)
5. Create `matcher.py` — Pass 1: exact match on `alias_normalized`. Pass 2: trigram similarity (threshold 0.3) with stop words excluded. Confidence < 80% → `needs_review = True`
6. Integrate matcher into `process_hansard` pipeline

**Files** (~9): Modified `models.py`, 2 migrations, `seed_aliases` command, `stop_words.py`, `matcher.py`, modified `process_hansard.py`, 2 test files

**Tests**:
- `seed_aliases`: 3 test schools → correct alias types and normalized forms
- `matcher`: exact match, fuzzy match, no match, multi-school mention, low-confidence flagged

**Acceptance**: Aliases for 528 schools. Mentions linked to schools. High-confidence auto-linked, low-confidence flagged.

---

### Sprint 0.4: Gemini AI Analysis + MP Scorecard

**Goal**: AI classifies each mention; scorecard tracks MP engagement over time.

**Tasks**:
1. Create `parliament` app with `MPScorecard`, `SittingBrief` models
2. Create `gemini_client.py` — wrapper calling Gemini Flash, structured prompt requesting JSON output (mp_name, constituency, party, mention_type, significance, sentiment, change_indicator, summary). Token budgeting: mention + context only (~1500 chars).
3. Create `scorecard.py` — aggregate all mentions per MP, count substantive (significance >= 3), questions (type == QUESTION)
4. Create `brief_generator.py` — generate markdown sitting brief, render to HTML. Also generate social post text.
5. Create `analyse_mentions` command — process unanalysed mentions via Gemini
6. Create `update_scorecards` command — full recalculation
7. Add `google-generativeai`, `markdown` to requirements

**Files** (~15): `parliament/` (models, admin, services/ with 3 modules, 2 management commands, 3 test files)

**Tests** (all Gemini calls mocked):
- `gemini_client`: mock API response, verify fields populated, test error handling
- `scorecard`: 5 mentions for 2 MPs → correct aggregation, substantive count only >= 3
- `brief_generator`: 3 approved mentions → markdown with all summaries, social text <= 280 chars

**Acceptance**: AI analysis stored. Scorecard aggregated correctly. Brief renders cleanly.

---

### Sprint 0.5: Admin Review Queue + Content Publishing

**Goal**: TF Admin reviews AI-drafted content, approves/rejects. Approved content published at `/parliament-watch/`.

**Tasks**:
1. Create Django views:
   - `ReviewQueueView` (login required) — pending mentions grouped by sitting, with counts
   - `MentionDetailView` — split-screen: left = verbatim quote + context with `<mark>` highlights, right = AI analysis (editable form). Link to original PDF.
   - Approve/Edit/Reject POST views — update `review_status`, log to AuditLog
   - `PublishBriefView` — generate SittingBrief, set `is_published = True`
2. Create public views:
   - `/parliament-watch/` — published briefs listed as cards
   - `/parliament-watch/<sitting_date>/` — single brief detail
3. Create templates: `base.html`, `queue.html`, `detail.html`, `watch.html`, `brief.html`, `login.html`
4. Create CSS stylesheet
5. Create keyword highlight template tag
6. Configure Django auth (LOGIN_URL, create superuser)
7. Wire up URLs

**Files** (~15): `parliament/` (views, urls, forms, templatetags/), `templates/` (6 templates), `static/css/`, 2 test files

**Tests**:
- Login required for queue/detail, public views accessible without login
- Approve flow: status changes, AuditLog entry created
- Edit + approve flow, reject flow
- Published brief appears at `/parliament-watch/`

**Acceptance**: Admin logs in, reviews split-screen, approves. Published briefs visible at `/parliament-watch/`.

---

### Sprint 0.6: Deployment + Cloud Scheduler + Documentation

**Goal**: Live on Cloud Run with automated daily Hansard checks.

**Tasks**:
1. Create `check_new_hansards` command — scrape parlimen.gov.my for new PDFs, run pipeline on each
2. Create `scraper.py` — fetch Hansard listing page, extract PDF URLs
3. Create health check endpoint at `/health/`
4. Deploy to Cloud Run (`gen-lang-client-0871147736`, service `sjktconnect-api`, `asia-southeast1`)
5. Configure Cloud Scheduler: daily at 06:00 MYT
6. End-to-end test on deployed instance
7. Update `CLAUDE.md`, `README.md`, create `CHANGELOG.md`
8. Write retrospective

**Files** (~9): `check_new_hansards` command, `scraper.py`, health check view, modified URLs, docs updates, 2 test files

**Tests**:
- Scraper: mock HTTP response, verify PDF URLs extracted
- `check_new_hansards`: mock scraper returns 3 URLs (1 already in DB), only 2 new sittings created

**Acceptance**: Pipeline runs on Cloud Run. Admin reviews at deployed URL. Cloud Scheduler triggers daily. Retrospective written.

---

## Phase 1: The Seed (8 Sprints)

### Sprint 1.1: WKT Boundary Import + GeoJSON API

**Goal**: Import constituency boundary polygons and serve as GeoJSON for the map.

**Risk**: Neon free tier may not support PostGIS. **Fallback**: Store WKT as text, convert to GeoJSON with `shapely` in Python. Frontend renders either way.

**Tasks**:
1. Test PostGIS availability on Neon free tier
2. If available: add GeoDjango, switch DB engine, add `boundary` MultiPolygonField to Constituency, update Dockerfile with GDAL
3. If not: add `boundary_wkt` TextField to Constituency, use `shapely` for WKT→GeoJSON conversion
4. Update `import_constituencies` to parse WKT column
5. Create GeoJSON API endpoint: `GET /api/v1/constituencies/geojson/`
6. Add `djangorestframework` to requirements

**Files** (~10): Modified `schools/models.py`, modified import command, API serializers/views/urls, modified Dockerfile, tests

**Acceptance**: 613 DUN boundaries stored. GeoJSON endpoint returns valid FeatureCollection.

---

### Sprint 1.2: Django REST API for Schools + Constituencies

**Goal**: REST API endpoints exposing all data for the Next.js frontend.

**Tasks**:
1. School API: list (filterable by state, ppd, constituency, enrolment range, skm), retrieve by moe_code
2. Constituency API: list (filterable by state), retrieve with nested schools + scorecard
3. DUN API: list, retrieve
4. MPScorecard API: list, retrieve
5. SittingBrief API: list, retrieve (published only)
6. Search endpoint: `GET /api/v1/search/?q=<query>`
7. Configure CORS for Next.js origin

**Files** (~10): `schools/api/` (serializers, views, urls), `parliament/api/` (serializers, views, urls), modified root urls, 2 test files

**Acceptance**: All endpoints return correct data. Filters, search, pagination work. CORS configured.

---

### Sprint 1.3: Next.js Frontend + School Map

**Goal**: Interactive Google Maps showing 528 school pins with clustering, filters, and search.

**Tasks**:
1. Create Next.js 14 project in `SJKTConnect/frontend/` (App Router, Tailwind CSS)
2. Layout with header, footer, navigation
3. Map page at `/` — full-width Google Maps
4. Fetch 528 schools from API, render as markers with clustering
5. Marker click → info window (name, code, enrolment, link to school page)
6. State filter sidebar (11 states)
7. Search box with typeahead
8. Dockerfile for Next.js

**Files** (~17): `frontend/` — package.json, next.config.js, tailwind.config.js, app/ (layout, page, globals.css), components/ (map, markers, filter, search, header, footer), lib/ (api client, types), Dockerfile

**Acceptance**: Map loads, shows 528 pins, clustering works, state filter narrows pins, search finds schools.

---

### Sprint 1.4: School Profile Pages (SSR)

**Goal**: SEO-friendly page per school with full profile data.

**Tasks**:
1. Dynamic route `app/school/[moe_code]/page.tsx` with `generateStaticParams` (SSG for 528 schools)
2. Profile layout: name, code, address, enrolment, teachers, constituency, DUN, embedded map, grade, SKM status
3. "Claim This Page" CTA button (prominent, above fold)
4. SEO metadata (title, description, Open Graph)
5. Breadcrumbs, "Schools in this constituency" sidebar
6. Parliament Watch mentions section (if any)

**Files** (~8): `frontend/app/school/[moe_code]/` (page, loading), components (profile, mini-map, claim button, breadcrumb, mentions, stat card)

**Acceptance**: 528 school pages generated, SEO metadata present, "Claim This Page" visible.

---

### Sprint 1.5: Constituency + DUN Pages

**Goal**: 122 constituency + 222 DUN pages with school lists and aggregate stats.

**Tasks**:
1. Constituency page: `app/constituency/[code]/page.tsx` with SSG
2. Content: MP name/party, scorecard snapshot, boundary map, demographics, school table, aggregate stats
3. DUN page: `app/dun/[code]/page.tsx`
4. Constituencies index page at `/constituencies/`
5. SEO metadata

**Files** (~9): `frontend/app/constituency/`, `app/dun/`, `app/constituencies/`, components (constituency profile, boundary map, school table, scorecard card, demographics card)

**Acceptance**: 122 + 222 pages with correct data. Scorecard on constituency pages.

---

### Sprint 1.6: Magic Link Authentication

**Goal**: Passwordless login for school reps via MOE email.

**Tasks**:
1. Create `accounts` Django app with `MagicLinkToken` and `SchoolContact` models
2. API: `POST /api/v1/auth/request-magic-link/` — validate @moe.edu.my, match to school, generate token (24h expiry), send via Brevo
3. API: `GET /api/v1/auth/verify/{token}/` — validate, mark used, create/update SchoolContact, return session
4. API: `GET /api/v1/auth/me/`
5. Brevo transactional email integration
6. Next.js claim pages: `/claim/`, `/claim/sent/`, `/claim/verify/[token]/`

**Files** (~14): `accounts/` (models, API views/serializers/urls, services for email + token, admin, 2 test files), `frontend/` (3 claim pages, form component)

**Acceptance**: School rep enters MOE email, receives Magic Link, clicks link, authenticated to their school. Token expires after 24h.

---

### Sprint 1.7: School Data Confirm/Edit + Admin Dashboard

**Goal**: Authenticated reps confirm/edit data. Admin sees verification status.

**Tasks**:
1. API: `GET/PUT /api/v1/schools/{code}/edit/` — Magic Link auth required, saves + logs to AuditLog
2. API: `POST /api/v1/schools/{code}/confirm/` — quick confirm, updates `last_verified`
3. Next.js edit page: pre-filled form, "Confirm" + "Edit" actions
4. Admin dashboard (Django templates): verification progress bar, recently verified, unverified by state, contact management

**Files** (~10): Modified school API, permission class, `frontend/` edit page + components, `templates/admin_dashboard/` (2 templates), tests

**Acceptance**: Confirm in 2 clicks. Edit saves + AuditLog. Admin sees progress.

---

### Sprint 1.8: School Images + Email Outreach + Full Deployment

**Goal**: Harvest images, deploy full stack at tamilschool.org.my, begin outreach.

**Tasks**:
1. Create `outreach` app with `SchoolImage`, `OutreachEmail` models
2. `harvest_school_images` command — Google Places → Street View → Satellite fallback (~$5 total)
3. `send_outreach_emails` command — Brevo, batched 50/day, `--state` filter, `--dry-run`
4. Update school profile page to display primary image
5. Deploy full stack: `sjktconnect-api` (update), `sjktconnect-web` (new), custom domain `tamilschool.org.my`
6. Update docs, write Phase 1 retrospective

**Files** (~12): `outreach/` (models, 2 commands, 2 services, admin, 2 test files), modified frontend image component, docs

**Acceptance**: Images harvested. Frontend at tamilschool.org.my. First outreach batch sent. Phase 1 retrospective written.

---

## Sprint Dependency Map

```
PHASE 0 (Sequential — each blocks the next):

  0.1 Scaffold + Import → 0.2 Hansard Pipeline → 0.3 Matching → 0.4 AI + Scorecard → 0.5 Review UI → 0.6 Deploy

PHASE 1 (Partially parallel after 1.2):

  1.1 WKT Import → 1.2 REST API ─┬─ 1.3 Map → 1.4 School Pages → 1.5 Constituency Pages ─┐
                                  └─ 1.6 Magic Link Auth → 1.7 Edit/Confirm + Admin ────────┤
                                                                                             └─ 1.8 Images + Outreach + Deploy
```

---

## Summary

| Sprint | Goal | Files |
|--------|------|-------|
| 0.1 | Scaffold + 528 schools + constituencies in Neon | ~30 |
| 0.2 | Hansard PDF → text → keyword search | ~18 |
| 0.3 | Alias table + trigram matching | ~9 |
| 0.4 | Gemini AI classification + MP scorecard | ~15 |
| 0.5 | Admin review queue + public /parliament-watch/ | ~15 |
| 0.6 | Cloud Run deployment + scheduler | ~9 |
| **Phase 0** | | **~96** |
| 1.1 | WKT boundary import + GeoJSON API | ~10 |
| 1.2 | REST API for schools/constituencies | ~10 |
| 1.3 | Next.js + interactive school map | ~17 |
| 1.4 | 528 school profile pages (SSR) | ~8 |
| 1.5 | 122 constituency + 222 DUN pages | ~9 |
| 1.6 | Magic Link passwordless auth | ~14 |
| 1.7 | Confirm/edit flow + admin dashboard | ~10 |
| 1.8 | Images + outreach + full deployment | ~12 |
| **Phase 1** | | **~90** |
| **Total** | **14 sprints** | **~186** |

## Risks

1. **Sprint 0.1 density** (30 files): Densest sprint. If MOE Excel parsing is tricky, constituency import can shift to Sprint 0.2 start without blocking.
2. **Neon PostGIS** (Sprint 1.1): Free tier may not support PostGIS. Fallback: store WKT as text, convert with shapely. Map works either way.
3. **Parlimen.gov.my scraping** (Sprint 0.6): Page structure may change. Build scraper defensively with configurable selectors.
4. **Brevo deliverability** (Sprint 1.6/1.8): Send from tamilschool.org.my (DKIM/SPF/DMARC configured). Batch at 50/day to build reputation.

## Verification

After each sprint: all tests pass (`pytest`), manual verification of deliverable.
After Phase 0 (Sprint 0.6): end-to-end test — Hansard PDF → pipeline → admin review → published brief.
After Phase 1 (Sprint 1.8): map live at tamilschool.org.my, claim flow working, first outreach batch sent.
