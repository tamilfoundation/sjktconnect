# Changelog

## Sprint 3.7 — Map InfoWindow, School Page Polish & Enrolment Filter (2026-03-03)

### Fixed
- **Enrolment filter**: Schools above the enrolment threshold are now hidden entirely instead of shown as grey pins — reduces visual clutter on the map

### Changed
- **Map InfoWindow redesign**: New popup with school image (or placeholder), assistance/location badges, 3-stat row (students, teachers, ratio), constituency + DUN links, full-width "View School" button
- **School detail page redesign**: 12-col grid layout (7/5 split), 3 elevated stat cards with SVG icons (students, teachers, grade), preschool/special ed info bar, top-aligned title, metadata chip with primary-coloured MOE code
- **SchoolPhotoGallery**: Taller image (400px on desktop), clickable thumbnails overlaid inside the image at bottom-left, attribution overlay with backdrop blur
- **StatCard**: Elevated design with rounded-xl, border, shadow, React.ReactNode icon support with configurable colour
- **SchoolListSerializer**: Added `dun_id`, `dun_code`, `dun_name`, `image_url` fields for map InfoWindow
- **SchoolListView**: Added `select_related("dun")` and `prefetch_related("images")` to avoid N+1 queries

### Added
- `mapInfoWindow` translation namespace (EN/MS/TA) with keys for badges, stats, and CTA

### Technical
- 757 tests passing (532 backend + 225 frontend)
- Both backend and frontend deployed to Cloud Run
- 3 commits: enrolment filter fix, InfoWindow redesign, school page redesign

---

## Sprint 3.6 — Footer, Legal, Contact, School Page & Map Filters (2026-03-03)

### Added
- **Footer redesign**: Dark bg, copyright + social media icons (left), Platform + Legal link columns (right)
- **Legal pages**: Privacy Policy, Terms of Service, Cookie Policy — trilingual (EN/MS/TA)
- **Contact page**: Form (name, email, subject, message) with backend API, sends via Brevo
- **Contact API**: `POST /api/v1/contact/` with 3/hour rate limit, Brevo email integration
- **MapFilterPanel**: Replaces StateFilter — 4 colour modes (Assistance, Location, Programmes, Enrolment), toggle switches, enrolment slider, counter, info note
- **Coloured map pins**: Dynamic pin colours based on active filter mode (assistance: purple/orange, location: blue/green, programmes: purple/blue/orange/grey, enrolment: red/grey)
- **MapFilterPanel tests**: 10 new tests covering all colour modes, toggles, slider, reset
- Contact link in header nav (desktop + mobile)
- `dun_id` field in SchoolDetailSerializer for DUN page linking
- `assistance_type`, `location_type`, `preschool_enrolment`, `special_enrolment` fields in SchoolListSerializer for map filtering
- `mapFilters` translation namespace (all 3 languages)

### Changed
- **School detail page**: Redesigned layout — political representation + MiniMap moved to right sidebar, 5 stat cards (Students, Teachers, Grade, Preschool, Special Ed)
- **Leadership section**: Always shown — displays "Not Available" placeholders when no leaders data
- **Constituency/DUN**: Now clickable links (→ `/constituency/P149`, → `/dun/{id}`)
- **ConstituencySchools**: Shows "only Tamil school" message instead of returning null when empty
- **StatCard**: Added top-border accent (`border-t-2 border-t-primary-500`)
- **Section headers**: Added coloured left-border accents, person icons on leadership
- **SchoolMap**: Uses MapFilterPanel instead of StateFilter, filtering by assistance/location/programmes/enrolment
- **SchoolMarkers**: Accepts `colourMode` and `enrolmentThreshold` props for dynamic pin colouring
- **Search**: "SJKT" now matches "SJK(T)" in search results (parenthesis normalisation)

### Technical
- 757 tests passing (532 backend + 225 frontend)
- New components: MapFilterPanel, ContactForm
- New pages: contact, privacy, terms, cookies

---

## Sprint 3.5 — Tamil Translation Review + Deployment (2026-03-03)

### Fixed
- Tamil translations: 7 vallinam doubling corrections (ஊடகச், புலனாய்வுத், இயங்குப்/த், பள்ளிப், நடவடிக்கைகளைத், புலனாய்வுக்குச்)
- Tamil translations: standardised நுண்ணறிவு → புலனாய்வு for "intelligence" consistency
- Tamil translations: AI → செய்யறிவு (proper Tamil term for artificial intelligence)
- Tamil translations: சந்தா செலுத்துங்கள் → இணையுங்கள் (join, not pay subscription)
- Tamil translations: removed redundant இயங்கு from செய்யறிவு compounds
- Frontend: updated @swc/helpers to 0.5.19 for next-intl compatibility

### Deployed
- Backend: revision sjktconnect-api-00016-vlb (all Sprint 3.3-3.4 changes)
- Frontend: revision sjktconnect-web-00013-ff8 (i18n, hero, about, data provenance)
- Cloud Run jobs updated to latest image (check-hansards, news-pipeline, monthly-blast)

### Technical
- 747 tests passing (532 backend + 215 frontend)
- gcloud CLI fixed: CLOUDSDK_PYTHON updated to Python 3.13

---

## Sprint 3.4 — Homepage, About, Data Provenance & UX (2026-03-03)

### Added
- National summary statistics API endpoint (`GET /api/v1/schools/national-stats/`)
- Homepage hero section with mission statement and national stats bar (528 schools, 75k students, 222 constituencies)
- About page (`/about/`) with mission, methodology, and team information
- Favicon and site metadata (apple-touch-icon, Open Graph, manifest icons)
- Data provenance notes on SchoolProfile ("Data source: MOE, January 2026") and Footer ("Data last updated: January 2026")
- Social proof text on subscribe form
- `translations.ts` utility for translating MOE jargon (enrolment categories, grade levels)
- HeroSection and NationalStats components
- 6 new frontend tests (HeroSection, NationalStats, About page, translations)
- 1 new backend test (national stats endpoint)

