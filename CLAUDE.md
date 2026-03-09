# SJK(T) Connect — Project CLAUDE.md

## Architecture

- **Backend**: Django 5.x (backend/)
- **Frontend**: Next.js 14 + App Router + Tailwind CSS (frontend/)
- **Database**: Supabase PostgreSQL (Tamil Foundation org, free tier)
- **AI**: Gemini Flash API (Hansard analysis, Sprint 0.4+)
- **Hosting**: Google Cloud Run (GCP project: `sjktconnect`, org: tamilfoundation.org)
- **Domain**: tamilschool.org

## Project Status

- **Current Phase**: Phase 7 (Quality Consolidation) complete. Sprint 7.1 + 7.2 done.
- **Last Sprint**: 7.2 — Medium Effort Quality Improvements (2026-03-09)
- **Tests**: ~1248 (~966 backend + 282 frontend)
- **Backend URL**: https://sjktconnect-api-748286712183.asia-southeast1.run.app
- **Frontend URL**: https://tamilschool.org (also: https://sjktconnect-web-748286712183.asia-southeast1.run.app)

## Apps

| App | Purpose | Sprint |
|-----|---------|--------|
| `core` | AuditLog, middleware | 0.1 |
| `schools` | School, Constituency, DUN, SchoolLeader models + import commands + utils | 0.1, 3.1 |
| `hansard` | Hansard pipeline (download, extract, search, match, discover) | 0.2-0.3, 0.6 |
| `parliament` | MP model + scrapers, MP Scorecard, review UI, content publishing | 0.4-0.5, 5.3 |
| `accounts` | Magic Link auth, SchoolContact, token/email services | 1.6 |
| `outreach` | SchoolImage, OutreachEmail, image harvesting, email campaigns | 1.8 |
| `subscribers` | Subscriber, SubscriptionPreference, subscribe/unsubscribe/preferences API | 2.1 |
| `broadcasts` | Broadcast, BroadcastRecipient, audience filtering, compose/preview/list UI, monthly blast aggregator | 2.2, 2.7 |
| `newswatch` | NewsArticle, RSS fetcher, article extractor, Gemini AI analysis, admin review queue | 2.5-2.6 |
| `donations` | Donation model, Toyyib Pay service, create/callback/status API | 4.1-4.2 |

## Commands

