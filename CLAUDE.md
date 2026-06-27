# SJK(T) Connect — Project CLAUDE.md

## Architecture

- **Backend**: Django 5.x (backend/)
- **Frontend**: Next.js 14 + App Router + Tailwind CSS (frontend/)
- **Database**: Supabase PostgreSQL (Tamil Foundation org, free tier)
- **AI**: Gemini Flash API (Hansard analysis, Sprint 0.4+)
- **Hosting**: Google Cloud Run (GCP project: `sjktconnect`, org: tamilfoundation.org)
- **Domain**: tamilschool.org

## Project Status

- **Current Phase**: **v2.0 series complete** — `v2.0.1` LIVE (tagged 2026-06-26, supersedes earlier v2.0). Production maintenance mode.
- **Last Sprint**: Sprint 30 — v2.0.1 release + Production folder move (closed 2026-06-26) — see CHANGELOG + `docs/release-notes-v2.0.1.md`
- **Tests**: 1803 (1436 backend + 367 frontend) — verified at v2.0 tag.
- **Plan/billing**: Supabase Pro plan (Tamil Foundation org) — was forced to upgrade for headroom; goal is to drive egress low enough to revisit free tier later. Per-route observability dashboard now lives at Cloud Monitoring → "SJK(T) Connect — Egress by Route/UA" (id `f1722366-2df9-4446-9941-7cda5c019615`).
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
| `community` | Suggestion model, create/list/approve/reject API, moderation queue, image management | 8.2 |

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

# Deployment
# Backend
cd backend && gcloud run deploy sjktconnect-api --account admin@tamilfoundation.org --project sjktconnect --source . --region asia-southeast1 --allow-unauthenticated
# Frontend
cd frontend && gcloud run deploy sjktconnect-web --account admin@tamilfoundation.org --project sjktconnect --source . --region asia-southeast1 --allow-unauthenticated
# After backend deploy, sync ALL Cloud Run jobs to the new api image:
./backend/scripts/update_jobs.sh
# This is MANDATORY — jobs carry their own pinned image and won't auto-update.
# Skipping this step caused the 2026-05-20 silent-news-rot incident (21 days
# of news-pipeline crashes after Sprint 19's migration). A Cloud Monitoring
# alert (admin@tamilfoundation.org) now fires on 2+ job failures in 24h.
# See backend/docs/monitoring/job-failure-alert.yaml + backend/scripts/update_jobs.sh.

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
| `BREVO_WEBHOOK_SECRET` | Optional | HMAC secret for Brevo webhook signature verification |

## Data Files (in `data/`, not in git — too large)

