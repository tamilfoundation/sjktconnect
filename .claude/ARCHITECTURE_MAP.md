# SJK(T) Connect — Architecture Map

Last updated: Sprint 2.5 close (2 Mar 2026)

## Stack

- **Backend**: Django 5.1 + DRF — Python 3.12, SQLite (dev), Supabase PostgreSQL (prod)
- **Frontend**: Next.js 14 App Router — TypeScript, Tailwind CSS, Google Maps
- **Infra**: Cloud Run (API), Cloud Scheduler (daily Hansard check), Supabase (DB)

## Backend — Django Apps

```
backend/
├── sjktconnect/          # Project settings (base/dev/prod split)
│   ├── settings/
│   ├── urls.py           # Root URL conf: /admin, /api/v1/
│   └── wsgi.py
│
├── core/                 # Cross-cutting concerns
│   ├── models.py         # AuditLog (immutable action log)
│   ├── middleware.py      # Request/audit middleware
│   └── signals.py        # Post-save hooks
│
├── schools/              # School + geography data
│   ├── models.py         # Constituency, DUN, School
│   ├── views.py          # VerificationDashboardView (admin, login required)
│   ├── urls.py           # /dashboard/verification/
│   ├── api/
│   │   ├── serializers.py  # SchoolList/Detail/Edit, Constituency, DUN serializers
│   │   ├── views.py      # SchoolList, SchoolDetail, SchoolEdit, SchoolConfirm, Constituency/DUN
│   │   ├── geojson.py    # GeoJSON endpoint (WKT → GeoJSON conversion)
│   │   └── urls.py       # /schools/, /constituencies/, /duns/
│   └── management/commands/
│       ├── import_schools.py         # CSV → School records
│       └── import_constituencies.py  # CSV → Constituency + DUN + demographics
│
├── hansard/              # Hansard pipeline (scrape → extract → match)
│   ├── models.py         # HansardSitting, HansardMention, SchoolAlias, MentionedSchool
│   ├── pipeline/
│   │   ├── scraper.py    # Fetch Hansard index from parliament.gov.my
│   │   ├── downloader.py # Download PDF
│   │   ├── extractor.py  # PDF → text extraction
│   │   ├── searcher.py   # Keyword search in text
│   │   ├── keywords.py   # Tamil school keyword list
│   │   ├── normalizer.py # Text normalisation for matching
│   │   ├── matcher.py    # Match mentions → schools (alias + trigram)
│   │   └── stop_words.py # False-positive filter
│   └── management/commands/
│       ├── check_new_hansards.py  # Daily cron: scrape + process new sittings
│       ├── process_hansard.py     # Process a single sitting
│       └── seed_aliases.py        # Generate SchoolAlias from School names
│
├── parliament/           # Parliament Watch (AI analysis + scorecards)
│   ├── models.py         # MPScorecard
│   ├── services/
│   │   ├── gemini_client.py    # Gemini API wrapper
│   │   ├── brief_generator.py  # Generate briefing notes from mentions
│   │   └── scorecard.py        # Compute/update MP scorecards
│   ├── api/
│   │   ├── serializers.py
│   │   ├── views.py
│   │   └── urls.py       # /parliament/ endpoints
│   ├── views.py          # Django template views (admin-facing)
│   ├── forms.py
│   ├── templatetags/
│   │   └── highlight.py  # Template filter for keyword highlighting
│   └── management/commands/
│       ├── analyse_mentions.py   # AI analysis of mentions (Gemini)
│       └── update_scorecards.py  # Recompute all MP scorecards
│
├── accounts/             # Magic Link authentication (Sprint 1.6)
│   ├── models.py         # MagicLinkToken (UUID, 24h expiry), SchoolContact (verified rep)
│   ├── permissions.py    # IsMagicLinkAuthenticated — DRF permission for session-based auth
│   ├── services/
│   │   ├── token.py      # validate_moe_email, find_school_by_email, create/verify tokens
│   │   └── email.py      # Brevo transactional email (console fallback in dev)
│   ├── api/
│   │   ├── serializers.py
│   │   ├── views.py      # RequestMagicLink, VerifyToken, Me
│   │   └── urls.py       # /auth/ endpoints
│   └── admin.py          # SchoolContact + MagicLinkToken admin
│
├── outreach/             # School images + email outreach (Sprint 1.8)
│   ├── models.py         # SchoolImage (satellite/places/manual), OutreachEmail (Brevo tracking)
│   ├── services/
│   │   ├── image_harvester.py  # Google Static Maps + Places API image harvesting
│   │   └── email_sender.py     # Brevo outreach email sending (console fallback in dev)
│   ├── management/commands/
│   │   ├── harvest_school_images.py  # Harvest images: --limit, --state, --source, --dry-run
│   │   └── send_outreach_emails.py   # Send emails: --limit, --state, --dry-run
│   ├── admin.py          # SchoolImage + OutreachEmail admin
│   └── tests/
│       ├── test_image_harvester.py   # 18 tests (satellite, places, command)
│       └── test_email_sender.py      # 16 tests (email, models, command, API)
│
├── subscribers/          # Subscriber management (Sprint 2.1)
│   ├── models.py         # Subscriber (email, verified), SubscriptionPreference (school/constituency/state)
│   ├── services/
│   │   └── confirmation.py  # Brevo confirmation email on subscribe
│   ├── api/
│   │   ├── serializers.py
│   │   ├── views.py      # Subscribe, Unsubscribe, Preferences
│   │   └── urls.py       # /subscribers/ endpoints
│   └── tests/
│
├── broadcasts/           # Broadcast messaging (Sprint 2.2-2.3)
│   ├── models.py         # Broadcast (draft/sent), BroadcastRecipient (per-recipient tracking)
│   ├── services/
│   │   └── sender.py     # Brevo transactional send, rate limiting, SENT/FAILED tracking
│   ├── views.py          # Django admin views: compose, preview, list
│   ├── forms.py          # BroadcastForm (audience filtering by scope)
│   ├── templates/        # Admin compose/preview/list templates
│   ├── management/commands/
│   │   └── send_broadcast.py  # Management command for sending broadcasts
│   └── tests/
│
└── newswatch/            # News monitoring pipeline (Sprint 2.5)
    ├── models.py         # NewsArticle (NEW → EXTRACTED/FAILED lifecycle)
    ├── services/
    │   ├── rss_fetcher.py       # Google Alerts RSS parser, URL dedup, redirect unwrapping
    │   └── article_extractor.py # trafilatura body text extraction, metadata (source, date)
    ├── management/commands/
    │   ├── fetch_news_alerts.py  # Poll RSS feeds (--url or NEWS_WATCH_RSS_FEEDS setting)
    │   └── extract_articles.py   # Extract body text from NEW articles (--batch-size)
    ├── admin.py          # NewsArticle admin with status/source filters
    └── tests/
```