```bash
# Development
cd backend
python manage.py runserver                    # Start dev server
python manage.py test --keepdb                 # Run backend tests (581 via Django runner)
pytest                                         # Run backend tests (715 via pytest, more thorough)

# Frontend
cd frontend
npm run dev                                    # Start dev server (port 3000)
npm test                                       # Run frontend tests (225 passing)
npm run build                                  # Production build

# AI Analysis (requires GEMINI_API_KEY env var)
python manage.py analyse_mentions              # Analyse unprocessed mentions with Gemini
python manage.py analyse_mentions --dry-run    # Preview what would be processed
python manage.py analyse_mentions --limit 5    # Process max 5 mentions
python manage.py update_scorecards             # Recalculate all MP scorecards

# Data Import
python manage.py import_constituencies        # Load constituencies from data/
python manage.py import_schools               # Load schools from data/ (proper case applied)

# Full Hansard Pipeline (Sprint 5.1 — replaces check_new_hansards --auto-process)
python manage.py run_hansard_pipeline              # Full pipeline (7 steps)
python manage.py run_hansard_pipeline --dry-run     # Preview what each step would do
python manage.py run_hansard_pipeline --skip-calendar  # Skip parlimen.gov.my calendar sync
python manage.py run_hansard_pipeline --skip-analysis  # Skip Gemini AI analysis

# Hansard Pipeline (individual commands)
python manage.py process_hansard <url>                        # Process a single PDF
python manage.py process_hansard <url> --sitting-date YYYY-MM-DD
python manage.py process_hansard <url> --catalogue-variants   # Print variant catalogue
python manage.py process_hansard <url> --skip-matching        # Skip school matching step

# Hansard Discovery
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

# News Watch (Sprint 2.5-2.6)
python manage.py fetch_news_alerts                         # Fetch from configured RSS feeds
python manage.py fetch_news_alerts --url "https://..."     # Fetch from specific feed
python manage.py extract_articles                           # Extract body text (batch of 20)
python manage.py extract_articles --batch-size 50           # Custom batch size
python manage.py analyse_news_articles                      # AI-analyse extracted articles (batch of 10)
python manage.py analyse_news_articles --batch-size 25      # Custom batch size

# Donations (Sprint 4.1-4.2)
python manage.py import_bank_details                        # Import bank details from TF Excel
python manage.py import_bank_details --dry-run              # Preview without saving
python manage.py import_bank_details --file path/to/file    # Custom Excel file

# MP Profiles (Sprint 5.3)
python manage.py import_mp_profiles                         # Scrape parlimen.gov.my + mymp.org.my
python manage.py import_mp_profiles --dry-run               # Preview without saving
python manage.py import_mp_profiles --constituency P078     # Single constituency

# GE15 Election Data (Sprint 5.4)
python manage.py scrape_ge15_results                         # Scrape undi.info API for all constituencies
python manage.py scrape_ge15_results --dry-run               # Preview without saving
python manage.py import_ge15_results data/ge15_results.csv   # Import from CSV fallback

# GPS Pin Verification (Sprint 5.4)
python manage.py verify_school_pins                          # Verify all schools vs Google Places
python manage.py verify_school_pins --state Perak            # Filter by state
python manage.py verify_school_pins --apply --skip CBD7093   # Apply Google coords, skip specific schools
python manage.py verify_school_pins --output data/pins.xlsx  # Custom output path

# News Pipeline (Sprint 2.8)
python manage.py run_news_pipeline                          # Full pipeline: fetch → extract → analyse

# Monthly Intelligence Blast (Sprint 2.7)
python manage.py compose_monthly_blast                       # Draft blast for previous month
python manage.py compose_monthly_blast --month 2026-02       # Specific month
python manage.py compose_monthly_blast --dry-run             # Preview without creating

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
| `DATABASE_URL` | Yes (prod) | Supabase PostgreSQL connection string. Use direct connection (port 5432) for bulk writes; transaction pooler (port 6543) can silently drop writes |
| `SECRET_KEY` | Yes (prod) | Django secret key |
| `DJANGO_SETTINGS_MODULE` | Yes | `sjktconnect.settings.development` or `.production` |
| `GEMINI_API_KEY` | Sprint 0.4+ | Google AI Studio API key |
| `ALLOWED_HOSTS` | Prod | Comma-separated hostnames |
| `CSRF_TRUSTED_ORIGINS` | Prod | Comma-separated origins |
| `CORS_ALLOWED_ORIGINS` | Sprint 1.2+ | Comma-separated origins for CORS (default: `http://localhost:3000`) |
| `NEXT_PUBLIC_API_URL` | Frontend | Backend API URL (default: `http://localhost:8000`) |
| `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY` | Frontend | Google Maps JavaScript API key |
| `NEXT_PUBLIC_GOOGLE_MAPS_MAP_ID` | Frontend | Google Maps Map ID (for AdvancedMarker styling) |
| `TOYYIBPAY_BASE_URL` | Sprint 4.1+ | Toyyib Pay base URL (default: `https://toyyibpay.com`) |
| `TOYYIBPAY_SECRET_KEY` | Sprint 4.1+ (prod) | Toyyib Pay user secret key |
| `TOYYIBPAY_CATEGORY_CODE` | Sprint 4.1+ (prod) | Toyyib Pay bill category code |
| `BREVO_API_KEY` | Sprint 1.6+ (prod) | Brevo transactional email API key (logs to console in dev if absent) |
| `FRONTEND_URL` | Sprint 1.6+ (prod) | Next.js frontend URL for magic link emails (default: `http://localhost:3000`) |
| `GOOGLE_MAPS_API_KEY` | Sprint 1.8+ | Backend Google Maps API key for image harvesting (falls back to `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY`) |
| `GMAIL_CLIENT_ID` | Feedback | OAuth2 client ID for feedback@tamilschool.org Gmail API |
| `GMAIL_CLIENT_SECRET` | Feedback | OAuth2 client secret |
| `GMAIL_REFRESH_TOKEN` | Feedback | OAuth2 refresh token (gmail.readonly scope) |