| File | Rows | Purpose |
|------|------|---------|
| `data/SenaraiSekolahWeb_April2026.xlsx` | 528 SJK(T) | MOE official school list (April 2026 release; previous: SenaraiSekolahWeb_Januari2026.xlsx) |
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
| 8.1 | Done | Community Admin Panel — Auth + Roles Foundation: UserProfile model, Google auth endpoint, /me update, link-school endpoint, 4 permission classes, NextAuth.js v5, AuthProvider, UserMenu, profile page, dashboard shell. 64 new backend tests (~1030 total). |
| 8.2 | Done | Suggestion Workflow: community app, Suggestion model (3 types, 3 statuses), create/list API, moderation queue, approve/reject with auto-apply, points system, image management API (reorder/delete), SchoolImage position+uploaded_by. Frontend: suggest form, my suggestions, moderation queue, image manager. 43 new backend + 8 new frontend tests (~1363 total). |
| 8.3 | Done | Supabase Egress Optimisation: server-side school map data via ISR (revalidate 24h), lightweight `/api/v1/schools/map/` endpoint (10 fields, ~50 KB), SchoolMap accepts props instead of client-side fetch, news revalidation 5min→24h, welcome email batch tracking. 1363 tests (unchanged). |
| 8.4 | Done | SEO Improvements: hreflang alternate links + canonical URLs on all 22 pages (fixing 69 GSC duplicates), dynamic sitemap.xml with locale alternates (static + 528 schools + constituencies), robots.txt, richer school meta titles ("SJK(T) Name | 450 Students, Grade A | Selangor"), richer constituency meta titles, lib/seo.ts helper with buildAlternates(). Frontend-only, no backend changes. 1363 tests (unchanged). |
| 8.5 | Done | Brevo Webhook Integration: webhook endpoint at /api/v1/webhooks/brevo/ for delivery tracking (delivered, opened, clicked, hard/soft bounce, spam, unsubscribed). Engagement fields on BroadcastRecipient (open_count, click_count, timestamps). Auto-deactivate subscribers after 3 hard bounces. Optional HMAC verification. 19 new backend tests. 1382 tests total. |
| 8.6 | Done | Email Quality & Spam Cleanup: fixed hero image bytes dumped into email HTML (compose_news_digest + compose_parliament_watch), contact form honeypot anti-spam, hard bounce threshold reduced to 1, purged 37 spam + deactivated 44 hard-bounced subscribers. 1382 tests total. |
| Egress Fix | Done | Supabase Egress Optimisation: `.defer("boundary_wkt")` on 6 views (~85% egress reduction), middleware IP blocking (Chrome/91 scraper), robots.txt bot exclusions (AhrefsBot, GPTBot, OAI-SearchBot, Amazonbot, ClaudeBot), Cloud Run `minScale=1`. Investigation report at `docs/egress-investigation-report.md`. 1382 tests (unchanged). |
| News Digest & Urgent Alert Fix | Done | `Broadcast.kind` + `coverage_start_date`/`coverage_end_date` (migration 0006). Digest cadence filters by `kind=NEWS_DIGEST`. Urgency classifier rewritten as two-gate + second-pass verification. `URGENT_ALERT_REQUIRE_REVIEW` dormant feature flag. 18 new tests. |
| Audit & Community Auth | Done | Community Google sign-in unblocked (OAuth External/Production, `SameSite=None` cookies, admin → SUPERADMIN). Fixed 3 Sprint 8.2 bugs (photo base64 prefix, preview, relative image URL). First full-codebase audit since Sprint 0.3: `docs/tech-debt.md` with 15 entries (3 resolved: TD-03 prod-DB guard, TD-08 DRF auth pin, TD-10 next-intl upgrade). Security review patched 2 vulns (suggestion image auth). 3 new backend tests. 1109 backend + 271 frontend tests. Retrospective: `docs/retrospective-audit-community-auth.md`. |
| User Management 11a | Done | Cloudflare reverse proxy adopted (tamilschool.org + api.tamilschool.org, both Cloudflare-proxied with Google-managed SSL). OAuth checks restored to `["pkce", "state"]`. SameSite=None workaround removed. Magic-link system fully deleted (~400 LOC); auto-claim on `@moe.edu.my` Google sign-in (~10 LOC) replaces it. New EmailClaimIndicator component renders inline next to the email — Google-style: claim link when unclaimed, ✓ Verified pill when claimed. SchoolEditView migrated to UserProfile auth. Next 14 → 16 upgrade with global.d.ts shim + async params migration on 5 pages. Resolves TD-01, TD-02, TD-04 + partial TD-10. 1076 backend + 258 frontend tests. Retrospective: `docs/retrospective-user-management-11a.md`. Phase 5 (`/dashboard/users` UI) deferred to Sprint 11b. |
| 12 | Done | User Management UI: SUPERADMIN `/dashboard/users` page with filter/search/table + RoleChangeModal + SchoolAssignModal + deactivate/reactivate; self-demotion safety checks (cannot change own role away from SUPERADMIN, cannot deactivate self). MeView PATCH for self-service display name edit. UserMenu adds "User Management" link for SUPERADMIN. Profile page: editable display name, removed broken `/claim` CTA. 30 new backend tests. **TD-01 re-opened** (regression): Next 16 + Auth.js v5 beta.30 state/PKCE cookie round-trip regressed; `checks: []` workaround reinstated, proper fix deferred to Sprint 16. 1106 backend + 258 frontend tests. |
| 13 | Done | Image Storage Migration: Supabase Storage bucket `school-images` + django-storages[boto3]/Pillow + S3-compat config. SchoolImage gets `image_file` ImageField + `display_url` property (falls back to legacy `image_url`). Harvester rewritten to download bytes + upload via image_file. New `migrate_images_to_storage` command. SchoolMarkers InfoWindow lazy-fetches detail to populate hero photo. Prod migration: 1009 PLACES + 528 SATELLITE re-harvested + 1 COMMUNITY migrated; 5 stuck rows deleted; **1534/1534 (100%) on Supabase Storage**. Resolves TD-05, TD-06, TD-13. 1117 backend (+11) + 258 frontend tests. Cost: ~US$15 in Google API re-harvest. |
| 14 | Done | Community Photo Uploads: Drop `Suggestion.image` BinaryField; new multipart endpoint `POST /schools/<moe>/suggestions/photo/` with Pillow validation (≤5 MB / JPEG/PNG/WebP / ≥640×400 / EXIF strip / 1600px resize / pHash dedup). DRF throttling 5/user/day + 20/school/day via custom scoped throttles. New `IsPhotoApprover` permission (SUPERADMIN OR bound school admin only — MODERATOR excluded). 20-photo cap on approve returns 409 `slot_full`. Reject deletes the staged file. New `POST /schools/<moe>/images/<id>/pin/` makes a photo the hero. Frontend SuggestForm rewritten to multipart with file picker + client-side validation + typed error surfacing. ImageManager gets ⭐ Make hero button. ModerationQueue shows photo preview + clickable school link + slot-full banner. Resolves TD-07 + TD-09 + TD-16 (suggestions-page portion). 28 new backend + 5 new frontend tests; final tally 1145 backend + 286 frontend (1 LLM-flake in parliament/test_brief_generator → TD-17, 1 SubscribeForm flake → TD-15). Deployed `sjktconnect-api-00101-klw` + `sjktconnect-web-00094-gqx`. |
| 15 | Done | Image Display Polish: `SchoolImage.caption` (CharField max 200) + migration `outreach/0005_add_caption`; `PATCH /schools/<moe>/images/<id>/caption/` (IsPhotoApprover); `POST /api/v1/auth/logout/` flushes Django session (fixes frontend/Django session divergence that left Edit button visible after sign-out). Frontend: `PhotoLightbox` wrapper around `yet-another-react-lightbox` (lazy-imported via next/dynamic), gallery click-to-zoom + "View all N photos" overlay, `ImageManager` inline caption editor. SchoolListSerializer image_url switched to `display_url` (fixes map InfoWindow placeholder for Sprint-13-migrated rows). EditSchoolLink + SuggestButton now reactive to NextAuth status; SuggestButton hides for SUPERADMIN + bound admin of the viewed school so Edit/Suggest CTAs are mutually exclusive per role. Public hero caption overlay removed (collided with thumbnail strip on 6+ photo schools); caption preserved in lightbox + admin editor. 10 new backend + 5 new frontend tests; final tally 1155 backend + 285 frontend. Deployed `sjktconnect-api-00104-qm7` + `sjktconnect-web-00102-v4f`. |
| 16 | Done | Code-Quality Pass — final of 5-sprint roadmap. **TD-01 RESOLVED**: bumped next-auth beta.30→beta.31, overrode `@auth/core`'s default csrfToken cookie name to use `__Secure-` prefix instead of `__Host-` (Cloudflare proxy was modifying Set-Cookie in ways that violated `__Host-` semantics, silently dropping the cookie), restored `checks: ["pkce", "state"]`. **TD-18 RESOLVED**: separate root cause from TD-01. Race between UserMenu's syncGoogleAuth (writes Django session) and EditSchoolLink/SuggestButton's fetchMe; new `lib/auth-events.ts` module-scoped pub/sub emitter; UserMenu fires emitProfileReady() after syncGoogleAuth resolves; CTAs subscribe and re-fetch on signal. Both auth fixes user-verified on prod (tamiliam USER + admin SUPERADMIN both confirmed 2026-04-27). **TD-14 RESOLVED**: extracted `_can_moderate_or_owns_school` helper in `community/api/views.py`, replaces 4 inline duplications. **TD-16 RESOLVED**: `.catch(() => router.push("/"))` on `/dashboard/users` fetchMe gate. **TD-15 RESOLVED**: 4 fixed pre-existing test failures inherited from Sprint 15 (mock useSession in EditSchoolLink/SuggestButton tests; honeypot field in SubscribeForm test). **TD-17 RESOLVED**: `@patch.dict` pinning `GEMINI_API_KEY=""` at class level for `test_brief_generator`. **TD-10 RESOLVED**: brace-expansion + picomatch transitive bumps via `npm audit fix`. TD-11 + TD-12 (test-coverage padding) deferred to a future sprint. 1155 backend + 289 frontend tests. Deploys: `web-00102-v4f` → `web-00103-phl` (TD-01) → `web-00104-d4n` (TD-18); `api-00104-qm7` → `api-00105-wwd` (TD-14). |
| 17 | Done | Egress Hardening (hotfix sprint, 2026-04-27 evening). Triggered by 500 MB/day Supabase egress with site not publicised. Found 4 leaks: (a) **ISR DISABLED** — 10 public pages had `revalidate = false` instead of an integer (Sprint 8.3 retro claimed 24h ISR; reality was opposite). Flipped all 10 to `revalidate = 86400`. **Single biggest fix.** (b) **Scraper IP not blocked** — `88.216.210.27` (Chrome/91 fake UA) generating ~1,400 req/day. Egress Fix retro claimed IP-block middleware; never actually landed. New `IPBlockMiddleware` in `core/middleware.py` reads CF-Connecting-IP / XFF / REMOTE_ADDR; returns 403; wired FIRST in middleware chain. 6 unit tests. (c) **Sitemap regenerates per-fetch** — added `revalidate = 86400` to `sitemap.ts`. (d) **News page fetches 500 articles** — reduced to 50. Plus observability: 2 new Cloud Logging metrics + dashboard "SJK(T) Connect — Egress by Route/UA" with route + user-agent breakdown. minScale=1 verified already in place on web service. 1161 backend + 289 frontend tests. Deploys: api-00105-wwd → api-00106-rxf; web-00104-d4n → web-00105-vhx. **Monitor 2026-04-29: confirm <150 MB/day on Supabase egress chart.** |

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
- **Accidental deploys** (`gen-lang-client-0871147736`): sjktconnect-api + sjktconnect-web created by gcloud config race condition (2026-03-10) — DELETE from GCP Console