## Frontend — Next.js App Router

```
frontend/
├── app/
│   ├── layout.tsx                     # Root layout: Header + Footer + Google Maps APIProvider
│   ├── page.tsx                       # Home: school map with 528 pins, search, state filter
│   ├── school/[moe_code]/
│   │   ├── page.tsx                   # ISR (1hr). School profile: stats, details, political rep
│   │   ├── edit/
│   │   │   └── page.tsx               # Client-side. Auth-gated school edit form
│   │   ├── loading.tsx                # Skeleton
│   │   └── not-found.tsx              # 404
│   ├── constituency/[code]/
│   │   ├── page.tsx                   # ISR (1hr). Constituency detail: schools, scorecard, demographics, map
│   │   └── loading.tsx
│   ├── dun/[id]/
│   │   ├── page.tsx                   # ISR (1hr). DUN detail: schools, demographics, map
│   │   └── loading.tsx
│   ├── constituencies/
│   │   └── page.tsx                   # ISR (1hr). Constituency index: filterable table
│   ├── claim/
│   │   ├── page.tsx                   # Claim form: enter @moe.edu.my email
│   │   └── verify/[token]/
│   │       └── page.tsx               # Token verification: success/error states
│   ├── subscribe/
│   │   └── page.tsx                   # Subscribe form: email, name, org, category preview
│   ├── unsubscribe/[token]/
│   │   └── page.tsx                   # One-click unsubscribe confirmation
│   └── preferences/[token]/
│       └── page.tsx                   # Manage subscription category toggles
│
├── components/
│   ├── Header.tsx          # Nav: School Map, Constituencies, Parliament Watch
│   ├── Footer.tsx          # Copyright + subscribe link
│   ├── SchoolMap.tsx       # Google Map + MarkerClusterer (home page)
│   ├── SchoolMarkers.tsx   # AdvancedMarker pins for schools
│   ├── SearchBox.tsx       # Typeahead school search
│   ├── StateFilter.tsx     # State dropdown filter
│   ├── SchoolProfile.tsx   # School detail: stat cards + info grid + political rep
│   ├── StatCard.tsx        # Reusable stat display (label + value + icon)
│   ├── Breadcrumb.tsx      # Navigation breadcrumbs
│   ├── ClaimButton.tsx     # "Claim this school" CTA — links to /claim/?school=CODE
│   ├── ClaimForm.tsx       # Email form: MOE email input, loading/success/error states
│   ├── EditSchoolLink.tsx  # Auth-aware: shows edit link only for authenticated school reps
│   ├── SchoolEditForm.tsx  # Pre-filled school edit form: confirm (2-click) + edit + save/cancel
│   ├── SchoolImage.tsx     # Hero image for school profile (lazy loading, responsive)
│   ├── MiniMap.tsx         # Single-pin embedded Google Map
│   ├── MentionsSection.tsx # Parliament Watch mentions list
│   ├── ConstituencySchools.tsx  # Sidebar: other schools in same constituency
│   ├── BoundaryMap.tsx     # GeoJSON boundary overlay on Google Map
│   ├── ScorecardCard.tsx   # MP Parliament Watch scorecard
│   ├── DemographicsCard.tsx    # Demographics: population, income, poverty, Gini
│   ├── SchoolTable.tsx     # School list table (constituency/DUN pages)
│   ├── ConstituencyList.tsx    # Filterable constituency table (index page)
│   ├── SubscribeForm.tsx       # Subscribe: email/name/org form, category preview, success state
│   ├── UnsubscribeConfirmation.tsx  # Auto-unsubscribe on mount, re-subscribe link
│   └── PreferencesForm.tsx     # Load/toggle/save category preferences
│
├── lib/
│   ├── types.ts            # All TypeScript interfaces
│   └── api.ts              # API client: fetchSchools, fetchSchoolDetail, fetchConstituencies, auth, etc.
│
└── __tests__/              # Jest + React Testing Library
    ├── components/         # 18 component test files
    └── lib/                # 5 API test files (schools, constituencies, school detail, auth, edit)
```

