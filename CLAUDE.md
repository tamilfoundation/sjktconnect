# SJK(T) Connect — Project CLAUDE.md

## Architecture

- **Backend**: Django 5.x (backend/)
- **Frontend**: Next.js 14 + App Router + Tailwind CSS (frontend/)
- **Database**: Supabase PostgreSQL (Tamil Foundation org, free tier)
- **AI**: Gemini Flash API (Hansard analysis, Sprint 0.4+)
- **Hosting**: Google Cloud Run (GCP project: `sjktconnect`, org: tamilfoundation.org)
- **Domain**: tamilschool.org

## Project Status

- **Current Phase**: Phase 2 in progress.
- **Last Sprint**: 2.1 (closed 2026-03-01)
- **Tests**: 560 passing (426 backend + 134 frontend)
- **Backend URL**: https://sjktconnect-api-748286712183.asia-southeast1.run.app
- **Frontend URL**: https://tamilschool.org (also: https://sjktconnect-web-748286712183.asia-southeast1.run.app)

## Apps

| App | Purpose | Sprint |
|-----|---------|--------|
| `core` | AuditLog, middleware | 0.1 |
| `schools` | School, Constituency, DUN models + import commands | 0.1 |
| `hansard` | Hansard pipeline (download, extract, search, match, discover) | 0.2-0.3, 0.6 |
| `parliament` | MP Scorecard, review UI, content publishing | 0.4-0.5 |
| `accounts` | Magic Link auth, SchoolContact, token/email services | 1.6 |
| `outreach` | SchoolImage, OutreachEmail, image harvesting, email campaigns | 1.8 |
| `subscribers` | Subscriber, SubscriptionPreference, subscribe/unsubscribe/preferences API | 2.1 |

## Commands

```bash
# Development
cd backend
python manage.py runserver                    # Start dev server
pytest                                        # Run backend tests (375 passing)

# Frontend
cd frontend
npm run dev                                    # Start dev server (port 3000)
npm test                                       # Run frontend tests (134 passing)
npm run build                                  # Production build

# AI Analysis (requires GEMINI_API_KEY env var)
python manage.py analyse_mentions              # Analyse unprocessed mentions with Gemini
python manage.py analyse_mentions --dry-run    # Preview what would be processed
python manage.py analyse_mentions --limit 5    # Process max 5 mentions
python manage.py update_scorecards             # Recalculate all MP scorecards

# Data Import
python manage.py import_constituencies        # Load constituencies from CSV
python manage.py import_schools ../SenaraiSekolahWeb_Januari2026.xlsx

# Hansard Pipeline
python manage.py process_hansard <url>                        # Full pipeline
python manage.py process_hansard <url> --sitting-date YYYY-MM-DD
python manage.py process_hansard <url> --catalogue-variants   # Print variant catalogue
python manage.py process_hansard <url> --skip-matching        # Skip school matching step

# Hansard Discovery (Sprint 0.6)
python manage.py check_new_hansards              # Discover new PDFs (last 14 days)
python manage.py check_new_hansards --days 30    # Last 30 days
python manage.py check_new_hansards --auto-process  # Discover + process automatically
python manage.py check_new_hansards --start 2026-01-01 --end 2026-03-31

# School Name Matching
python manage.py seed_aliases                 # Generate aliases for all 528 schools
python manage.py seed_aliases --clear         # Re-seed (delete non-HANSARD aliases first)

# Outreach (Sprint 1.8)
python manage.py harvest_school_images                     # Harvest images (satellite + places)
python manage.py harvest_school_images --limit 10          # Sample: 10 schools
python manage.py harvest_school_images --source satellite  # Satellite only
python manage.py harvest_school_images --state Johor       # Filter by state
python manage.py harvest_school_images --dry-run           # Preview
python manage.py send_outreach_emails                      # Send outreach emails
python manage.py send_outreach_emails --limit 50           # Batch: 50 emails
python manage.py send_outreach_emails --state Johor        # Filter by state
python manage.py send_outreach_emails --dry-run            # Preview

# Deployment (verify account first!)
gcloud config set account admin@tamilfoundation.org
gcloud config set project sjktconnect
# Backend
cd backend && gcloud run deploy sjktconnect-api --source . --region asia-southeast1 --allow-unauthenticated
# Frontend
cd frontend && gcloud run deploy sjktconnect-web --source . --region asia-southeast1 --allow-unauthenticated
# After backend deploy, update the job image:
gcloud run jobs update sjktconnect-check-hansards --image <new-image> --region asia-southeast1

# Cloud Run Job (manual trigger)
gcloud run jobs execute sjktconnect-check-hansards --region asia-southeast1
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes (prod) | Supabase PostgreSQL connection string (transaction pooler, port 6543) |
| `SECRET_KEY` | Yes (prod) | Django secret key |
| `DJANGO_SETTINGS_MODULE` | Yes | `sjktconnect.settings.development` or `.production` |
| `GEMINI_API_KEY` | Sprint 0.4+ | Google AI Studio API key |
| `ALLOWED_HOSTS` | Prod | Comma-separated hostnames |
| `CSRF_TRUSTED_ORIGINS` | Prod | Comma-separated origins |
| `CORS_ALLOWED_ORIGINS` | Sprint 1.2+ | Comma-separated origins for CORS (default: `http://localhost:3000`) |
| `NEXT_PUBLIC_API_URL` | Frontend | Backend API URL (default: `http://localhost:8000`) |
| `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY` | Frontend | Google Maps JavaScript API key |
| `NEXT_PUBLIC_GOOGLE_MAPS_MAP_ID` | Frontend | Google Maps Map ID (for AdvancedMarker styling) |
| `BREVO_API_KEY` | Sprint 1.6+ (prod) | Brevo transactional email API key (logs to console in dev if absent) |
| `FRONTEND_URL` | Sprint 1.6+ (prod) | Next.js frontend URL for magic link emails (default: `http://localhost:3000`) |
| `GOOGLE_MAPS_API_KEY` | Sprint 1.8+ | Backend Google Maps API key for image harvesting (falls back to `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY`) |