### Changed
- School profile: enrolment categories translated from Malay (e.g. "ENROLMEN PRASEKOLAH" → "Preschool Enrolment")
- School profile: grade levels translated (e.g. "GRED A" → "Grade A")
- Claim This Page CTA reframed — emphasises community benefit over claiming
- Parliament Watch page: improved empty state with constructive messaging
- NewsWatchSection: improved empty state with explanation text
- MentionsSection: added context for empty mentions state
- ConstituencyList: filters out constituencies with zero schools
- Constituency page: hides boundary map when no GeoJSON available
- Footer: added About link alongside Subscribe and Contact
- Header: added About link to navigation

### Technical
- 747 tests passing (532 backend + 215 frontend)
- 33 files changed, +1,037 lines

---

## Sprint 3.3 — i18n Infrastructure (2026-03-03)

### Added
- Trilingual support (English, Tamil, Malay) using next-intl
- Locale-prefixed URLs: `/en/`, `/ta/`, `/ms/`
- Language switcher in Header (EN | தமிழ் | BM)
- ~162 strings extracted to `messages/en.json`, `messages/ta.json`, `messages/ms.json`
- Middleware for automatic locale detection and redirect
- Translation completeness tests (all three languages must have matching keys)
- LanguageSwitcher component
- 6 new i18n tests (190 frontend total, 852 overall)

### Changed
- All pages moved under `app/[locale]/` directory
- All internal links use i18n-aware navigation (`@/i18n/navigation`)
- Root `/` redirects to `/en/`
- Layout wraps children with NextIntlClientProvider

---

## Sprint 3.2 — Frontend Layout Redesign (2026-03-02)

### Changed
- School page hero: side-by-side layout on desktop (photo 3/5, name + stats 2/5), stacked on mobile
- Stat cards moved to hero: Students (primary + preschool combined), Teachers, Grade
- Removed SKM stat card, MOE Code detail row, and Full Name detail row
- Enrolment breakdown always shown: School, Preschool, Special Needs (even when 0)
- Assistance type mapped: SBK → Government-Aided (SBK), SK → Government (SK)
- Address format: postcode and city grouped together

### Added
- `SchoolLeader` TypeScript type
- `leaders` field on `SchoolDetail` interface
- School Leadership section in SchoolProfile (Board Chairman, Headmaster, PTA Chair, Alumni Chair)
- 5 new frontend tests (184 total), all 846 tests passing (662 backend + 184 frontend)

---

## Sprint 3.1 — Data Quality + School Leadership (2026-03-02)

### Added
- `to_proper_case()` utility: converts ALL CAPS MOE data to proper title case, preserving abbreviations (SJK(T), PPD, LDG, SG, etc.) and handling apostrophes, Roman numerals, parenthetical expressions
- `format_phone()` utility: standardises Malaysian phone numbers to `+60-X XXX XXXX` format
- Data migration: proper case for 528 schools (names, addresses, states, PPD), lowercase emails, formatted phones
- Import script updated: future MOE re-imports produce proper case automatically
- `SchoolLeader` model: Board Chairman, Headmaster, PTA Chairman, Alumni Association Chairman
- Admin inline for managing school leaders with full contact details
- Public API exposes leader name and role only (phone/email private)
- Unique constraint: one active leader per role per school
- 41 new backend tests (32 utils + 7 model + 3 API → 662 total)

### Design docs
- `docs/plans/2026-03-02-school-page-improvements-design.md`
- `docs/plans/2026-03-02-school-page-improvements-impl.md`

---

## Sprint 2.8 — News Watch Live + Cloud Scheduler Automation (2026-03-02)

### Added
- Public news API endpoint: `GET /api/v1/schools/<moe_code>/news/` — returns approved news articles mentioning a school
- `NewsArticleSerializer` and `SchoolNewsView` in `newswatch/api/`
- Real `NewsWatchSection` component on school pages — replaces placeholder with actual article display (title, source, date, AI summary, sentiment badge, urgency flag)
- `NewsArticle` TypeScript type and `fetchSchoolNews()` API function
- `run_news_pipeline` management command — chains fetch → extract → analyse for Cloud Scheduler
- Cloud Run Jobs: `sjktconnect-news-pipeline` (daily) and `sjktconnect-monthly-blast` (1st of month)
- Cloud Scheduler: `sjktconnect-daily-news` (8:30 AM MYT daily), `sjktconnect-monthly-blast` (9:00 AM 1st of month)
- Clickable photo thumbnails in `SchoolPhotoGallery` — click to swap into hero position (from pre-sprint work, included in deploy)
- 16 new backend tests (7 news API + existing), 9 new frontend tests (NewsWatchSection)

### Fixed
- Fixed gcloud CLI Python path issue (Python 3.11 removed, updated to Python 3.13 via CLOUDSDK_PYTHON)

### Infrastructure
- Backend deployed: revision `sjktconnect-api-00015-9bt`
- Frontend deployed: revision `sjktconnect-web-00012-jfx`
- Updated all Cloud Run Jobs to latest image
- Added `CLOUDSDK_PYTHON` to `~/.bashrc` for permanent gcloud fix

---

## Sprint 2.7 — Monthly Intelligence Blast (2026-03-02)

### Added
- `blast_aggregator.py` service: queries top 5 approved Hansard mentions, top 5 approved news articles, top 3 MP scorecards for a given month
- `compose_monthly_blast` management command with `--month YYYY-MM` and `--dry-run` flags
- `monthly_blast.html` email template with three sections (Parliament Watch, News Watch, MP Scorecard Highlights)
- 23 new backend tests (blast aggregator service + management command)