## Next Sprint

**Sprint 31 ✅ closed 2026-06-27 — Per-school history / origin story.** Schema (migrations 0015 + 0016) + 3-state SchoolHistory display with conditional placement (above School Details when populated) + bulk-import command + Gemini-restructured Wikipedia backfill for 72 / 528 schools (14%). All UNVERIFIED — awaiting school-admin review. Live: api `00137-z5g`, web `00145-tmc`. Retro at `docs/retrospective-sprint31.md`. Key lesson: never diagnose Next.js render via curl alone — `redirect()` returns a JS-only shell that curl reads as "empty" (now in `docs/lessons.md`).

### Post-Sprint-31 backlog (small-change-lane eligible)

- **More history coverage**: 389 schools still have stub Wikipedia articles. A future pass could try other sources (state Tamil education websites, news archive mining, alumni FB groups) — owner-driven, not scheduled.
- **Tamil locale (`history` + `history_key_dates` ta keys)**: intentionally empty per `tamil-style-guide.md` — needs owner-curated translation, not Gemini. Park until requested.
- **Add 2 pills-branch tests** to `SchoolHistory.test.tsx` (test file lost its pills coverage during the mid-sprint revert/restore — file restored from pre-pills commit). Small-change-lane.

**Sprint 29 ✅ closed 2026-06-26 — Security & Dependency Refresh.** Driven by the 2026-06-26 TD audit (`docs/tech-debt-audit-2026-06-26.md`). Closes TD-19 (Django 5.2.15 / Pillow 12.2 / cryptography 49 / lxml 6.1; ws/next-intl/postcss on the npm side), TD-20 (broadcast views now SUPERADMIN-gated via `SuperuserRequiredMixin`), TD-21 (revalidate route now requires `X-Revalidate-Token`; backend triggers via `schools/services/revalidation.py`), TD-22/23/25 (cleanups). TD-24 deferred to user (gcloud auth expired non-interactively — 1-line dashboard check post-deploy). 1436 backend (+12) + 367 frontend. Sprint 30 next.

### 2026-06-26 small-change-lane — Cloudflare legacy URL 301s

Item (B) from the 2026-06-26 SEO audit shipped via small-change-lane (commit `01348d0`): Cloudflare ruleset extended with `/claim*` → / and `*.aspx` → / rules, closing 148 of 157 GSC 404 URLs. No repo code changes.

Sprint 30 SEO scope items (C) and (D) **dropped** after owner review:
- (C) 87 canonical conflicts: no action needed — mostly pre-Sprint-22 www variants that clear naturally on re-crawl; 34 "Google-chose-different" are Google correctly folding locale variants.
- (D) School-page body-content beef-up: dropped — school pages already content-rich; thin-content gap is on DUN/constituency pages (deferred to a future content sprint, not in current scope).

3-week GSC validation pull target: ~2026-07-17.

### Sprint 30 — v2.0.1 Release + Production folder move (✅ DONE 2026-06-26)

- Tagged `v2.0.1` (cumulative cleanup superseding the earlier v2.0 from Sprint 24 close) covering Sprint 25 → Sprint 29 + 2026-06-26 small-change-lane. Full notes at `docs/release-notes-v2.0.1.md`.
- Moved `Development/SJKTConnect/` → `Production/SJKTConnect/`.
- Updated workspace `MEMORY.md` registry row + `memory/sjktconnect.md` path refs.

### Post-v2.0 backlog (no scheduled sprint)

The project enters maintenance. Owner-flagged work runs via small-change-lane unless it crosses the sprint threshold (≥6 files, new model/feature/page, or money/consent/auth/PII).