## Data Files (not in git — too large)

| File | Rows | Purpose |
|------|------|---------|
| `SenaraiSekolahWeb_Januari2026.xlsx` | 528 SJK(T) | MOE official school list |
| `Political Constituencies.csv` | 613 DUN | Constituency reference data |
| `school_pin_verification.csv` | 528 | GPS verification results |
| `பள்ளிகள் - மாநிலம்.xlsx` | 529 | TF school database |

## Database Notes

- Supabase free tier: 500 MB storage, Tamil Foundation org
- Region: Southeast Asia (Singapore) — matches Cloud Run asia-southeast1
- Transaction pooler (port 6543) recommended for Cloud Run serverless
- Supports pg_trgm (needed for Sprint 0.3 fuzzy matching)
- Django connects via `DATABASE_URL` using dj-database-url

## Sprint History

| Sprint | Status | Summary |
|--------|--------|---------|
| 0.1 | Done | Scaffold + 528 schools + 222 constituencies + 613 DUNs imported. 26 tests. |
| 0.2 | Done | Hansard pipeline: download, extract, normalise, keyword search. 44 new tests (70 total). Tested on 3 real PDFs — 5 mentions found. |
| 0.3 | Done | School name matching: SchoolAlias + MentionedSchool models, seed_aliases command, matcher (exact + trigram), stop words. 41 new tests (111 total). |
| 0.4 | Done | Gemini AI analysis + MP Scorecard: parliament app, gemini_client (google.genai SDK), scorecard aggregation, brief generator, 2 management commands. 38 new tests (149 total). |
| 0.5 | Done | Admin Review Queue + Content Publishing: 8 views, MentionReviewForm, highlight_keywords templatetag, 7 templates, CSS, URL wiring, login/logout. 49 new tests (198 total). |
| 0.6 | Done | Deployment: Cloud Run + Supabase PostgreSQL, check_new_hansards discovery command, Cloud Scheduler (daily 8am MYT), health check, README. 22 new tests (220 total). |
| 1.1 | Done | WKT boundary import + GeoJSON API: boundary_wkt on Constituency/DUN, shapely + DRF, 4 GeoJSON endpoints. 19 new tests (239 total). |
| 1.2 | Done | REST API: School/Constituency/DUN/Scorecard/Brief endpoints, search, CORS, pagination. 37 new tests (276 total). |
| 1.3 | Done | Next.js frontend: Google Maps + 528 school pins + clustering, state filter, search typeahead, Dockerfile. 26 new tests (302 total). |
| 1.4 | Done | School profile pages: ISR route, SchoolProfile, StatCard, Breadcrumb, ClaimButton, MiniMap, MentionsSection, ConstituencySchools sidebar, SEO metadata, loading skeleton. 36 new tests (338 total). |
| 1.5 | Done | Constituency + DUN pages: constituency detail, DUN detail, constituencies index, BoundaryMap, ScorecardCard, DemographicsCard, SchoolTable, ConstituencyList. 36 new tests (374 total). |
| 1.6 | Done | Magic Link auth: accounts app, MagicLinkToken + SchoolContact, Brevo email, claim pages, @moe.edu.my validation, session auth. 47 new tests (421 total). |
| 1.7 | Done | School Data Confirm/Edit + Admin Dashboard: IsMagicLinkAuthenticated permission, edit/confirm API, Next.js edit page, verification dashboard. 51 new tests (472 total). |
| 1.8 | Done | Outreach app: SchoolImage + OutreachEmail models, image harvesting (satellite + Places), email outreach (Brevo), image_url on API, SchoolImage component. 37 new tests (509 total). |
| 1.9 | Done | Full stack deployment: new GCP project `sjktconnect` (tamilfoundation.org), backend + frontend on Cloud Run, Maps API key, CORS, 528 satellite images harvested, job + scheduler migrated. |
| 2.1 | Done | Subscriber models + subscribe/unsubscribe API. New `subscribers` app with Subscriber + SubscriptionPreference models, service layer, 3 REST endpoints. 51 new tests (560 total). |