## Data Files (in `data/`, not in git — too large)

| File | Rows | Purpose |
|------|------|---------|
| `data/SenaraiSekolahWeb_Januari2026.xlsx` | 528 SJK(T) | MOE official school list |
| `data/Political Constituencies.csv` | 613 DUN | Constituency reference data |
| `data/school_pin_verification.csv` | 528 | GPS verification results |
| `data/பள்ளிகள் - மாநிலம்.xlsx` | 529 | TF school database |
| `data/school_pin_verification.xlsx` | 528 | GPS verification (Excel version) |
| `data/district_boundaries.kml` | — | District boundary polygons |

## Database Notes

- Supabase free tier: 500 MB storage, Tamil Foundation org
- Region: Southeast Asia (Singapore) — matches Cloud Run asia-southeast1
- Transaction pooler (port 6543) recommended for Cloud Run serverless **read-heavy** workloads
- **CAUTION**: Pooler (port 6543) can silently drop sequential writes. Use direct connection (port 5432) for bulk data operations (Hansard batch processing, AI analysis). Add `connection.close()` after writes if using pooler.
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
| 1.10 | Done | School page redesign: mentions API, multi-photo harvester, SchoolPhotoGallery, History CTA, News Watch placeholder, map/search links to school pages. Fixed 528 broken image URLs (API key rotation). |
| 2.1 | Done | Subscriber models + subscribe/unsubscribe API. New `subscribers` app with Subscriber + SubscriptionPreference models, service layer, 3 REST endpoints. 51 new tests (560 total). |
| 2.2 | Done | Broadcast models + admin compose UI. New `broadcasts` app with Broadcast + BroadcastRecipient models, audience filtering service, compose/preview/list admin views. 47 new tests (484 total). |
| 2.3 | Done | Broadcast sending + confirmation email. Sender service (Brevo API), per-recipient tracking, rate limiting, management command, confirmation email on subscribe. 32 new tests (516 total). |
| 2.4 | Done | Subscribe/unsubscribe frontend pages. `/subscribe/`, `/unsubscribe/[token]/`, `/preferences/[token]/` pages. SubscribeForm, UnsubscribeConfirmation, PreferencesForm components. API client + types. Footer subscribe link. 33 new frontend tests (683 total). |
| 2.5 | Done | News Watch Pipeline: newswatch app, NewsArticle model, RSS fetcher (Google Alerts), article extractor (trafilatura), 2 management commands, admin. 36 new backend tests (719 total). |
| 2.6 | Done | News AI Analysis + Rapid Response + Review UI: Gemini Flash analysis (relevance, sentiment, summary, schools, urgency), analyse_news_articles command, admin review queue + detail view, approve/reject/toggle-urgent actions. 39 new backend tests (758 total). |
| 2.7 | Done | Monthly Intelligence Blast: blast_aggregator service, compose_monthly_blast command (--month, --dry-run), monthly_blast.html email template (3 sections), reuses Broadcast infrastructure. 23 new backend tests (781 total). |
| 2.8 | Done | News Watch Live + Cloud Scheduler Automation: public news API, real NewsWatchSection component, run_news_pipeline command, Cloud Run Jobs (news-pipeline, monthly-blast), Cloud Scheduler (daily-news, monthly-blast), clickable photo thumbnails. 25 new tests (800 total). |
| 3.1 | Done | Data Quality + School Leadership: to_proper_case/format_phone utils, data migration (528 schools), SchoolLeader model (4 roles), admin inline, public API (name+role only), import scripts updated for data/ folder. 41 new tests (841 total). |
| 3.2 | Done | Frontend Layout Redesign: side-by-side hero, stat cards (Students/Teachers/Grade), leadership section, enrolment breakdown, assistance type mapping. 5 new frontend tests (846 total). |
| 3.3 | Done | i18n Infrastructure: next-intl trilingual (EN/TA/MS), pages under `app/[locale]/`, ~162 strings extracted, LanguageSwitcher, translation completeness tests. 6 new frontend tests (852 total). |
| 3.4 | Done | Homepage, About, Data Provenance & UX: national stats API, hero section, About page, favicon/metadata, MOE jargon translation, CTA reframe, empty state improvements, zero-school constituency filter, data provenance. 25 new frontend + 1 backend test (747 total). |
| 3.5 | Done | Tamil Translation Review + Deployment: 9 Tamil grammar/terminology fixes (vallinam, செய்யறிவு, புலனாய்வு consistency), deployed backend + frontend to production, updated 3 Cloud Run jobs. |
| 3.6 | Done | Footer, Legal, Contact, School Page & Map Filters: footer redesign, 3 legal pages, contact form + API, school page sidebar/leadership/stats redesign, MapFilterPanel with coloured pins (4 modes), SJKT search fix. 10 new tests (757 total). |
| 3.7 | Done | Map InfoWindow, School Page Polish & Enrolment Filter: enrolment filter hides (not greys) schools above threshold, InfoWindow redesign (image, badges, stats, DUN link), school page 12-col grid with elevated stat cards + info bar + taller gallery with overlay thumbnails. mapInfoWindow i18n namespace. 757 tests (unchanged). |
| 4.1-4.2 | Done | Donations feature: bank_name/bank_account_number/bank_account_name on School, import_bank_details command (202 schools), DuitNow QR endpoint, SupportSchoolCard sidebar, donations Django app (Toyyib Pay), /donate page + thank-you page, DonationForm. 47 new tests (979 total). |
| UI Polish | Done | Hansard display fix (PENDING→visible, briefs ungated), constituency mentions API, news pagination, collapsible map filters, footer social icons, school leadership empty state, news school matching improvement. 8 new tests (988 total). |
| 5.1 | Done | Pipeline Automation: calendar scraper (parlimen.gov.my), auto brief generator, Gemini meeting report generator, unified `run_hansard_pipeline` command (7 steps), WAT workflow. 30 new tests. |
| 5.3 | Done | MP Contact Card: MP model, scrapers (parlimen.gov.my + mymp.org.my), import_mp_profiles command, ContactMPCard sidebar component, API nesting, trilingual i18n. 222 MPs imported. 24 new tests (1037 total). |
| 5.4 | Done | Electoral Influence + GPS: GE15 election fields, electoral influence API (ratio/verdict), ElectoralInfluenceCard with capsule power meter + DOSM/Wikipedia links, scrape/import GE15 commands, verify_school_pins command (Google Places), 519 schools GPS-corrected, constituency page redesign, clickable MiniMap pin. 16 new tests (1053 total). |
| 5.2 | Done | Historical Rebuild: improved speaker extraction (YAB/Tun/Menteri Besar, 2-page lookback), tightened Gemini prompt (significance scale, speaker hint), MP resolver (cross-ref 222 MPs), rebuild_all_hansards command, full rebuild of 97 sittings → 193 mentions, 193 AI-analysed, 165 MP-resolved, 32 scorecards. 18 new tests. |
| 5.5 | Done | Intelligence Report Quality: rewritten brief/report prompts (journalistic style, JSON response mode), Imagen 4.0 editorial cartoons, illustration API + frontend display, Gemini thinking budget fix, news auto-triage. Deployed to production. |
| 5.6 | Done | Report Quality Fixes: PDF text artefact cleanup (clean_extracted_text), SJK(T) bracket post-processing, journalistic MP Scorecard taxonomy (Stance/Impact/Ministerial Response), lead paragraph blurb extraction, illustration ethnicity fix. Tested on 1st Meeting 2025. |
| Quality Engine | Done | Self-correcting report engine: 4-layer architecture (Generator→Evaluator→Corrector→Learner). QualityLog model, quality_flag on briefs/reports, evaluator service (Gemini rubric scoring, fail-open), corrector (re-prompt + code fix, 3-attempt circuit breaker), school name repairer (comma/filler/fuzzy), learner (pattern detection), brief + report generator integration. 46 new tests (898 total). |
| Full Rebuild | Done | Complete wipe and rebuild of all 15th Parliament Hansard data (Dec 2022 - Mar 2026). 13 meetings, 286 sittings, 204 mentions, 203 analysed, 67 matched, 53 MP scorecards, 71 briefs, 11 reports with illustrations. Fixed 2nd Meeting 2025 report bloat (108KB→8KB). Deployed to production. |
| 6.1 | Done | Foundation & Data Layer: report context JSON v2.0 (cabinet, glossary, RPM 2026-2035, taxonomy), context_builder service, MP portfolio field + scraper, executive_response_attribution rubric criterion, dedup fix (speaker+page), "without Ladang" aliases (294 schools), WAT context-maintenance workflow. 22 new tests (920 total). |
| 6.2 | Done | Pipeline Prompts: wired context_builder into all 3 Gemini prompts (mentions, briefs, reports). Past tense enforcement. Brief generator now Gemini-powered prose (exec summary → details → quotes) with template fallback. Report prompt restructured with cabinet reference, taxonomy definitions, RPM alignment. Validated on 3rd Meeting 2025 — all 5 FLAGs resolved. 8 new tests (928 total). |
| 6.3 | Done | Frontend & Polish: brief detail page (`/parliament-watch/sittings/[id]`), `_linkify_briefs` links sitting dates in reports to brief pages, BriefsList "Full page" link, i18n (EN/TA/MS). Deployed backend + frontend. Updated Cloud Run job image. Ran `seed_aliases --clear` + `import_mp_profiles` on production. 2 new tests (930 total). Phase 6 complete. |
| 7.1 | Done | Pipeline Quality Quick Wins: speaker verification on mentions, brief correction loop (3-attempt evaluate→correct), evaluator fail-safe (AMBER on API errors), context staleness warning. 13 new tests (~943 total). |
| 7.2 | Done | Medium Effort Quality: fuzzy school matching in linkification, MP name normalisation (honorific stripping), deterministic mention-level evaluator, unified quality_loop.py framework. 23 new tests (~966 total). Phase 7 complete. |