- **2026-07-17 GSC validation pull** — confirm Sprint 28 URL slug + small-change-lane 301s shifted the numbers. Update TD-06 / TD-24 with the egress dashboard outcome.
- **DUN/constituency page content enrichment** — the genuinely-thin pages per the 2026-06-26 audit. Defer until GSC re-pull confirms they're the binding constraint.
- **Personalised digest** (per-subscriber MP personalisation) — original 2026-05-11 roadmap Sprint 29 item. Defer indefinitely unless owner pulls it in.

### Future SEO follow-up (post-v2.0)

After ~2026-07-17 GSC re-pull, drive next moves from what actually shifted:
- If "Not found (404)" dropped from 157 → ~10, item (B) confirmed effective; no further action.
- If "Crawled - currently not indexed" remains >300, revisit DUN/constituency page enrichment.
- If avg position on school-name queries improved 2+ places, Sprint 28's slug work paying off.

### Original Sprint 27 — Auth / Profile Cleanup (DEFERRED — no longer planned)

The original 2026-05-11 roadmap had S27=Auth/Profile, S28=Egress R3, S29=Personalised Digest. The actual delivery diverged: S27/28/28.1 were owner-reported bug bundles + SEO URL slug, S29 became the audit-driven Security sprint. Personalised Digest deferred to post-v2.0 backlog — SEO has higher leverage for an unknown-to-Google site.

### Original Sprint 27 — Auth / Profile Cleanup (DEFERRED)