## Production Infrastructure (Sprint 1.9)

- **GCP Project**: `sjktconnect` (org: tamilfoundation.org, account: admin@tamilfoundation.org)
- **Backend**: https://sjktconnect-api-748286712183.asia-southeast1.run.app
- **Frontend**: https://sjktconnect-web-748286712183.asia-southeast1.run.app
- **Cloud Run services**: `sjktconnect-api`, `sjktconnect-web` (asia-southeast1)
- **Cloud Run job**: `sjktconnect-check-hansards` — runs `check_new_hansards --auto-process --days 7`
- **Cloud Scheduler**: `sjktconnect-daily-check` — triggers job daily at 8:00 AM MYT
- **Maps API key**: `AIzaSyAsxMjbkpPs5AW75CeEXLjU1jpj02AC6eo` (restricted to Maps JS, Static Maps, Places)
- **Health check**: `/health/` returns `{"status": "ok"}`
- **Admin**: `/admin/` (username: admin, email: admin@tamilfoundation.org)
- **Old project** (`gen-lang-client-0871147736`): old sjktconnect-api deleted (2026-03-01)

## Next Sprint

**Sprint 2.2 — Broadcast Models + Admin Compose UI**
- New `broadcasts` app: `Broadcast` model (subject, html_content, audience_filter JSON, status) + `BroadcastRecipient` (per-email tracking)
- Audience filtering service: filter subscribers by state, district, constituency, enrolment, SKM
- Django admin templates: compose form, preview with recipient count, broadcast list
- Views at `/broadcast/compose/`, `/broadcast/preview/<id>/`, `/broadcast/`
- Depends on Sprint 2.1 (Subscriber model) — now complete
- See `.claude/plans/streamed-munching-bird.md` for full Phase 2 roadmap

## Frontend (Sprint 1.3–1.8)
- **Stack**: Next.js 14, App Router, Tailwind CSS, TypeScript
- **Map**: `@vis.gl/react-google-maps` + `@googlemaps/markerclusterer`
- **API client**: `lib/api.ts` — auto-paginates, school/constituency/DUN detail, GeoJSON, mentions, edit/confirm
- **School profiles**: `/school/[moe_code]` — ISR, SEO, SchoolImage (hero), Breadcrumb, ClaimButton, EditSchoolLink, SchoolProfile, MiniMap, MentionsSection, ConstituencySchools sidebar
- **School edit**: `/school/[moe_code]/edit/` — pre-filled edit form, confirm (2-click) + edit actions, auth-gated
- **Constituency pages**: `/constituency/[code]` — ISR, scorecard, boundary map, demographics, school table, DUN list
- **DUN pages**: `/dun/[id]` — ISR, demographics, boundary map, school table, constituency link
- **Constituencies index**: `/constituencies/` — filterable table with state dropdown
- **Claim flow**: `/claim/` (email form), `/claim/verify/[token]/` (verification). ClaimForm component with pre-fill, loading/success/error states.
- **Auth API**: `requestMagicLink`, `verifyMagicLink`, `fetchMe` — session-based via credentials: "include"
- **Edit API**: `fetchSchoolEdit`, `updateSchool`, `confirmSchool` — session-based, school ownership validated server-side
- **Tests**: Jest + React Testing Library (134 tests)
- **Build**: Standalone output, 107 kB first load JS
- **Dockerfile**: Multi-stage (deps → build → runner), port 8080
- **Env vars**: `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY`, `NEXT_PUBLIC_GOOGLE_MAPS_MAP_ID`