### Technical
- No new models — reuses existing Broadcast, HansardMention, NewsArticle, MPScorecard
- Audience filter set to MONTHLY_BLAST category for subscriber targeting
- Plain-text fallback auto-generated via strip_tags
- Admin reviews draft via existing broadcast preview UI, sends via existing Brevo infrastructure

## Sprint 2.6 — News AI Analysis + Rapid Response + Review UI (2026-03-02)

### Added
- Gemini Flash AI analysis of extracted news articles: relevance score (1-5), sentiment (POSITIVE/NEGATIVE/NEUTRAL/MIXED), AI summary, mentioned school extraction, urgency flagging
- `news_analyser.py` service: Gemini API wrapper with token budgeting (~3000 chars), structured JSON output, response validation with enum clamping
- `analyse_news_articles` management command: processes EXTRACTED articles in batches (`--batch-size`), warns about urgent articles pending review
- Admin review queue at `/dashboard/news/`: filterable by review status (PENDING/APPROVED/REJECTED) and urgency, sorted urgent-first then by relevance
- Article detail view at `/dashboard/news/<pk>/`: split-screen layout (article body left, AI analysis + actions right), approve/reject/toggle-urgent actions
- Navigation sidebar showing other articles for quick review switching
- "News Watch" nav link in base template
- Migration `0002_add_ai_analysis_fields`: adds 9 fields to NewsArticle (relevance_score, sentiment, ai_summary, mentioned_schools, is_urgent, urgent_reason, ai_raw_response, review_status, reviewed_by, reviewed_at)

### Changed
- NewsArticle model: extended status lifecycle NEW → EXTRACTED → ANALYSED, added PENDING/APPROVED/REJECTED review status
- NewsArticle admin: added AI analysis fields to list display and filters

### Technical
- Follows same Gemini pattern as `parliament/services/gemini_client.py` — structured JSON response, validation with enum clamping, token budgeting
- Review actions use `update_fields` for efficient partial saves
- Queue view uses `LoginRequiredMixin` — admin-only access
- Urgency criteria: school closures, safety crises, funding cuts, political controversies
- 39 new backend tests (news analyser service, management command, admin views, model fields), 758 total (591 backend + 167 frontend)

---

## Sprint 2.5 — News Watch Pipeline: RSS + Article Extraction (2026-03-02)

### Added
- New `newswatch` Django app with `NewsArticle` model (status lifecycle: NEW → EXTRACTED or FAILED)
- RSS fetcher service: parses Google Alerts RSS feeds, unwraps redirect URLs, deduplicates by URL, batch-checks existing articles
- Article extractor service: uses trafilatura to fetch and extract body text, source name, and published date from article URLs
- Management commands: `fetch_news_alerts` (RSS polling, supports `--url` flag or `NEWS_WATCH_RSS_FEEDS` setting) and `extract_articles` (body extraction, `--batch-size` flag)
- Django admin for NewsArticle with list display, status/source filters, search
- New dependencies: feedparser, trafilatura, lxml_html_clean

### Technical
- Google Alerts redirect URL resolution (`google.com/url?...&url=ACTUAL_URL`)
- HTML tag stripping for RSS titles (Google Alerts uses `<b>` tags)
- Batch URL existence check to avoid N+1 queries during RSS import
- Article extraction preserves RSS-sourced published_date, only fills from trafilatura if missing
- Graceful failure handling: download failures and extraction errors set status=FAILED with error message
- 36 new backend tests (model, RSS fetcher, article extractor, management commands), 719 total (552 backend + 167 frontend)

---

## Sprint 2.4 — Subscribe/Unsubscribe Frontend Pages (2026-03-01)

### Added
- `/subscribe/` page with SubscribeForm component: email, name, organisation fields, category preview, success/error/loading states
- `/unsubscribe/[token]/` page with UnsubscribeConfirmation component: auto-calls API on mount, re-subscribe link
- `/preferences/[token]/` page with PreferencesForm component: loads current toggles, save with feedback, unsubscribe link
- Footer updated with "Subscribe to Intelligence Blast" link
- API client functions: `subscribe()`, `unsubscribe()`, `fetchPreferences()`, `updatePreferences()`
- TypeScript interfaces: `SubscribeRequest`, `SubscriberResponse`, `UnsubscribeResponse`, `PreferenceUpdate`

### Technical
- 33 new frontend tests (3 component test files + 1 API test file), 683 total (516 backend + 167 frontend)
- Follows existing patterns: Breadcrumb, metadata, `"use client"` for interactive components, server components for pages
- Dynamic routes use `params: Promise<{ token: string }>` pattern (Next.js 14 App Router)

---

## Sprint 2.3 — Broadcast Sending + Confirmation Email (2026-03-01)

### Added
- Broadcast sender service: sends individual emails via Brevo transactional API with per-recipient tracking
- Each broadcast email includes personalised unsubscribe and preferences links in footer
- Status transitions: DRAFT → SENDING → SENT (or FAILED on error)
- BroadcastRecipient tracks SENT/FAILED per-email with brevo_message_id
- Rate limited: 0.5s between emails to stay within Brevo free tier
- Dev mode: logs to console when no BREVO_API_KEY (no real emails sent)
- Confirmation email service: welcome email on new subscriber with preferences/unsubscribe links
- Management command `send_broadcast --id <pk>` for Cloud Run Job execution
- Broadcast detail view at `/broadcast/<pk>/` with per-recipient delivery status table
- Send button on preview page (POST with JavaScript confirmation dialog)

### Technical
- Atomic conditional UPDATE prevents race condition on concurrent send requests
- Try/finally ensures broadcast never stuck in SENDING state (transitions to FAILED on error)
- Recipient loop uses `select_related("subscriber")` to avoid N+1 queries
- Confirmation email sent outside `transaction.atomic()` to avoid holding DB connection during API call
- HTML template uses `.format()` (not `%s`) to handle content with literal `%` characters
- 32 new tests (sender service + send views + management command + confirmation email), 516 total passing