- **Goal**: address backlogged sign-in / sign-out / profile issues. Symptoms not yet enumerated — kickoff should walk through Google sign-in (anonymous → signed-in), sign-out, profile-edit display-name flow, and the SUPERADMIN role-change UI for any remaining race conditions or stale-state bugs.
- **Why now**: school page UX is clean post-Sprint-26. Auth has been the longest-lived unresolved area (TD-01 / TD-18 had Sprint 16 fixes but the user previously hinted "suspect remnants").
- **Plan**: not yet written. Awaits owner symptom enumeration at kickoff (same pattern as Sprint 26's six-bug list).

### Sprint 27–29 roadmap (locked 2026-05-11)

| # | Sprint | Goal |
|---|--------|------|
| 27 | Auth / Profile Cleanup | Sign-in / sign-out / profile issues. Suspect remnants of TD-01 / TD-18 race conditions. |
| 28 | Egress Round 3 (conditional) | Only if 2026-05-08 egress checkpoint shows drift. Task #43 image-proxy if needed. |
| 29 | Personalised Digest | Per-subscriber MP personalisation (`Subscriber.home_constituency` FK + per-recipient template injection). The original "Sprint 24" work, resequenced after quality + reliability fixes. |

**Release + folder-move sequencing**: Sprint 24 closed without the v2.0 tag (deferred to a separate release workflow). v2.0 release notes will cover Recovery Cut (Sprint 23) + Quality Overhaul (Sprint 24) + Urgent/PW UI (Sprint 25) as one narrative. After S29 close, run `project-complete` workflow + move `Development/SJKTConnect/` → `Production/SJKTConnect/`.

### Current codebase state (Sprint 31 closed, 2026-06-27)

- **Prod API**: `sjktconnect-api-00137-z5g` (Sprint 31 — applied migrations schools/0015, 0016 on startup; serves 5 new history_* fields).
- **Prod web**: `sjktconnect-web-00145-tmc` (Sprint 31 — 3-state SchoolHistory component, conditional placement, pills, single-line provenance footer).
- **Tests**: 1442 backend (+18 Sprint 31) + 378 frontend (+11 Sprint 31).
- **School history backfill**: 72 / 528 schools (14%) have UNVERIFIED Wikipedia-sourced history with en + ms paragraphs + key-date pills. 456 schools show the empty-state placeholder.
- **Scheduler state**: ALL four enabled.
  - `sjktconnect-monthly-blast` **ENABLED** (`0 9 1 * *` MYT) — un-paused 2026-06-26; June 2026 blast auto-fires 1 Jul 09:00 MYT.
  - `sjktconnect-fortnightly-digest` ENABLED (weekly cron; 14-day coverage guard enforces fortnight cadence).
  - `sjktconnect-resume-sending` ENABLED (daily 10:00 MYT).
  - `sjktconnect-urgent-alerts` ENABLED.
- **Active broadcast in flight**: Broadcast 86 (May 2026 blast, SENDING). 250/490 drained on 2026-06-26; remaining 240 drain at next `sjktconnect-resume-sending` run (~27 Jun 10:00 MYT). Subject: "May 2026: Private Sector Boosts SJK(T) Ladang Labu; Sedenak Gets Piped Water…".
- **State normalisation live**: `format_state()` collapses W.P. variants to compact form at storage; 15 School + 9 Constituency rows rewritten by migration `schools/0011`. Frontend, API, email all show "W.P. Kuala Lumpur" with zero per-component formatting.
- **News matcher activated**: Strategy 1.5 wires `SchoolAlias` lookup into `_resolve_school_codes` — 1,500+ existing seeded aliases + 31 new HANSARD aliases (Jenderata `hansard/0008` + KKB/St Teresa/West Country `hansard/0009`) now active for news matching.
- **April 2026 MOE refresh confirmed** (imported 2026-05-28 via `--skip-fields postcode,phone,fax,gps_lat,gps_lng,gps_verified`); 9 frontend label strings updated `January 2026 → April 2026` across en/ms/ta.
- **Sprint 23 shipped + still in effect**: dup-guard at compose, Brevo quota allowance (transient errors, not terminal), recess detection, admin coverage column.
- **Traffic-pin gotcha (Sprint 23)**: prod was pinned to `00115-fdf` since 29 Apr; 3 deploys had landed at 0% traffic. `gcloud run revisions list` ACTIVE column is not the source of truth — always also check `services describe --format='value(status.traffic)'`.
- **SEO baseline (Sprint 22)**: locale-aware metadata builders + JSON-LD on every school page + branded SVG fallback. `/about-tamil-schools` is live FAQ + state breakdown.
- **Canonical hostname (Sprint 22, Cloudflare 2026-05-02)**: `www.tamilschool.org/*` → 301 → root via Cloudflare Single Redirect ruleset id `1af056d066e44a5885c933227a413981`.
- **Cloudflare API access**: zone-scoped token in `.env`, perms = DNS / Zone Settings / Config Rules / Single Redirect (Edit).
- **Egress hardened (Sprint 21)**: `next-intl` ISR engaged, AwarioBot UA-blocked, MQL dashboard fixed. `Cache-Control: s-maxage=86400` + `x-nextjs-cache: HIT` verified live.

### Sprint history (post-roadmap)

The 5-sprint roadmap table below covers everything from Sprint 12 onward. The earlier sprint history table (lines ~196-254) only goes up to Sprint 17 — that's intentional, no need to duplicate.

### 5-Sprint Roadmap (12 → 16) — final state

| # | Sprint | Status |
|---|---|---|
| 12 | User Management UI | ✅ Done 2026-04-24 |
| 13 | Image Storage Migration | ✅ Done 2026-04-26 — resolved TD-05, TD-06, TD-13 |
| 14 | Community Photo Uploads | ✅ Done 2026-04-26 — resolved TD-07, TD-09, TD-16 (suggestions portion) |
| 15 | Image Display Polish | ✅ Done 2026-04-26 |
| 16 | Code-Quality Pass | ✅ Done 2026-04-27 — resolved TD-01, TD-10, TD-14, TD-15, TD-16 (users page), TD-17, TD-18 |
| 17 | Egress Hardening (hotfix) | ✅ Done 2026-04-27 evening |
| 18 | Monthly Digest Coverage | ✅ Done 2026-04-27 evening — aggregator now queries SittingBrief + ParliamentaryMeeting + filters mentions exclude(REJECTED) (was APPROVED-only — silently dropped 3 PENDING mentions on 2 Mar 2026 from the 1 Apr digest); MPScorecard date-filtered with lifetime fallback; new `--backfill-since` flag on compose_monthly_blast for one-time fill scenarios. **Operational followup**: manual trigger of `sjktconnect-monthly-blast` job with `--backfill-since 2026-02-01` before 1 May 2026 to include the missing 1st Meeting 2026 report in the April digest. |
| 19 | Edit Page Tabs | ✅ Done 2026-04-28 — `/school/[moe_code]/edit` now a 5-tab layout (Core/Contact/Leaders/Support/Images). Confirm Data + verified fields + Sprint 1.7 verification dashboard all removed. GPS edit gated to SUPERADMIN. Stitch screen approved before coding. New components in `frontend/components/edit_tabs/`. SchoolEditSerializer extended with read-only MOE metadata + nested leaders so single API call serves the whole page. "Claimed by HM since {date}" badge added. 1174 backend + 288 frontend tests. Deploys: api-00109-hjm → api-00110-r6l; web-00105-vhx → web-00106-dd6. |
| 21 | **Egress Round 2** | ✅ Done 2026-04-29 (Task #43 deferred to Sprint 22). **Three landed fixes:** (1) **next-intl ISR engaged** — `setRequestLocale(locale)` in `app/[locale]/layout.tsx` + 10 page files; new `app/[locale]/dashboard/layout.tsx` opts the dashboard segment out via `dynamic="force-dynamic"`; new `frontend/app/[locale]/dashboard/layout.tsx` for the dashboard pages; empty `generateStaticParams()` added to all 5 dynamic-segment routes (school/[moe_code], constituency/[code], dun/[id], parliament-watch/[id], parliament-watch/sittings/[id]) to opt them into ISR-on-demand caching; `lib/api.ts` `fetchJSON()` now sets `next:{revalidate:86400}` (Next 15+ defaults fetch to uncached, which was the root reason dynamic-route pages stayed dynamic). All 10 ISR pages verified live: `Cache-Control: s-maxage=86400, stale-while-revalidate=31449600` + `x-nextjs-cache: HIT`. (2) **AwarioBot UA block** — new `UserAgentBlockMiddleware` in `core/middleware.py` (case-insensitive substring match against AwarioBot, AwarioRssBot, AwarioSmartBot, SemrushBot, DataForSeoBot, MJ12bot); wired second in `MIDDLEWARE` after IPBlockMiddleware. `app/robots.ts` adds explicit Disallow for the same 6 UAs. 7 new backend tests. Verified live: AwarioBot/1.0 → 403; real browsers pass. (3) **Egress dashboard fixed** — recreated both log-based metrics (`sjktconnect_api_egress_per_route`, `sjktconnect_web_egress_per_route`) from YAML configs in `backend/docs/metrics/` (they kept DISTRIBUTION since GCP rejects INT64+valueExtractor combo). Dashboard `f1722366-2df9-4446-9941-7cda5c019615` query rewritten with secondary `ALIGN_SUM` aggregation so `pickTimeSeriesFilter` sees a scalar and the top-10 charts render. **Task #43 (Supabase Storage hot-link protection) deferred** — image proxy on backend or signed-URL approach both need ~2-4h of design work; user approved deferral. **Operational followup**: monitor Supabase egress chart 2026-04-30 to confirm <150 MB/day. Deploys: api-00111-mrq → api-00112-k7t (UA block); web-00107-wd9 → web-00108-c56 → web-00109-6r4 → web-00110-vph (3 iterative deploys to pin down the dynamic-route caching gap). 1198 backend (+7) + 297 frontend tests. |
| 20 | Leader Inline CRUD | ✅ Done 2026-04-28 evening — Replaces Sprint 19's read-only LeadersTab. New backend POST/PATCH/DELETE endpoints on /api/v1/schools/<moe>/leaders/ with school-admin permission (mirrors community._is_photo_approver: SUPERADMIN OR bound admin only; MODERATOR not special-cased). 409 slot_taken on duplicate active role; soft-delete via is_active=False; delete-then-recreate-same-role works because unique constraint is conditional. SchoolEditSerializer.get_leaders switched to admin serializer (id+phone+email) so single round-trip serves the page. Frontend LeadersTab rewrite: 4 fixed role slots, existing rows editable (name + phone + email + Remove), empty roles show "+ Add {role}". Single Save Changes button (disabled when no pending changes). Sequential flush (delete → create → update) keeps unique-constraint happy on swap-same-role. Blanking name = treated as delete. 17 new backend + 8 new frontend tests. 1191 backend + 297 frontend total. Deploys: api-00110-r6l → api-00111-mrq; web-00106-dd6 → web-00107-wd9. |
| 22 | **SEO Snippet & Canonical Hostname Fix** | ✅ Done 2026-05-01 (Cloudflare redirect 2026-05-02). Sprint 22 ships frontend metadata builders (`buildSchoolMetadata`, `buildConstituencyMetadata`, `buildDUNMetadata`) in `frontend/lib/seo.ts` — locale-aware Metadata with town-aware titles + labelled-k/v descriptions (Address/Alamat/முகவரி + Email + Phone + Location + Assistance). `buildSchoolJsonLd` emits EducationalOrganization JSON-LD on every school page. `frontend/public/school-placeholder.svg` (1200×630 branded) wired as og:image + ImageObject + SchoolPhotoGallery empty-state fallback so every school renders a real `<img>` for SERP thumbnail extraction. `/about-tamil-schools` extended from "Coming Soon" stub to live FAQ + state-breakdown table targeting "how many tamil schools" long-tail queries. **Cloudflare Single Redirect** (zone `tamilschool.org`, ruleset `1af056d066e44a5885c933227a413981`) applied via API 2026-05-02 — `www.*` → `https://tamilschool.org/$path?$query` 301; verified live. 1198 backend + 320 frontend tests (+23). |
| 23 | **Recovery Cut — duplicate-blast incident response** | ✅ Deployed 2026-05-11 `sjktconnect-api-00118-5w4`. Triggered by 2026-05-02 duplicate April blast (4 Broadcast rows, ~80-300 subs got 2x). Landed: (#4a) Brevo daily-quota pre-flight check in `broadcasts/services/brevo_quota.py` calling `GET /v3/account` — refuses-at-start when `len(recipients) > remaining`; (#4b) duplicate-Broadcast guard at compose time — aborts if a SENT/SENDING/DRAFT Broadcast exists with matching `kind` + month coverage; recess detection at aggregator (`HansardSitting.status=COMPLETED` filter sets `parliament_was_in_session=False` for recess months); admin coverage column. `resume-sending` scheduler un-paused 2026-05-11 (drains Broadcast 77's 256 stragglers over 12–14 May). `monthly-blast` scheduler stays PAUSED until Sprint 24 ships. Traffic-pin gotcha discovered at deploy: prod was pinned to `00115-fdf` since 29 Apr; 3 deploys (00116-voy, 00117-kab `sprint23` tag, 00118-5w4) had landed at 0% traffic — `gcloud run services update-traffic --to-latest` required. 1225 backend + 320 frontend tests. Commit `65f9720`. |
| 24 | **Monthly Digest Quality Overhaul + Scheduling Resume** | ✅ Closed 2026-06-26. Eng tasks 1–9 done 2026-05-15 (recess prompt, news triage, topic clustering, schools-by-state, template overhaul, footer CTAs, smoke test). Tasks 10b–10h done 2026-06-25/26: news section collapse with hybrid scoring + top-N cap (10b); W.P. KL state normalisation + UTF-8 preview-shell (10c, migration `schools/0011`); Jenderata aliases (10d, migration `hansard/0008`); April 2026 frontend label (10e, 9 strings × en/ms/ta); MOE file refs to April 2026 (10f); Take Action editorial-card redesign (10g); news matcher Strategy 1.5 SchoolAlias lookup + bracket/Ladang variants + KKB/St Teresa/West Country aliases (10h, migration `hansard/0009`). Plus PJS casing+spacing (parallel commit) + rematch_schools UTF-8 fix. Deployed: api 00120-25k → 00121-7hb; web 00114-2jq → 00115-82q (ISR cache-bust). `monthly-blast` scheduler un-paused. May 2026 blast manually composed+sent (Broadcast 86, 490 recipients, draining over 2-3 days). 1389 backend (+14 net) + 320 frontend. v2.0 release tag deferred to separate release workflow. Retro: `docs/retrospective-sprint24.md`. |
| 25 | **Urgent Alerts + Parliament Watch UI** | ✅ Closed 2026-06-26 (backend-only, ~1h wall time). `URGENT_ALERT_REQUIRE_REVIEW` default flipped to `true` in `base.py` — the 09:30 MYT cron now leaves DRAFTs for admin review instead of auto-sending. New `send_test(broadcast_id, recipient_emails)` primitive + `--test-recipients` flag on `send_broadcast` mgmt command + "Send Test" form on broadcast preview admin UI (capped at 5 recipients, bypasses Brevo daily quota, `[TEST]` subject prefix, no `BroadcastRecipient` rows, broadcast stays DRAFT). Kind filter dropdown + Kind column on broadcast list (`?kind=URGENT_ALERT` etc.). Dry-run hardening on all three compose commands — each now prints "Would target N subscriber(s)". 1406 backend (+17 net) + 328 frontend (+8 from held pre-sprint bug fixes). Retro: `docs/retrospective-sprint25.md`. |
| 26 | **School Page UX Pass** | ✅ Closed 2026-06-26 (~1.5h, 13 files). 6 owner-reported bugs: (#4) `/en?state=Selangor` crashed in browser after hydration — DRF serialises `gps_lat`/`gps_lng` as string and `bounds.extend()` threw; `FitBoundsOnStateFilter` now coerces with `Number()` + `Number.isFinite` guard. (#3) Tamil name de-duplicated from School Details box (still in hero). (#2) Session Type free-text → constrained `SelectField` dropdown with backend `validate_session_type`. (#6) MP `tel:` link strips multi-number values via `firstPhoneForTelUri()` helper. (#5) MP Facebook button hidden when URL matches generic ParlimenMY shape via `isUsableMpFacebookUrl()` frontend guard + `is_generic_facebook_url()` scraper-side drop (two-layer fix). (#1) Phone + email validation across Contact + Leaders edit tabs: `validation.ts` helpers + `EditableField` `error`/`pattern` props + inline red-border + `aria-describedby` + serializer `validate_phone` mirror on `SchoolEditSerializer` and `SchoolLeaderAdminSerializer`; 3-locale i18n. 1417 backend (+11) + 349 frontend (+21). Retro: `docs/retrospective-sprint26.md`. |
| 27 | **School Page UX Pass (follow-up)** | ✅ Closed 2026-06-26 (~1.5h, 11 files). 4 more owner-reported bugs: (#1+#4) ISR cache held edit-saves stale for up to 24h — new `app/api/revalidate/route.ts` + `revalidateSchoolPage()` helper called from SchoolEditForm + LeadersTab after Save, then `router.refresh()` + `router.push('/{locale}/school/{moe}')` so the user lands on the public page with the change live. (#3) News page `pageSize` 50→250 + search input converted to debounced API-backed (`?search=` was always supported server-side); search now spans entire approved corpus. (#2) NBD4079 (SJK(T) Ladang Labu Bhg 4) had 9 articles in news DB but only 2 correctly tagged — investigation found the variant generator doesn't bridge `Bhg ⇔ Bahagian ⇔ Division`, and the only two other schools in the DB with "Bahagian" / "Division" in their names (ABDB006, MBD0067) were absorbing the 7 mis-tagged articles. Migration `hansard/0010_ladang_labu_bahagian_aliases` adds 13 HANSARD aliases; post-deploy `rematch_schools` cleans up existing rows. 1420 backend (+3) + 349 frontend (unchanged). Retro: `docs/retrospective-sprint27.md`. |
| 28 | **SEO URL Slug + Alias Bridge + Phone Validation** | ✅ Closed 2026-06-26 (~2.5h, 18 files). 3 owner-flagged items: **(A) URL slug**: `/school/<name>-<city>-<moe>` shape (e.g. `subramaniya-barathee-gelugor-pbd1088`) replaces bare-code. New `lib/urls.ts` (`schoolPath` / `parseSchoolSlug` / `isCanonicalSchoolSlug`). Page handler accepts both slug + legacy bare-code; non-canonical → 301 to canonical. Sitemap + JSON-LD + meta canonical all emit slug. Closes the SEO gap vs apac.com.my that put us at #7 vs their #3. **(B) Aliasing root cause** (owner-corrected diagnosis): extended `seed_aliases.generate_aliases_for_school` with `Bhg ⇔ Bahagian ⇔ Division` bridge — closes the gap that caused Sprint 27's mis-tagging at the proper layer (alias generator) rather than at the fallback (Strategy 5). Sprint 27's hansard/0010 migration becomes belt-and-braces. **(C) Phone validation**: replaced permissive `{6,20}` shape regex with MY-specific digit-count rules (mobile 10-11 + landline 9-10 + `+60` normalisation). Truncated numbers now fail. **(D)** Added `city` to `/api/v1/schools/map/` serializer for slug builder. **Post-deploy step**: run `seed_aliases` on prod to materialise the new Bhg/Bahagian/Division variants. 1424 backend (+4) + 366 frontend (+17). Retro: `docs/retrospective-sprint28.md`. |
| — | **News Digest Stuck-Loop Fix** (ad-hoc incident sprint) | ✅ Done 2026-06-11, deployed `sjktconnect-api-00119-92c` + all 7 jobs synced (commit `d2f6269`). Quota errors now transient (send-what-fits, stay SENDING — un-breaks full-list urgent alerts too); 14-day coverage-anchored fortnight guard (weekly cron unchanged); digest subject = big-story headline; sender "SJK(T) News" for digest+urgent; `Broadcast.Status.CANCELLED` formalised (migration 0007); `resume_sending` FAILED sweep + compose window tripwires close the exit-0-while-broken monitoring gap. Live repair same day: broadcast 82 catch-up sent to its 250 pending (zero duplicates), 79-81 + 83-84 CANCELLED. **Verify: 15 Jun skip log; 22 Jun digest covers 9-22 Jun; 23 Jun resume drains to SENT.** 1375 backend + 320 frontend tests. Retro: `docs/retrospective-news-digest-stuck-fix.md`. |
| 28.1 | **Sprint 28 follow-up bundle** | ✅ Closed 2026-06-26 (~3h, 16 files, 9 commits, 11 api + 7 web deploys). 9 owner-reported issues from post-deploy testing. **GPS edit unblocked for SUPERADMIN** (read_only_fields drop + .update() role gate + view context= threading + FE round-to-7dp + BE quantize). **ISR revalidate-slug fixed** (literal slug URL in payload — segment+'page' was returning 200 but not invalidating in Next 16). **TIADA / N/A / - accepted** in phone validators. **Leader phones normalised to +60-X XXX XXXX** (serializer-side; +format_phone mobile prefix recognition — was missing 010-019; +migration 0014 backfill). **`Kg.Simee` → `Kg. Simee` space** (to_proper_case + migration 0012 for 3 affected rows). **MP CTA in monthly blast** → /constituencies. **7 Labu articles relabelled** via new relabel_labu_mistags command (the systemic alias fix from Sprint 28 couldn't reach them — first-resolution overwrote Gemini's name). **Kathumba + Jawa Lane aliases added** (migration hansard/0011, 14 alias variants); 2 more articles tagged correctly. Net news-matcher effect: NBD4079 2→9, ABDB006 4→0, MBD0067 3→0, KBD0053 0→1, NBD4070 1→2. 1424 backend (+0 net) + 367 frontend (+1). Retro: `docs/retrospective-sprint28.1.md`. |
| 31 | **Per-school history / origin story** | ✅ Closed 2026-06-27 (~6h, 1h on a curl-vs-redirect false-positive detour). Every school page had carried an empty "History & Story" placeholder since Sprint 1.10. Shipped: schema (migrations `schools/0015` + `0016`: `history`, `history_source_urls`, `history_status`, `history_updated_at`, `history_key_dates`); 3-state `SchoolHistory` component (empty CTA / fallback-banner / populated with pills + 2-paragraph 75-100w prose + single-line `Source: Wikipedia (ms) — Help improve →` footer); conditional page placement (above School Details when populated; bottom-of-column when empty so the 86% empty pages don't crowd the address). Backfilled 72 / 528 schools (14% coverage) by scraping `ms.wikipedia.org/wiki/Kategori:Sekolah_jenis_kebangsaan_Tamil_di_Malaysia` + 11 state subcategories, then Gemini 2.5 Flash restructure (per-locale en+ms, ms-only is intentional per tamil-style-guide). 389 stub articles + 67 no-article. Bulk-import via new `seed_school_histories` mgmt command (--dry-run / --force / skips human-curated). `i18n` namespace `schoolHistory` × 3 locales. 1442 backend (+18) + 378 frontend (+11). Retro: `docs/retrospective-sprint31.md`. |

### Open tech debt remaining

- **TD-12** (🟢 low) — `hansard/pipeline/extractor.py` at 26% coverage. Test-coverage padding; can wait indefinitely.

(TD-07/09/11 were resolved in Sprint 14/16/18 — register headers + bodies now consistently marked ✅. TD-06 still PROVISIONALLY RESOLVED pending the 2026-05-08 egress checkpoint.)

### Gotchas carried out of Sprint 16 + 17

- **Half-applied tech-debt fixes**: Sprint 15's test-suite claim ("285 passing") was actually 282 pass + 3 fail. The Sprint 15 hotfix added a useSession dep to two components without updating their tests; nobody re-ran the full suite at sprint close. Lesson: the close workflow should run `npm test` (and pytest) and record the actual result, not the expected one.
- **Retrospectives that claim work is done aren't proof**: Sprint 8.3 retro said "ISR with 24h revalidate"; reality was `revalidate = false` everywhere. Egress Fix retro said "middleware IP blocking"; no such middleware existed. **Sprint 17's first job was undoing both gaps.** Future sprint-close commits must include the literal config/code that proves the work landed (e.g. `git diff` snippet, not just claim).
- **`__Host-` cookie prefix is incompatible with Cloudflare proxy** in our config. Any future cookie-related Auth.js change must override that prefix to `__Secure-`. The override now lives in `frontend/lib/auth.ts`; don't strip it.
- **Auth-events pattern is now the canonical way** to coordinate "Django session is ready" between `UserMenu` and any auth-aware component. Future role-gated UI should subscribe to `onProfileReady` rather than re-deriving the race-mitigation logic.
- **Per-route egress observability is now live**. Cloud Monitoring → Dashboards → "SJK(T) Connect — Egress by Route/UA" answers "which route is leaking" without further investigation. Use it before hypothesising the next egress bug.
- **`revalidate = false` is the worst possible value in Next 16 — disables ISR entirely**. Always specify a number (or omit `revalidate` to use the default). If a page genuinely needs no caching, use `dynamic = "force-dynamic"` instead, which is more discoverable in code review.

### Small passive/manual items carried over (no engineering work)

- Google Search Console: manually set Googlebot crawl rate
- Verify urgency audit trail after first post-fix urgent alert
- Verify 4 May 2026 fortnightly cron fires with coverage "21 Apr – 4 May"
- 2 transitive npm deps still in audit (`brace-expansion`, `picomatch`) — resolves in Sprint 16
- **Monitor Supabase egress** for 1 week post-Sprint-13 to confirm <100 MB/day target now met (was 5–10× over)

**Ongoing**: Triage `docs/tech-debt.md` at every sprint close.

**Future work**:
- **Task #43 — Supabase Storage hot-link protection** (carried over from Sprint 21, never landed in Sprint 22). Recommended approach (per Sprint 21 retro): image proxy at `api.tamilschool.org/img/<key>` that streams Supabase bytes after a Referer check, with `Cache-Control: s-maxage=31536000, immutable` so Cloudflare absorbs most repeat hits. ~2-4 hours. Trade-off: shifts egress from Supabase Pro ($0.09/GB) to Cloud Run (1 GB/day free, then $0.12/GB) with most absorbed by Cloudflare cache. **Pull into a micro-sprint if Supabase egress climbs above 250 MB/day for 3+ days; otherwise park.**
- **Egress checkpoint — 2026-05-08**: confirm Supabase egress chart shows <150 MB/day for the preceding 7 days. If yes, mark TD-06 from PROVISIONALLY RESOLVED → RESOLVED. If still elevated, the Sprint 21 fixes haven't fully landed and Task #43 becomes urgent. Single observation, not an open-ended monitoring item.
- **Email engagement dashboard** — query open/click rates per broadcast, identify disengaged subscribers
- **Close the learner feedback loop** — auto-inject learner flags into prompts, store successful corrections as pattern memory
- Urgent Response System (design approved, see `docs/plans/2026-03-04-urgent-response-system-design.md`)
- MP profile pages (combine Hansard data with contact info)
- Pre-filled advocacy message templates per school
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
- **Tests**: Jest + React Testing Library (290 tests)
- **Build**: Standalone output, 107 kB first load JS
- **Dockerfile**: Multi-stage (deps → build → runner), port 8080
- **Env vars**: `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY`, `NEXT_PUBLIC_GOOGLE_MAPS_MAP_ID`

## REST API (Sprint 1.2+)
- All endpoints under `/api/v1/` — paginated (50/page via `?page=N`)
- **Schools**: `GET /api/v1/schools/` (filters: `?state=`, `?ppd=`, `?constituency=`, `?skm=true`, `?min_enrolment=`, `?max_enrolment=`), `GET /api/v1/schools/<moe_code>/` (includes `leaders` array: name + role_display, ordered: Chairman → HM → PTA → Alumni), `GET /api/v1/schools/map/` (all active schools, 10 minimal fields, non-paginated ~50 KB — Sprint 8.3), `GET /api/v1/schools/national-stats/` (total schools, students, teachers, constituencies — Sprint 3.4)
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
- **Brevo Webhook** (Sprint 8.5): `POST /api/v1/webhooks/brevo/` (delivery events: delivered, opened, clicked, hard/soft bounce, spam, unsubscribed — updates BroadcastRecipient engagement fields, auto-deactivates after 3 hard bounces)
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