## Production Infrastructure (Sprint 1.9)

- **GCP Project**: `sjktconnect` (org: tamilfoundation.org, account: admin@tamilfoundation.org)
- **Backend**: https://sjktconnect-api-748286712183.asia-southeast1.run.app
- **Frontend**: https://sjktconnect-web-748286712183.asia-southeast1.run.app
- **Cloud Run services**: `sjktconnect-api`, `sjktconnect-web` (asia-southeast1)
- **Cloud Run jobs**: `sjktconnect-check-hansards` (Hansard pipeline), `sjktconnect-news-pipeline` (daily news fetch→extract→analyse), `sjktconnect-news-digest` (fortnightly compose+send), `sjktconnect-urgent-alerts` (daily check+send), `sjktconnect-monthly-blast` (1st of month compose+send), `sjktconnect-process-feedback` (Gmail fetch→classify→auto-respond)
- **Cloud Scheduler**: `sjktconnect-daily-check` (8:00 AM MYT daily, Hansard), `sjktconnect-daily-news` (8:30 AM MYT daily, news pipeline), `sjktconnect-urgent-alerts` (9:30 AM MYT daily), `sjktconnect-fortnightly-digest` (9:00 AM MYT, 1st+3rd Monday), `sjktconnect-monthly-blast` (9:00 AM 1st of month), `sjktconnect-process-feedback` (8AM/12PM/4PM/8PM MYT daily)
- **Email**: Brevo transactional API, senders: noreply@tamilschool.org + feedback@tamilschool.org (both DKIM+DMARC verified). Google Workspace for inbound.
- **Maps API key**: Set in Dockerfile + Cloud Run (restricted to Maps JS, Static Maps, Places + referrer-restricted to tamilschool.org)
- **Health check**: `/health/` returns `{"status": "ok"}`
- **Admin**: `/admin/` (username: admin, email: admin@tamilfoundation.org)
- **Old project** (`gen-lang-client-0871147736`): old sjktconnect-api deleted (2026-03-01)

