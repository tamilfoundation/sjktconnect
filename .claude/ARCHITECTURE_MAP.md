# SJK(T) Connect — Architecture Map

Last updated: Sprint 1.6 (27 Feb 2026)

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
│   ├── api/
│   │   ├── serializers.py
│   │   ├── views.py      # SchoolList, SchoolDetail, ConstituencyList/Detail, DUNList/Detail
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
└── accounts/             # Magic Link authentication (Sprint 1.6)
    ├── models.py         # MagicLinkToken (UUID, 24h expiry), SchoolContact (verified rep)
    ├── services/
    │   ├── token.py      # validate_moe_email, find_school_by_email, create/verify tokens
    │   └── email.py      # Brevo transactional email (console fallback in dev)
    ├── api/
    │   ├── serializers.py
    │   ├── views.py      # RequestMagicLink, VerifyToken, Me
    │   └── urls.py       # /auth/ endpoints
    └── admin.py          # SchoolContact + MagicLinkToken admin
```

## Frontend — Next.js App Router

```
frontend/
├── app/
│   ├── layout.tsx                     # Root layout: Header + Footer + Google Maps APIProvider
│   ├── page.tsx                       # Home: school map with 528 pins, search, state filter
│   ├── school/[moe_code]/
│   │   ├── page.tsx                   # ISR (1hr). School profile: stats, details, political rep
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
│   └── claim/
│       ├── page.tsx                   # Claim form: enter @moe.edu.my email
│       └── verify/[token]/
│           └── page.tsx               # Token verification: success/error states
│
├── components/
│   ├── Header.tsx          # Nav: School Map, Constituencies, Parliament Watch
│   ├── Footer.tsx
│   ├── SchoolMap.tsx       # Google Map + MarkerClusterer (home page)
│   ├── SchoolMarkers.tsx   # AdvancedMarker pins for schools
│   ├── SearchBox.tsx       # Typeahead school search
│   ├── StateFilter.tsx     # State dropdown filter
│   ├── SchoolProfile.tsx   # School detail: stat cards + info grid + political rep
│   ├── StatCard.tsx        # Reusable stat display (label + value + icon)
│   ├── Breadcrumb.tsx      # Navigation breadcrumbs
│   ├── ClaimButton.tsx     # "Claim this school" CTA — links to /claim/?school=CODE
│   ├── ClaimForm.tsx       # Email form: MOE email input, loading/success/error states
│   ├── MiniMap.tsx         # Single-pin embedded Google Map
│   ├── MentionsSection.tsx # Parliament Watch mentions list
│   ├── ConstituencySchools.tsx  # Sidebar: other schools in same constituency
│   ├── BoundaryMap.tsx     # GeoJSON boundary overlay on Google Map
│   ├── ScorecardCard.tsx   # MP Parliament Watch scorecard
│   ├── DemographicsCard.tsx    # Demographics: population, income, poverty, Gini
│   ├── SchoolTable.tsx     # School list table (constituency/DUN pages)
│   └── ConstituencyList.tsx    # Filterable constituency table (index page)
│
├── lib/
│   ├── types.ts            # All TypeScript interfaces
│   └── api.ts              # API client: fetchSchools, fetchSchoolDetail, fetchConstituencies, auth, etc.
│
└── __tests__/              # Jest + React Testing Library
    ├── components/         # 15 component test files
    └── lib/                # 4 API test files (schools, constituencies, school detail, auth)
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
  └── has many MagicLinkTokens (FK school)    ← auth tokens

HansardSitting (PK: auto ID, unique: sitting_date)
  └── has many HansardMentions (FK sitting)
       └── has many MentionedSchools (FK mention)  ← bridge to School

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
| `/auth/request-magic-link/` | POST | Send magic link email (requires @moe.edu.my) |
| `/auth/verify/{token}/` | GET | Verify token, create session + SchoolContact |
| `/auth/me/` | GET | Current authenticated school contact |

## Key Design Decisions

- **ISR over SSG**: `revalidate = 3600` avoids build-time API dependency. Pages refresh hourly.
- **DUN routes by ID not code**: DUN codes (N01, N02...) repeat across states. Numeric ID is globally unique.
- **WKT → GeoJSON on the fly**: Boundaries stored as WKT text. `geojson.py` converts at request time.
- **Auto-pagination in API client**: `fetchConstituencies()` iterates all pages automatically.
- **Google Maps Data Layer for boundaries**: `map.data.addGeoJson()` instead of a Polygon component.
- **Magic Link over passwords**: Schools don't need accounts — verify via MOE email, session-based auth.
- **Brevo with console fallback**: No API key in dev → logs magic link to console. No paid service needed for development.