---

## Sprint 2.2 — Broadcast Models + Admin Compose UI (2026-03-01)

### Added
- New `broadcasts` app with `Broadcast` and `BroadcastRecipient` models
- Broadcast compose form at `/broadcast/compose/` with subject, HTML content, plain text, and audience filters
- Broadcast preview at `/broadcast/preview/<id>/` with sandboxed HTML preview, recipient count, filter summary
- Broadcast list at `/broadcast/` with status, dates, and pagination (50/page)
- Audience filtering service: filter subscribers by category, state, constituency, PPD, enrolment range, SKM eligibility
- `created_by` field on Broadcast for audit trail
- Django admin registration with inline recipient tracking
- Nav link to Broadcasts in base template

### Technical
- Server-side validation for empty subjects and non-numeric enrolment values
- HTML preview sandboxed in `<iframe sandbox="">` to prevent XSS
- States and PPDs dynamically queried from School model (not hardcoded)
- `UniqueConstraint` on (broadcast, subscriber) pair
- 47 new tests (13 model + 15 audience service + 19 views), 484 total passing

---

## Sprint 1.10 — School Page Redesign + Image Fix (2026-03-01)

### Added
- School mentions API endpoint: `GET /api/v1/schools/<moe_code>/mentions/` — returns approved parliamentary mentions
- Multi-photo image harvester: Google Places now fetches up to 3 photos per school (was 1)
- `SchoolImageSerializer` + `images` array in school detail API response
- `SchoolImageData` TypeScript type on frontend
- `SchoolPhotoGallery` component: hero image + thumbnails, fallback chain (Places → satellite → placeholder)
- `SchoolHistory` component: "Help us tell this school's story" CTA with contact link
- `NewsWatchSection` component: placeholder for upcoming news monitoring
- New school page layout: photo gallery → name/Tamil name → stats → details → map → Parliament Watch → News Watch → History → sidebar → Claim button

### Fixed
- Google Maps API key rotation: replaced deleted key in all 528 stored image URLs
- Updated `GOOGLE_MAPS_API_KEY` env var on backend Cloud Run service
- Redeployed frontend + backend with new API key

### Technical
- `MentionsSection` renders approved `HansardMention` records via bridge table
- Image harvester does clean re-harvest (deletes old PLACES images before creating new)
- First Places photo promoted to primary; satellite demoted to secondary
- 437 backend tests passing

---

## Sprint 2.1 — Subscriber Models + Subscribe/Unsubscribe API (2026-03-01)

### Added
- New `subscribers` Django app with `Subscriber` and `SubscriptionPreference` models
- `Subscriber`: email (unique), name, organisation, is_active, unsubscribe_token (UUID), subscribed/unsubscribed timestamps
- `SubscriptionPreference`: per-subscriber toggle for PARLIAMENT_WATCH, NEWS_WATCH, MONTHLY_BLAST categories
- Service layer (`subscriber_service.py`): subscribe (with reactivation), unsubscribe, get/update preferences
- REST API endpoints:
  - `POST /api/v1/subscribers/subscribe/` — create subscriber with all preferences enabled (idempotent)
  - `GET /api/v1/subscribers/unsubscribe/<token>/` — one-click unsubscribe via token
  - `GET/PUT /api/v1/subscribers/preferences/<token>/` — view/update category preferences
- Admin registration with inline preferences
- 51 new tests (16 model + 17 service + 18 API)

### Technical
- Email normalised to lowercase on subscribe
- Duplicate subscribe returns 200 (not 400) — idempotent
- Reactivation: previously unsubscribed users are reactivated on re-subscribe
- Preferences auto-created for all categories on subscribe or first access
- All endpoints are public (no authentication required) — tokens provide access control

### Test count: 426 (375 existing + 51 new)

---

## Sprint 1.9 — Full Stack Deployment + Phase 1 Close (2026-02-28)

### Infrastructure
- New GCP project `sjktconnect` created under `tamilfoundation.org` organisation (previously on personal account)
- Backend deployed as `sjktconnect-api` on Cloud Run (asia-southeast1)
- Frontend deployed as `sjktconnect-web` on Cloud Run (asia-southeast1) — first frontend deployment
- Google Maps API key created and restricted to Maps JS, Static Maps, Places APIs
- CORS configured: frontend origin whitelisted on backend
- Cloud Run job `sjktconnect-check-hansards` recreated in new project
- Cloud Scheduler `sjktconnect-daily-check` recreated (daily 8am MYT)