## Next Sprint

**Current state**: Phase 7 (Quality Consolidation) complete. Sprint 7.1 + 7.2 done. ~966 backend + 282 frontend = ~1248 tests. Not yet deployed (backend-only changes, no urgency).

**Phase 7 deliverables summary**:
- Speaker verification + mention-level evaluator (deterministic quality checks)
- Brief correction loop (mirrors report pattern)
- Evaluator fail-safe (AMBER on API errors)
- MP name normalisation (honorific stripping)
- Fuzzy school matching in reports
- Unified quality_loop.py framework
- Context staleness warning

**Next phase candidates** (no sprint planned):
- Urgent Response System (design approved, see `docs/plans/2026-03-04-urgent-response-system-design.md`)
- MP profile pages (combine Hansard data with contact info)
- Pre-filled advocacy message templates per school

**Pending (not sprint-specific)**:
- Deploy Phase 7 changes to production
- Test each email type end-to-end (Parliament Watch, News Digest, Urgent Alert, Monthly Blast)
- End-to-end test: donate page → Toyyib sandbox, school bank card display
- gcloud CLI requires `CLOUDSDK_PYTHON` env var pointing to Python 3.13

## Frontend (Sprint 1.3–3.3)
- **Stack**: Next.js 14, App Router, Tailwind CSS, TypeScript, next-intl (i18n)
- **Map**: `@vis.gl/react-google-maps` + `@googlemaps/markerclusterer`
- **API client**: `lib/api.ts` — auto-paginates, school/constituency/DUN detail, GeoJSON, mentions, edit/confirm
- **School profiles**: `/school/[moe_code]` — ISR, SEO, SchoolPhotoGallery (hero + thumbnails), Breadcrumb, ClaimButton, EditSchoolLink, SchoolProfile, MiniMap, MentionsSection, NewsWatchSection, SchoolHistory CTA, ConstituencySchools sidebar
- **School edit**: `/school/[moe_code]/edit/` — pre-filled edit form, confirm (2-click) + edit actions, auth-gated
- **Constituency pages**: `/constituency/[code]` — ISR, ContactMPCard (photo + email/call/Facebook), scorecard, boundary map, demographics, school table, DUN list
- **DUN pages**: `/dun/[id]` — ISR, demographics, boundary map, school table, constituency link
- **Constituencies index**: `/constituencies/` — filterable table with state dropdown
- **Claim flow**: `/claim/` (email form), `/claim/verify/[token]/` (verification). ClaimForm component with pre-fill, loading/success/error states.
- **Auth API**: `requestMagicLink`, `verifyMagicLink`, `fetchMe` — session-based via credentials: "include"
- **Edit API**: `fetchSchoolEdit`, `updateSchool`, `confirmSchool` — session-based, school ownership validated server-side
- **Subscriber pages** (Sprint 2.4): `/subscribe/` (form), `/unsubscribe/[token]/` (one-click), `/preferences/[token]/` (toggle categories). SubscribeForm, UnsubscribeConfirmation, PreferencesForm components. Footer subscribe link.
- **Subscriber API**: `subscribe`, `unsubscribe`, `fetchPreferences`, `updatePreferences` — public, no auth required
- **i18n** (Sprint 3.3): Trilingual (EN/TA/MS) via next-intl. Pages under `app/[locale]/`. ~162 strings in `messages/{en,ta,ms}.json`. LanguageSwitcher in Header. All links via `@/i18n/navigation`.
- **Homepage** (Sprint 3.4): HeroSection with mission statement, NationalStats bar (schools/students/constituencies from API), About link
- **About page** (Sprint 3.4): `/about/` — mission, methodology, team, data sources
- **Data provenance** (Sprint 3.4): MOE source attribution on SchoolProfile and Footer, social proof on SubscribeForm
- **MOE jargon translation** (Sprint 3.4): `lib/translations.ts` — translates enrolment categories, grade levels from Malay to English
- **Contact page** (Sprint 3.6): `/contact/` — ContactForm (name/email/subject/message), backend API via Brevo
- **Legal pages** (Sprint 3.6): `/privacy/`, `/terms/`, `/cookies/` — trilingual
- **Footer** (Sprint 3.6): Dark bg, copyright + social icons left, Platform + Legal link columns right
- **Map filters** (Sprint 3.6): MapFilterPanel replaces StateFilter — 4 colour modes (Assistance/Location/Programmes/Enrolment), toggle switches, enrolment slider, dynamic pin colours. Enrolment mode hides schools above threshold (Sprint 3.7).
- **Map InfoWindow** (Sprint 3.7): School image/placeholder, assistance + location badges, 3-stat row (students, teachers, ratio), constituency + DUN links, "View School" CTA button. `mapInfoWindow` i18n namespace.
- **School page** (Sprint 3.6-3.7): 12-col grid (7/5 split), 3 elevated stat cards with SVG icons, preschool/special info bar, top-aligned title, metadata chip, taller gallery (400px) with overlay thumbnails, sidebar with constituency/DUN links + MiniMap + nearby schools, leadership always shown
- **Donate page** (Sprint 4.2): `/donate/` — DonationForm (preset amounts, custom, donor info → Toyyib Pay), `/donate/thank-you/` — payment status display
- **SupportSchoolCard** (Sprint 4.1): Sidebar card on school pages showing bank details + DuitNow QR. Hidden for schools without bank data. Bank fields editable via SchoolEditForm.
- **Tests**: Jest + React Testing Library (265 tests)
- **Build**: Standalone output, 107 kB first load JS
- **Dockerfile**: Multi-stage (deps → build → runner), port 8080
- **Env vars**: `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY`, `NEXT_PUBLIC_GOOGLE_MAPS_MAP_ID`