## REST API (Sprint 1.2+)
- All endpoints under `/api/v1/` — paginated (50/page via `?page=N`)
- **Schools**: `GET /api/v1/schools/` (filters: `?state=`, `?ppd=`, `?constituency=`, `?skm=true`, `?min_enrolment=`, `?max_enrolment=`), `GET /api/v1/schools/<moe_code>/`
- **School Edit** (Sprint 1.7, Magic Link auth): `GET/PUT /api/v1/schools/<moe_code>/edit/` (view/update school data), `POST /api/v1/schools/<moe_code>/confirm/` (2-click verify)
- **Constituencies**: `GET /api/v1/constituencies/` (filter: `?state=`, includes `school_count`), `GET /api/v1/constituencies/<code>/` (nested schools + scorecard)
- **DUNs**: `GET /api/v1/duns/` (filters: `?state=`, `?constituency=`), `GET /api/v1/duns/<pk>/` (nested schools)
- **Scorecards**: `GET /api/v1/scorecards/` (filters: `?constituency=`, `?party=`), `GET /api/v1/scorecards/<pk>/`
- **Briefs**: `GET /api/v1/briefs/` (published only), `GET /api/v1/briefs/<pk>/`
- **Search**: `GET /api/v1/search/?q=<query>` — searches schools (name, code) and constituencies (name, code, MP name). Min 2 chars.
- **Subscribers** (Sprint 2.1, public): `POST /api/v1/subscribers/subscribe/` (create subscriber, idempotent), `GET /api/v1/subscribers/unsubscribe/<token>/` (one-click unsubscribe), `GET/PUT /api/v1/subscribers/preferences/<token>/` (view/update category toggles)
- CORS via `django-cors-headers` — origins from `CORS_ALLOWED_ORIGINS` env var
- URL ordering: GeoJSON literal paths before `<str:code>` detail paths to avoid capture conflicts

## GeoJSON API (Sprint 1.1)
- `GET /api/v1/constituencies/geojson/` — all constituency boundaries as FeatureCollection
- `GET /api/v1/constituencies/<code>/geojson/` — single constituency
- `GET /api/v1/duns/geojson/` — all DUN boundaries (filters: `?state=`, `?constituency=`)
- `GET /api/v1/duns/<pk>/geojson/` — single DUN
- Uses shapely for WKT→GeoJSON conversion (not GeoDjango — avoids GDAL/GEOS dependency)
- Constituency boundaries computed by unioning DUN polygons via `shapely.ops.unary_union`

## Review UI & URL Structure (Sprint 0.5)
- Admin review at `/review/` (login required): queue → sitting → mention detail → approve/reject
- Public at `/parliament-watch/` and `/parliament-watch/<sitting_date>/`
- Login/logout at `/accounts/login/` and `/accounts/logout/` (Django built-in)
- `highlight_keywords` templatetag wraps SJK(T) variants in `<mark>` tags
- MentionReviewForm uses TypedChoiceField for significance (IntegerField → coerce=int, empty_value=None)
- Approve saves form edits + sets APPROVED; reject just sets REJECTED + review_notes
- PublishBriefView calls `generate_brief()` then sets `is_published=True`
- **Verification dashboard** (Sprint 1.7): `/dashboard/verification/` (login required) — progress bar, unverified by state, recently verified, registered contacts

## Gemini AI Notes
- Uses `google.genai` SDK (not deprecated `google.generativeai`)
- Model: `gemini-2.0-flash` with JSON response mode and temperature 0.1
- Token budgeting: sends mention + context only (~1500 chars), never full Hansard
- Structured output: mp_name, constituency, party, mention_type, significance (1-5), sentiment, change_indicator, summary
- All Gemini calls are mocked in tests — no API key needed for test suite
- Scorecard recalculation is idempotent — safe to run multiple times
- Brief generator falls back to all analysed mentions if none are approved yet

## Hansard Pipeline Notes
- parlimen.gov.my has invalid SSL cert — downloader uses verify=False for that domain
- PDF date format: DR-DDMMYYYY.pdf (e.g. DR-26012026.pdf = 26 Jan 2026)
- Real variants found so far: "sjk(t)", "sekolah jenis kebangsaan tamil"
- Not every sitting mentions Tamil schools — the Jan-Mar 2026 session had 2/15 sittings with mentions
- Normaliser handles: SJK(T), SJKT, S.J.K.(T), S.J.K(T), non-breaking spaces, whitespace collapse

## School Matching Notes
- Matcher uses two passes: exact alias match (100% confidence), then trigram similarity (Python fallback on SQLite)
- pg_trgm migration is conditional — skips on SQLite, applies on PostgreSQL
- `seed_aliases` generates ~4 aliases per school: official, short, stripped prefix, SJKT variant
- Candidate extractor stops at Malay boundary words (dan, di, yang, untuk, memerlukan, etc.)
- Progressive shortening: candidates trimmed word-by-word from right to find exact matches
- Confidence < 80% → needs_review = True. Exact matches always 100%.