### Changed
- Frontend Dockerfile: switched from ARG to ENV for `NEXT_PUBLIC_*` build vars (Cloud Build doesn't pass build args)
- Backend ALLOWED_HOSTS and CSRF_TRUSTED_ORIGINS updated for new URLs

### Data
- 528 satellite images harvested into production database (all schools with GPS coordinates)

### Post-Sprint Follow-ups (2026-03-01)
- Custom domain `tamilschool.org` mapped to Cloud Run (auto-verified via domain provider)
- BREVO_API_KEY set on backend; Brevo sender domain `tamilschool.org` authenticated (DKIM + DMARC)
- GEMINI_API_KEY set on backend for AI analysis commands
- Upgraded map markers from deprecated `Marker` to `AdvancedMarker` with indigo `Pin` styling
- Added Google Maps Map ID (`ce9504578e73fb7dd21b6704`) to Dockerfile
- Fixed outreach email encoding: replaced literal em dashes with `&mdash;` entities
- Deleted old `sjktconnect-api` from personal GCP project (`gen-lang-client-0871147736`)
- Removed stale `tamilschool.org.my` domain mapping

---

## Sprint 1.8 — Outreach App + School Images + Email Outreach (2026-02-28)

### Added
- `outreach` Django app (6th app) with `SchoolImage` and `OutreachEmail` models + migration
- `SchoolImage` model: image URL, source (SATELLITE/STREET_VIEW/PLACES/MANUAL), primary flag, attribution, photo reference
- `OutreachEmail` model: recipient, subject, status (PENDING/SENT/FAILED/BOUNCED), Brevo message ID tracking
- `harvest_school_images` management command — Google Static Maps (satellite) + Places API (real photos), `--limit`, `--state`, `--source`, `--dry-run` flags
- `send_outreach_emails` management command — Brevo introduction emails with school page + claim links, `--limit`, `--state`, `--dry-run` flags, skips already-emailed schools
- Image harvester service: `harvest_satellite_image` (GPS → static map URL), `harvest_places_image` (Places API search + photo reference), `harvest_images_for_school` (both sources)
- Email sender service: `send_outreach_email` with Brevo API integration and console fallback in dev
- Admin registration for SchoolImage and OutreachEmail with list display, filters, search
- `SchoolImage` frontend component — responsive image with lazy loading, rounded border
- `GOOGLE_MAPS_API_KEY` backend env var (falls back to `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY`)
- 34 new backend tests: satellite harvest (5), places harvest (6), combined harvest (2), harvest command (5), email sending (4), email model (2), image model (2), email command (6), API image_url (2)
- 3 new frontend tests: SchoolImage component (src/alt, lazy loading, responsive classes)

### Changed
- `SchoolDetailSerializer` now includes `image_url` field (primary image URL from SchoolImage or null)
- School profile page displays hero image above header when `image_url` is available
- `SchoolDetail` TypeScript type extended with `image_url: string | null`
- `INSTALLED_APPS` in base settings: added `outreach`

### Test totals
- Frontend: 134 passing (+3)
- Backend: 375 passing (+34)
- **Total: 509**

---

## Sprint 1.7 — School Data Confirm/Edit + Admin Dashboard (2026-02-28)

### Added
- `IsMagicLinkAuthenticated` DRF permission class in `accounts/permissions.py` — validates session-based Magic Link auth, sets `request.school_contact` and `request.school_moe_code`
- `SchoolEditSerializer` — writable fields for school data (address, phone, enrolment, GPS, etc.), read-only for identity fields
- `GET/PUT /api/v1/schools/{code}/edit/` — authenticated reps can view and update their school's editable fields; creates AuditLog with changed_fields
- `POST /api/v1/schools/{code}/confirm/` — 2-click confirmation: updates `last_verified` timestamp without editing
- Next.js edit page at `/school/[moe_code]/edit/` — pre-filled form with confirm button (green, prominent) + edit form with save/cancel
- `SchoolEditForm` component: 16 fields (3 read-only), confirm and save actions, success/error states, last verified display
- `EditSchoolLink` component: client-side auth check, shows "Edit School Data" link only for authenticated school reps
- Admin verification dashboard at `/dashboard/verification/` (Django templates, login required):
  - Progress bar showing verified/total schools
  - Unverified schools by state table (ordered by count)
  - Recently verified schools table (last 20)
  - Registered school contacts table (last 20)
- `schools/views.py` — `VerificationDashboardView` (LoginRequiredMixin + ListView)
- `schools/urls.py` — dashboard URL routing
- "Verification" nav link in base template for authenticated admin users
- CSS styles: `.card`, `.progress-bar-container`, `.progress-bar`, `.progress-text`, `.data-table`, `.muted`
- Frontend types: `SchoolEditData`, `SchoolConfirmResponse`
- Frontend API functions: `fetchSchoolEdit`, `updateSchool`, `confirmSchool` (all with `credentials: "include"`)
- 32 new backend tests: permission class (4), school edit API (8), school confirm API (6), admin dashboard (14)
- 19 new frontend tests: SchoolEditForm (10), EditSchoolLink (3), API edit functions (6)

### Changed
- School profile page: added `EditSchoolLink` alongside ClaimButton
- `schools/api/urls.py`: added edit/confirm routes before detail route (avoids capture conflicts)
- `sjktconnect/urls.py`: added `schools.urls` include for dashboard

### Test totals
- Frontend: 131 passing (+19)
- Backend: 341 passing (+32)
- **Total: 472**

---

## Sprint 1.6 — Magic Link Authentication (2026-02-27)

### Added
- `accounts` Django app with `MagicLinkToken` and `SchoolContact` models
- Magic link API: `POST /api/v1/auth/request-magic-link/`, `GET /api/v1/auth/verify/{token}/`, `GET /api/v1/auth/me/`
- Token service: 24-hour expiry, UUID tokens, single-use validation
- Email service: Brevo transactional email in production, console logging in development
- @moe.edu.my email validation — matches school by MOE code or stored email
- Session-based authentication after token verification
- Next.js claim flow: `/claim/` (email form), `/claim/verify/[token]/` (verification)
- ClaimForm component: email input with pre-fill from school code, loading/success/error states
- ClaimButton now links to `/claim/?school=MOE_CODE` (was disabled placeholder)
- Types: `MagicLinkResponse`, `AuthUser`, `ApiError`
- API functions: `requestMagicLink`, `verifyMagicLink`, `fetchMe`
- Admin: SchoolContact and MagicLinkToken registered with list display/filters/search
- 33 new backend tests: models (7), token service (5), email validation (5), school matching (4), API endpoints (12)
- 14 new frontend tests: ClaimForm (6), auth API (8)

### Changed
- ClaimButton: active link instead of disabled button

### Test totals
- Frontend: 112 passing (+14)
- Backend: 309 passing (+33)
- **Total: 421**

---

## Sprint 1.5 — Constituency + DUN Pages (2026-02-27)

### Added
- Constituency page `/constituency/[code]` with ISR — MP info, scorecard, boundary map, demographics, school table, DUN list
- DUN page `/dun/[id]` with ISR — ADUN info, demographics, boundary map, school table, parent constituency link
- Constituencies index `/constituencies/` — browsable table with state filter, school counts, MP/party info
- BoundaryMap component: Google Maps with GeoJSON overlay for constituency/DUN boundaries
- ScorecardCard component: Parliament Watch scorecard stats (mentions, questions, commitments)
- DemographicsCard component: Indian population, income, poverty rate, Gini, unemployment
- SchoolTable component: sortable school list with links, enrolment, teacher count, PPD
- ConstituencyList component: filterable table with state dropdown
- "Constituencies" nav link added to Header (desktop + mobile)
- API functions: `fetchConstituencies`, `fetchConstituencyDetail`, `fetchConstituencyGeoJSON`, `fetchDUNs`, `fetchDUNDetail`, `fetchDUNGeoJSON`
- Types: `ConstituencyDetail`, `Scorecard`, `DUN`, `DUNDetail`, `GeoJSONFeature`, `GeoJSONFeatureCollection`
- Loading skeletons for constituency and DUN pages
- SEO metadata for all new pages
- 36 new frontend tests: API (9), ScorecardCard (7), DemographicsCard (7), SchoolTable (7), ConstituencyList (6)

### Test totals
- Frontend: 98 passing (+36)
- Backend: 276 passing (unchanged)
- **Total: 374**

---

## Sprint 1.4 — School Profile Pages (2026-02-27)

### Added
- Dynamic school profile route `app/school/[moe_code]/page.tsx` with ISR (revalidates hourly)
- SchoolProfile component: stat cards (enrolment, teachers, grade, SKM), full detail grid, political representation section
- StatCard component: reusable stat display with number formatting
- Breadcrumb navigation: Home > State > School
- ClaimButton component: "Claim This Page" CTA (disabled, coming in Sprint 1.6)
- MiniMap component: embedded Google Map with single school pin
- MentionsSection component: Parliament Watch mentions with MP name, party, significance, date
- ConstituencySchools sidebar: links to other schools in the same constituency
- Loading skeleton (`loading.tsx`) for school pages
- Not-found page for invalid school codes
- API functions: `fetchSchoolDetail`, `fetchSchoolsByConstituency`, `fetchSchoolMentions`
- `SchoolMention` TypeScript type
- SEO metadata: dynamic title, description, Open Graph tags per school
- 36 new frontend tests: API (5), StatCard (3), Breadcrumb (5), ClaimButton (4), MentionsSection (7), ConstituencySchools (4), SchoolProfile (8)

### Test totals
- Frontend: 62 passing (+36)
- Backend: 276 passing (unchanged)
- **Total: 338**

---

## Sprint 1.3 — Next.js Frontend + School Map (2026-02-27)

### Added
- Next.js 14 project in `frontend/` (App Router, Tailwind CSS, TypeScript)
- Layout: responsive Header with mobile menu, Footer with copyright
- Google Maps integration via `@vis.gl/react-google-maps` + `@googlemaps/markerclusterer`
- Full-width map page at `/` showing 528 school pins with automatic clustering
- Info window on marker click: school name, code, state, enrolment, teachers, constituency
- State filter dropdown — narrows map pins by state, shows count
- Search box with 300ms debounced typeahead — searches schools and constituencies via API
- API client (`lib/api.ts`) with automatic pagination through all school pages
- TypeScript types for School, Constituency, PaginatedResponse, SearchResults
- Dockerfile for Cloud Run deployment (standalone output, port 8080)
- `.env.local.example` for Google Maps API key and API URL configuration
- 26 frontend tests: API client (8), Header (4), Footer (3), StateFilter (5), SearchBox (6)

### Changed
- `.gitignore` updated with Node.js / Next.js entries (node_modules, .next, out)

### Test totals
- Frontend: 26 passing (new)
- Backend: 276 passing (unchanged)
- **Total: 302**

---

## Sprint 1.2 — Django REST API for Schools + Constituencies (2026-02-26)

### Added
- REST API endpoints (12 new):
  - `GET /api/v1/schools/` — list with filters: state, ppd, constituency, skm, min/max enrolment
  - `GET /api/v1/schools/<moe_code>/` — full school profile
  - `GET /api/v1/constituencies/` — list with school_count annotation, state filter
  - `GET /api/v1/constituencies/<code>/` — detail with nested schools + scorecard
  - `GET /api/v1/duns/` — list with state/constituency filters
  - `GET /api/v1/duns/<pk>/` — detail with nested schools
  - `GET /api/v1/scorecards/` — list with constituency/party filters
  - `GET /api/v1/scorecards/<pk>/` — MP scorecard detail
  - `GET /api/v1/briefs/` — published sitting briefs only
  - `GET /api/v1/briefs/<pk>/` — single published brief
  - `GET /api/v1/search/?q=<query>` — cross-entity search (schools, constituencies, MPs)
- `schools/api/serializers.py` — 6 serializers (School list/detail, Constituency list/detail, DUN list/detail)
- `parliament/api/` package — serializers, views, URLs for MPScorecard + SittingBrief
- CORS support via `django-cors-headers` with configurable `CORS_ALLOWED_ORIGINS` env var
- DRF pagination (50 items/page via PageNumberPagination)
- 37 new tests: test_school_api (26), test_parliament_api (11)

### Changed
- `schools/api/urls.py` expanded from 4 GeoJSON routes to 15 total routes
- `schools/api/views.py` expanded with School, Constituency, DUN, Search views
- `corsheaders` added to INSTALLED_APPS and MIDDLEWARE
- REST_FRAMEWORK config added to base settings

### Test totals
- 276 tests passing (239 from Sprint 1.1 + 37 new)

---

## Sprint 1.1 — WKT Boundary Import + GeoJSON API (2026-02-26)

### Added
- `boundary_wkt` TextField on Constituency and DUN models — stores OGC WKT polygon boundaries
- GeoJSON API endpoints (4 new):
  - `GET /api/v1/constituencies/geojson/` — all constituency boundaries as FeatureCollection
  - `GET /api/v1/constituencies/<code>/geojson/` — single constituency boundary
  - `GET /api/v1/duns/geojson/` — all DUN boundaries (filters: `?state=`, `?constituency=`)
  - `GET /api/v1/duns/<pk>/geojson/` — single DUN boundary
- `schools/api/` package: `geojson.py` (WKT-to-GeoJSON via shapely), `views.py` (4 DRF views), `urls.py`
- `shapely>=2.0` and `djangorestframework>=3.15` dependencies
- 19 new tests: test_geojson_api (13), test_geojson_helpers (6)

### Changed
- `import_constituencies` now parses WKT column from CSV and stores on DUN records
- `import_constituencies` computes constituency boundaries by unioning DUN polygons via `shapely.ops.unary_union`
- `rest_framework` added to INSTALLED_APPS
- Test CSV encoding fixed from `utf-8-sig` to `cp1252` (matches real CSV)
- Implementation plan and roadmap updated: Neon references replaced with Supabase, PostGIS risk resolved

### Test totals
- 239 tests passing (220 from Sprint 0.6 + 19 new)

---

## Sprint 0.6 — Deployment + Cloud Scheduler + Documentation (2026-02-26)

### Added
- `hansard/pipeline/scraper.py` — Discovers new Hansard PDFs via HEAD requests to parlimen.gov.my, probing date ranges for `DR-DDMMYYYY.pdf` URLs
- `check_new_hansards` management command — compares discovered PDFs against processed sittings in DB; supports `--days`, `--start`/`--end`, `--auto-process` (chains into `process_hansard`)
- Health check endpoint at `/health/` — returns `{"status": "ok"}` for Cloud Run liveness probes
- Cloud Run service `sjktconnect-api` deployed to asia-southeast1
- Cloud Run job `sjktconnect-check-hansards` — runs `check_new_hansards --auto-process --days 7`
- Cloud Scheduler `sjktconnect-daily-check` — triggers job daily at 8:00 AM MYT
- 22 new tests: test_scraper (11), test_check_new_hansards (10), test_health_check (1)

### Changed
- Database switched from planned Neon PostgreSQL to Supabase PostgreSQL (Tamil Foundation org, Singapore region, free tier)
- Production settings and docs updated from "Neon" to "Supabase"

### Infrastructure
- **Service URL**: https://sjktconnect-api-90344691621.asia-southeast1.run.app
- **Database**: Supabase PostgreSQL (transaction pooler, port 6543)
- **Reference data imported**: 222 constituencies, 613 DUNs, 528 schools, 2,106 aliases
- **Admin user**: admin@tamilfoundation.org

### Test totals
- 220 tests passing (198 from Sprint 0.5 + 22 new)

---

## Sprint 0.5 — Admin Review Queue + Content Publishing (2026-02-25)

### Added
- `MentionReviewForm` — ModelForm for editing AI analysis fields (mp_name, constituency, party, mention_type, significance, sentiment, change_indicator, ai_summary, review_notes)
- 8 Django views in `parliament/views.py`:
  - Admin (login required): ReviewQueueView, SittingReviewView, MentionDetailView, ApproveMentionView, RejectMentionView, PublishBriefView
  - Public: ParliamentWatchView, BriefDetailView
- 8 URL patterns in `parliament/urls.py` with `app_name = "parliament"`
- Root URL wiring: Django built-in LoginView/LogoutView at `/accounts/login/` and `/accounts/logout/`
- `highlight_keywords` template filter — wraps SJK(T) variants (6 regex patterns) in `<mark>` tags
- 7 templates: base.html (navbar + footer), queue, sitting_review, detail (split-screen), watch, brief, login
- `static/css/style.css` — full stylesheet with CSS variables, responsive split-screen grid, mention cards with status-coloured borders, keyword highlight styling
- 49 new tests: test_views (33), test_highlight (12), test_forms (4)

### Fixed
- Approve/reject redirect bug — was pointing to `mention-detail` with sitting ID (wrong lookup), fixed to redirect to `sitting-review`
- Empty significance field crash — IntegerField received `''` from blank ChoiceField. Fixed with `TypedChoiceField(coerce=int, empty_value=None)`

### Design decisions
- Split-screen review: left panel shows verbatim quote with keyword highlights + context; right panel shows editable AI analysis form
- Approve saves form edits + sets status in one POST; reject only saves review_notes + status
- PublishBriefView delegates to `generate_brief()` then sets `is_published=True`
- Public views have no auth requirement; admin views use `LoginRequiredMixin`
- ChoiceFields include blank option `("", "---")` so reviewers can clear AI-set values

### Test totals
- 198 tests passing (149 from Sprint 0.4 + 49 new)

---

## Sprint 0.4 — Gemini AI Analysis + MP Scorecard (2026-02-25)

### Added
- `parliament` app with `MPScorecard` and `SittingBrief` models
- Service modules in `parliament/services/`:
  - `gemini_client.py` — Gemini Flash API wrapper using `google.genai` SDK, structured JSON output, token budgeting (~1500 chars per call), response validation with enum clamping
  - `scorecard.py` — aggregates all analysed mentions per MP: total, substantive (significance >= 3), questions, commitments. Caches school count and enrolment from constituency. Idempotent recalculation with stale scorecard cleanup.
  - `brief_generator.py` — generates markdown sitting brief, renders to HTML, creates social post (<= 280 chars). Falls back to all analysed mentions if none approved yet.
- `analyse_mentions` management command — processes unanalysed mentions via Gemini, with `--dry-run`, `--limit`, `--sitting-date` options
- `update_scorecards` management command — full recalculation of all MP scorecards
- Admin registration for MPScorecard and SittingBrief
- 38 new tests: gemini_client (12), scorecard (13), brief_generator (13) — all Gemini calls mocked
- `google-genai` and `markdown` added to requirements.txt

### Design decisions
- Used `google.genai` SDK (not deprecated `google.generativeai`) — client pattern instead of global configuration
- Response validation: enum fields clamped to valid values, significance clamped 1-5, missing fields get sensible defaults
- Cross-platform date formatting helper (Windows lacks `%-d` strftime flag)
- Scorecard `update_or_create` pattern: full recalculation each run, stale records deleted
- Brief generator prefers APPROVED mentions but falls back to all analysed for early-stage use (before Sprint 0.5 review queue)

### Test totals
- 149 tests passing (111 from Sprint 0.3 + 38 new)

---

## Sprint 0.3 — School Name Matching (2026-02-25)

### Improved (code simplification pass)
- Hoisted `_BOUNDARY_WORDS` set and prefix regex to module-level constants in `matcher.py` (were recreated per call)
- Cached `_get_tracked_models()` in `signals.py` — was resolving on every Django signal
- Changed tracked models from `list` to `set` for O(1) membership checks
- Consolidated duplicate regex patterns for `s.j.k.(t)` / `s.j.k(t)` in `normalizer.py`
- Removed unused imports (`STOP_WORDS`, `re`) and unused variables (`all_alias_keys`, `quote`)
- Fixed f-string logging to use `%s` lazy formatting in `signals.py`

### Added
- `SchoolAlias` model — stores multiple name variants per school (official, short, common, SJKT, Hansard-discovered)
- `MentionedSchool` bridge model — links HansardMention to School with confidence score and match method
- `seed_aliases` management command — auto-generates ~4 aliases per school from official/short names
- Pipeline modules in `hansard/pipeline/`:
  - `matcher.py` — two-pass matching: exact alias lookup (100% confidence) then trigram similarity with difflib fallback
  - `stop_words.py` — 20 high-frequency words excluded from fuzzy matching (school prefixes + location words)
- pg_trgm extension migration (conditional — skips on SQLite, applies on PostgreSQL)
- Matcher integrated into `process_hansard` pipeline (Step 7, with `--skip-matching` flag)
- Admin registration for SchoolAlias and MentionedSchool
- 41 new tests: matcher (19), seed_aliases (11), stop_words (7), models (4)

### Design decisions
- Candidate extractor uses Malay boundary words (dan, di, yang, untuk, etc.) to stop capturing after the school name
- Progressive shortening: candidates trimmed word-by-word from right for exact match boundary detection
- Confidence < 80% auto-flagged as needs_review for human verification
- HANSARD alias type preserved during `--clear` re-seeding

### Test totals
- 111 tests passing (70 from Sprint 0.2 + 41 new)

---

## Sprint 0.2 — Hansard Download + Text Extraction + Keyword Search (2026-02-25)

### Added
- `hansard` app with HansardSitting and HansardMention models
- Pipeline modules in `hansard/pipeline/`:
  - `downloader.py` — HTTP download with retries, Content-Disposition support, parlimen.gov.my SSL workaround
  - `extractor.py` — pdfplumber text extraction (page by page)
  - `normalizer.py` — text normalisation: Unicode NFKC, lowercase, whitespace collapse, SJK(T) variant canonicalisation
  - `searcher.py` — keyword search with ±500 chars context extraction and verbatim quote mapping
  - `keywords.py` — primary (12) and secondary (7) keyword lists, DB school name loader
- `process_hansard <url>` management command with `--sitting-date`, `--catalogue-variants`, `--dest-dir` options
- Date extraction from Hansard filename pattern (DR-DDMMYYYY.pdf)
- Admin registration for HansardSitting and HansardMention
- 44 new tests: normaliser (13), searcher (12), downloader (10), pipeline integration (6), models (3)
- pdfplumber and requests added to requirements.txt

### Tested against real data
- 3 real Hansard PDFs processed (26 Jan, 28 Jan, 23 Feb 2026)
- 5 mentions found across 2 sittings (1 sitting had zero mentions — expected)
- Variant catalogue: "sjk(t)" (3 occurrences), "sekolah jenis kebangsaan tamil" (2 occurrences)
- Normaliser correctly handles: SJK(T), SJKT, S.J.K.(T), S.J.K(T), non-breaking spaces

### Test totals
- 70 tests passing (26 from Sprint 0.1 + 44 new)

---

## Sprint 0.1 — Project Scaffold + Reference Data Import (2026-02-25)

### Added
- Django project scaffold with split settings (base/development/production)
- `core` app: AuditLog model with post_save/post_delete signals and request middleware
- `schools` app: Constituency, DUN, School models
- `import_constituencies` management command — imports 222 constituencies and 613 DUNs from Political Constituencies CSV
- `import_schools` management command — imports 528 SJK(T) schools from MOE Excel, with GPS verification CSV override
- 26 tests across 3 test files (models, import_constituencies, import_schools)
- Project infrastructure: requirements.txt, Dockerfile, pytest.ini, .env.example, .gitignore, .dockerignore

### Fixed
- DUN model: changed from `code` as primary key to auto-generated PK with `unique_together = (code, constituency)` — DUN codes like "N01" repeat across all 13 states
- CSV encoding: Political Constituencies CSV uses cp1252, not UTF-8
- MOE Excel format: PARLIMEN/DUN columns contain names only (no codes), added name-based lookup fallback

### Data verification
- 222 constituencies, 613 DUNs, 528 schools imported
- 528/528 schools linked to constituency (100%)
- 513/528 schools linked to DUN (97% — 15 KL schools have no DUN, correct)
- 476/528 GPS coordinates verified from verification CSV