## REST API (Sprint 1.2+)
- All endpoints under `/api/v1/` — paginated (50/page via `?page=N`)
- **Schools**: `GET /api/v1/schools/` (filters: `?state=`, `?ppd=`, `?constituency=`, `?skm=true`, `?min_enrolment=`, `?max_enrolment=`), `GET /api/v1/schools/<moe_code>/` (includes `leaders` array: name + role_display, ordered: Chairman → HM → PTA → Alumni), `GET /api/v1/schools/national-stats/` (total schools, students, teachers, constituencies — Sprint 3.4)
- **School Mentions** (Sprint 1.10): `GET /api/v1/schools/<moe_code>/mentions/` (approved parliamentary mentions, public, no pagination)
- **School News** (Sprint 2.8): `GET /api/v1/schools/<moe_code>/news/` (approved news articles mentioning a school, public)
- **School Edit** (Sprint 1.7, Magic Link auth): `GET/PUT /api/v1/schools/<moe_code>/edit/` (view/update school data), `POST /api/v1/schools/<moe_code>/confirm/` (2-click verify)
- **Constituencies**: `GET /api/v1/constituencies/` (filter: `?state=`, includes `school_count`), `GET /api/v1/constituencies/<code>/` (nested schools + scorecard + mp contact data), `GET /api/v1/constituencies/<code>/mentions/` (Hansard mentions for constituency MP, excludes rejected)
- **DUNs**: `GET /api/v1/duns/` (filters: `?state=`, `?constituency=`), `GET /api/v1/duns/<pk>/` (nested schools)
- **Scorecards**: `GET /api/v1/scorecards/` (filters: `?constituency=`, `?party=`), `GET /api/v1/scorecards/<pk>/`
- **Briefs**: `GET /api/v1/briefs/` (published only), `GET /api/v1/briefs/<pk>/`
- **Meetings** (Sprint 5.1+): `GET /api/v1/meetings/` (reports with sitting/mention counts), `GET /api/v1/meetings/<pk>/`, `GET /api/v1/meetings/<pk>/illustration/` (PNG editorial cartoon, 404 if none)
- **Search**: `GET /api/v1/search/?q=<query>` — searches schools (name, code) and constituencies (name, code, MP name). Min 2 chars.
- **Subscribers** (Sprint 2.1, public): `POST /api/v1/subscribers/subscribe/` (create subscriber, idempotent), `GET /api/v1/subscribers/unsubscribe/<token>/` (one-click unsubscribe), `GET/PUT /api/v1/subscribers/preferences/<token>/` (view/update category toggles)
- **Contact** (Sprint 3.6): `POST /api/v1/contact/` (name, email, subject, message → Brevo email, 3/hour rate limit)
- **DuitNow QR** (Sprint 4.1): `GET /api/v1/schools/<moe_code>/duitnow-qr/` (PNG QR code with bank details, 404 if no bank data)
- **Donations** (Sprint 4.2): `POST /api/v1/donations/` (create donation → Toyyib redirect URL), `POST /api/v1/donations/callback/` (Toyyib server callback), `GET /api/v1/donations/status/?order_id=` (check payment status)
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
- **News Watch review** (Sprint 2.6): `/dashboard/news/` (login required) — queue with urgency/status filters, detail view with split-screen (article body + AI analysis), approve/reject/toggle-urgent actions