## Data Models (key relationships)

```
Constituency (PK: code "P140")
  ├── has many DUNs (FK constituency)
  ├── has many Schools (FK constituency)
  └── has many MPScorecards (FK constituency)

DUN (PK: auto ID, unique: code+constituency)
  └── has many Schools (FK dun)

School (PK: moe_code "JBD0050")
  ├── has many SchoolAliases (FK school)
  ├── has many MentionedSchools (FK school)
  ├── has many SchoolContacts (FK school)     ← verified reps
  ├── has many MagicLinkTokens (FK school)    ← auth tokens
  ├── has many SchoolImages (FK school)       ← satellite/places photos
  └── has many OutreachEmails (FK school)     ← email tracking

HansardSitting (PK: auto ID, unique: sitting_date)
  └── has many HansardMentions (FK sitting)
       └── has many MentionedSchools (FK mention)  ← bridge to School

Subscriber (PK: auto ID, unique: email)
  └── has many SubscriptionPreferences (FK subscriber)
       └── scope: school/constituency/state + target ID

Broadcast (PK: auto ID)
  ├── has many BroadcastRecipients (FK broadcast, FK subscriber)
  └── status: draft → sending → sent

NewsArticle (PK: auto ID, unique: url)
  └── status: NEW → EXTRACTED or FAILED
       Fields: url, title, source_name, alert_title, published_date, body_text, extraction_error

AuditLog — standalone, tracks all admin actions
```

## API Endpoints (all under /api/v1/)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/schools/` | GET | List schools (paginated, filter: state, constituency) |
| `/schools/<moe_code>/` | GET | School detail |
| `/schools/geojson/` | GET | All schools as GeoJSON FeatureCollection |
| `/constituencies/` | GET | List constituencies (paginated, filter: state) |
| `/constituencies/<code>/` | GET | Constituency detail (includes schools, scorecard) |
| `/constituencies/<code>/geojson/` | GET | Constituency boundary as GeoJSON |
| `/duns/` | GET | List DUNs (filter: constituency) |
| `/duns/<id>/` | GET | DUN detail (includes schools) |
| `/duns/<id>/geojson/` | GET | DUN boundary as GeoJSON |
| `/parliament/` | GET | Parliament Watch views (Django templates) |
| `/schools/<moe_code>/edit/` | GET/PUT | View/update school data (Magic Link auth) |
| `/schools/<moe_code>/confirm/` | POST | 2-click school data confirmation (Magic Link auth) |
| `/auth/request-magic-link/` | POST | Send magic link email (requires @moe.edu.my) |
| `/auth/verify/{token}/` | GET | Verify token, create session + SchoolContact |
| `/auth/me/` | GET | Current authenticated school contact |
| `/subscribers/subscribe/` | POST | Subscribe with email + preferences |
| `/subscribers/unsubscribe/` | POST | Unsubscribe by email + token |
| `/subscribers/preferences/` | GET/PUT | View/update subscription preferences |
| `/broadcasts/compose/` | GET/POST | Admin: compose a broadcast (Django template) |
| `/broadcasts/preview/<id>/` | GET | Admin: preview broadcast before sending |
| `/broadcasts/` | GET | Admin: list all broadcasts |

## Key Design Decisions

- **ISR over SSG**: `revalidate = 3600` avoids build-time API dependency. Pages refresh hourly.
- **DUN routes by ID not code**: DUN codes (N01, N02...) repeat across states. Numeric ID is globally unique.
- **WKT → GeoJSON on the fly**: Boundaries stored as WKT text. `geojson.py` converts at request time.
- **Auto-pagination in API client**: `fetchConstituencies()` iterates all pages automatically.
- **Google Maps Data Layer for boundaries**: `map.data.addGeoJson()` instead of a Polygon component.
- **Magic Link over passwords**: Schools don't need accounts — verify via MOE email, session-based auth.
- **Brevo with console fallback**: No API key in dev → logs magic link to console. No paid service needed for development.
