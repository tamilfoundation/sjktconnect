# SJK(T) Connect — Detailed Implementation Plan

## Context

SJK(T) Connect is an intelligence and advocacy platform for Malaysia's 528 Tamil schools. The PRD defines 5 phases. We have an approved roadmap (v0.6) with Phase 0 broken into 6 sprints at goal/scope level, but lacking task-level detail. Phase 1 has only a high-level outline.

**This plan provides**: Sprint-by-sprint task breakdowns for Phase 0 (6 sprints) and Phase 1 (8 sprints), with model definitions, file lists, test cases, and acceptance criteria. Total: 14 sprints, ~186 files.

**Stack**: Django + Supabase PostgreSQL (free tier) + Gemini Flash API on Cloud Run. Phase 0 is Django-only (templates for review UI). Phase 1 adds Next.js for the public-facing map/pages.

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

### Sprint 0.1: COMPLETED (2026-02-25) — see docs/retrospective-sprint0.1.md

---

### Sprint 0.2: COMPLETED (2026-02-25) — see docs/retrospective-sprint0.2.md

---

### Sprint 0.3: COMPLETED (2026-02-25) — see docs/retrospective-sprint0.3.md

---

### Sprint 0.4: COMPLETED (2026-02-25) — Gemini AI Analysis + MP Scorecard

38 new tests (149 total). parliament app with MPScorecard + SittingBrief models, gemini_client (google.genai SDK), scorecard aggregation, brief generator, 2 management commands.

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

### Sprint 1.1: COMPLETED (2026-02-26) — see docs/retrospective-sprint1.1.md

boundary_wkt on Constituency/DUN, shapely + DRF, 4 GeoJSON endpoints. 19 new tests (239 total).

---

### Sprint 1.2: COMPLETED (2026-02-26) — see docs/retrospective-sprint1.2.md

REST API: 12 endpoints (School/Constituency/DUN/Scorecard/Brief/Search), CORS, pagination. 37 new tests (276 total).

---

### Sprint 1.3: Next.js Frontend + School Map — DONE (2026-02-27, 25 files, 26 tests)

---

### Sprint 1.4: School Profile Pages — DONE (2026-02-27, ISR approach, 36 tests, 338 total)

---

### Sprint 1.5: Constituency + DUN Pages — DONE (2026-02-27, ISR approach, 36 tests, 374 total)

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
2. **~~Neon PostGIS~~ RESOLVED** (Sprint 1.1): Supabase supports PostGIS. Using shapely + TextField approach anyway — avoids GDAL/GEOS dependency on Windows dev + Docker. Upgrade to GeoDjango later if spatial queries needed.
3. **Parlimen.gov.my scraping** (Sprint 0.6): Page structure may change. Build scraper defensively with configurable selectors.
4. **Brevo deliverability** (Sprint 1.6/1.8): Send from tamilschool.org.my (DKIM/SPF/DMARC configured). Batch at 50/day to build reputation.

## Verification

After each sprint: all tests pass (`pytest`), manual verification of deliverable.
After Phase 0 (Sprint 0.6): end-to-end test — Hansard PDF → pipeline → admin review → published brief.
After Phase 1 (Sprint 1.8): map live at tamilschool.org.my, claim flow working, first outreach batch sent.