## Gemini AI Notes
- Uses `google.genai` SDK (not deprecated `google.generativeai`)
- Model: `gemini-2.5-flash` with JSON response mode and temperature 0.1 (Paid Tier 1: 1000 RPM, 10K RPD)
- Token budgeting: sends mention + context only (~1500 chars), never full Hansard
- Structured output: mp_name, constituency, party, mention_type, significance (1-5), sentiment, change_indicator, summary
- All Gemini calls are mocked in tests — no API key needed for test suite
- Scorecard recalculation is idempotent — safe to run multiple times
- Brief generator falls back to all analysed mentions if none are approved yet

## Hansard Pipeline Notes
- parlimen.gov.my has invalid SSL cert — downloader uses verify=False for that domain
- PDF date format: DR-DDMMYYYY.pdf (e.g. DR-26012026.pdf = 26 Jan 2026)
- Real variants found so far: "sjk(t)", "sekolah jenis kebangsaan tamil"
- Not every sitting mentions Tamil schools — out of 97 sittings across 5 sessions (Feb 2025 – Mar 2026), 33 had mentions
- parlimen.gov.my now blocks HEAD requests (403) — scraper uses ranged GET (`Range: bytes=0-0`) instead
- Non-sitting days (Fridays, recesses) return HTML (HTTP 200) instead of PDF — pdfplumber fails with "No /Root object". These are correctly marked FAILED.
- Normaliser handles: SJK(T), SJKT, S.J.K.(T), S.J.K(T), non-breaking spaces, whitespace collapse

## School Matching Notes
- Matcher uses two passes: exact alias match (100% confidence), then trigram similarity (Python fallback on SQLite)
- pg_trgm migration is conditional — skips on SQLite, applies on PostgreSQL
- `seed_aliases` generates ~4 aliases per school: official, short, stripped prefix, SJKT variant
- Candidate extractor stops at Malay boundary words (dan, di, yang, untuk, memerlukan, etc.)
- Progressive shortening: candidates trimmed word-by-word from right to find exact matches
- Confidence < 80% → needs_review = True. Exact matches always 100%.
