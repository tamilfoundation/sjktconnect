# SJK(T) Connect — Architecture Map

Last updated: Quality Engine sprint close (7 Mar 2026)

## Stack

- **Backend**: Django 5.1 + DRF — Python 3.12, SQLite (dev), Supabase PostgreSQL (prod)
- **Frontend**: Next.js 14 App Router — TypeScript, Tailwind CSS, Google Maps
- **AI**: Gemini 2.5 Flash (Hansard analysis, news analysis, report generation, quality evaluation)
- **Infra**: Cloud Run (API + Web), Cloud Run Jobs (6 jobs), Cloud Scheduler (6 schedules), Supabase (DB)
- **Email**: Brevo transactional API (noreply@tamilschool.org, feedback@tamilschool.org)
- **Domain**: tamilschool.org

## Backend — Django Apps

```
backend/
├── sjktconnect/          # Project settings (base/dev/prod split)
│   ├── settings/
│   ├── urls.py           # Root URL conf: /admin, /api/v1/, /review/, /dashboard/
│   └── wsgi.py
│
├── core/                 # Cross-cutting concerns
│   ├── models.py         # AuditLog (immutable action log)
│   ├── middleware.py      # Request/audit middleware
│   └── signals.py        # Post-save hooks
│
├── schools/              # School + geography data
│   ├── models.py         # Constituency, DUN, School, SchoolAlias, SchoolLeader
│   ├── utils.py          # to_proper_case(), format_phone() — data quality utilities
│   ├── views.py          # VerificationDashboardView (admin, login required)
│   ├── urls.py           # /dashboard/verification/
│   ├── api/
│   │   ├── serializers.py  # SchoolList/Detail/Edit, SchoolLeader, Constituency, DUN serializers
│   │   ├── views.py      # SchoolList, SchoolDetail, SchoolEdit, SchoolConfirm, Constituency/DUN
│   │   ├── geojson.py    # GeoJSON endpoint (WKT → GeoJSON conversion via shapely)
│   │   └── urls.py       # /schools/, /constituencies/, /duns/
│   └── management/commands/
│       ├── import_schools.py         # Excel → School records (proper case, data/ folder)
│       ├── import_constituencies.py  # CSV → Constituency + DUN + demographics
│       ├── seed_aliases.py           # Generate SchoolAlias from School names (~4 per school)
│       └── verify_school_pins.py     # GPS verification via Google Places API
│
├── hansard/              # Hansard pipeline (scrape → extract → match)
│   ├── models.py         # HansardSitting, HansardMention, MentionedSchool
│   ├── pipeline/
│   │   ├── scraper.py    # parlimen.gov.my calendar scraper (SSL bypass)
│   │   ├── downloader.py # Download PDF (ranged GET, HEAD blocked)
│   │   ├── extractor.py  # PDF → text extraction (pdfplumber) + clean_extracted_text
│   │   ├── searcher.py   # Keyword search in text
│   │   ├── keywords.py   # Tamil school keyword list
│   │   ├── normalizer.py # Text normalisation for matching
│   │   ├── matcher.py    # Match mentions → schools (alias + trigram)
│   │   └── stop_words.py # False-positive filter
│   └── management/commands/
│       ├── run_hansard_pipeline.py  # Full 7-step pipeline (Sprint 5.1)
│       ├── check_new_hansards.py    # Discovery: scrape + process new sittings
│       ├── process_hansard.py       # Process a single sitting
│       ├── rebuild_all_hansards.py  # Re-process all sittings (Sprint 5.2)
│       └── scrape_ge15_results.py   # Scrape GE15 election data from undi.info
│
├── parliament/           # Parliament Watch (AI analysis + reports + quality engine)
│   ├── models.py         # MPScorecard, SittingBrief, ParliamentaryMeeting, MP,
│   │                     # MeetingIllustration, QualityLog, quality_flag on Brief/Meeting
│   ├── services/
│   │   ├── gemini_client.py    # Gemini API wrapper (google.genai SDK)
│   │   ├── brief_generator.py  # Generate sitting briefs + quality loop integration
│   │   ├── scorecard.py        # Compute/update MP scorecards
│   │   ├── mp_scraper.py       # Scrape MP profiles (parlimen.gov.my + mymp.org.my)
│   │   ├── mp_resolver.py      # Cross-ref mention speakers → 222 MP records
│   │   ├── evaluator.py        # Quality evaluator: Gemini rubric scoring, fail-open (Quality Engine)
│   │   ├── corrector.py        # Quality corrector: re-prompt + code fixes, 3-attempt circuit breaker
│   │   ├── name_repairer.py    # School name repair: comma/filler removal, fuzzy matching
│   │   └── learner.py          # Pattern detection: recurring Tier 2 low scores across reports
│   ├── api/
│   │   ├── serializers.py      # Meeting, Brief, Scorecard, MP serializers
│   │   ├── views.py            # Meeting list/detail, illustration endpoint
│   │   └── urls.py             # /meetings/, /briefs/, /scorecards/
│   ├── views.py          # Django template views (admin review queue)
│   ├── forms.py          # MentionReviewForm
│   ├── templatetags/
│   │   └── highlight.py  # Template filter for keyword highlighting
│   └── management/commands/
│       ├── analyse_mentions.py        # AI analysis of mentions (Gemini)
│       ├── update_scorecards.py       # Recompute all MP scorecards
│       ├── generate_meeting_reports.py # Generate meeting reports + quality loop
│       ├── import_mp_profiles.py      # Scrape + import MP profiles
│       ├── regenerate_briefs.py       # Re-generate all sitting briefs
│       ├── backfill_mp_names.py       # Backfill MP names on mentions
│       ├── backfill_speakers.py       # Backfill speakers from Hansard text
│       └── dedup_mentions.py          # Remove duplicate mentions
│
├── accounts/             # Magic Link authentication (Sprint 1.6)
│   ├── models.py         # MagicLinkToken (UUID, 24h expiry), SchoolContact (verified rep)
│   ├── permissions.py    # IsMagicLinkAuthenticated — DRF permission
│   ├── services/
│   │   ├── token.py      # validate_moe_email, find_school_by_email, create/verify tokens
│   │   └── email.py      # Brevo transactional email (console fallback in dev)
│   └── api/              # /auth/ endpoints
│
├── outreach/             # School images + email outreach (Sprint 1.8)
│   ├── models.py         # SchoolImage (satellite/places/manual), OutreachEmail
│   ├── services/
│   │   ├── image_harvester.py  # Google Static Maps + Places API image harvesting
│   │   └── email_sender.py     # Brevo outreach email sending
│   └── management/commands/
│       ├── harvest_school_images.py
│       └── send_outreach_emails.py
│
├── subscribers/          # Subscriber management (Sprint 2.1)
│   ├── models.py         # Subscriber (email, verified), SubscriptionPreference
│   ├── services/
│   │   └── confirmation.py  # Brevo confirmation email on subscribe
│   └── api/              # /subscribers/ endpoints (subscribe, unsubscribe, preferences)
│
├── broadcasts/           # Broadcast messaging (Sprint 2.2-2.3, 2.7)
│   ├── models.py         # Broadcast (draft/sent), BroadcastRecipient
│   ├── services/
│   │   ├── sender.py          # Brevo send, rate limiting, per-recipient tracking
│   │   ├── audience.py        # Audience filtering (category, state, constituency)
│   │   └── blast_aggregator.py # Monthly blast: top mentions, articles, scorecards
│   ├── views.py          # Admin: compose, preview, list
│   ├── templates/        # Admin views + monthly_blast.html email template
│   └── management/commands/
│       ├── send_broadcast.py
│       └── compose_monthly_blast.py
│
├── newswatch/            # News monitoring pipeline (Sprint 2.5-2.6)
│   ├── models.py         # NewsArticle (NEW → EXTRACTED → ANALYSED, review lifecycle)
│   ├── services/
│   │   ├── rss_fetcher.py       # Google Alerts RSS parser, URL dedup
│   │   ├── article_extractor.py # trafilatura body text extraction
│   │   └── news_analyser.py     # Gemini AI analysis (relevance, sentiment, urgency)
│   ├── views.py          # Admin review queue + detail + approve/reject/toggle-urgent
│   └── management/commands/
│       ├── fetch_news_alerts.py
│       ├── extract_articles.py
│       ├── analyse_news_articles.py
│       └── run_news_pipeline.py  # Full pipeline: fetch → extract → analyse
│
└── donations/            # Online donations (Sprint 4.1-4.2)
    ├── models.py         # Donation (Toyyib Pay integration)
    ├── services.py       # Toyyib Pay API wrapper (create bill, verify payment)
    ├── api/
    │   ├── serializers.py
    │   ├── views.py      # Create donation, Toyyib callback, payment status
    │   └── urls.py       # /donations/ endpoints
    └── management/commands/
        └── import_bank_details.py  # Import bank details from TF Excel
```

## Quality Engine (Self-Correcting Report Engine)

```
Generator → Evaluator → Corrector → Learner
                ↓              ↓
           QualityLog    Re-prompt Gemini
                ↓
         quality_flag (GREEN/AMBER/RED)
```

- **Evaluator** (`evaluator.py`): Gemini scores output against 3-tier rubric. Fail-open — API errors = PASS.
- **Corrector** (`corrector.py`): Targeted re-prompt + deterministic code fixes. 3-attempt circuit breaker.
- **Name Repairer** (`name_repairer.py`): Comma removal, filler word removal, fuzzy matching (SequenceMatcher ≥0.7).
- **Learner** (`learner.py`): Detects recurring Tier 2 low scores across reports. Writes to `docs/quality/learner-patterns.md`.
- **Rubric** (`docs/quality/rubric.md`): Permanent quality standard. Tier 1 (red lines), Tier 2 (scored 1-10), Tier 3 (drift detection).
- **Prompt Registry** (`docs/quality/prompt-registry.md`): Version tracking for all Gemini prompts.
- **QualityLog** model: Records every evaluation cycle (scores, corrections, verdict) for auditing.

## Frontend — Next.js App Router + next-intl (i18n)

```
frontend/
├── app/[locale]/                      # All pages under locale prefix (en/ta/ms)
│   ├── layout.tsx                     # NextIntlClientProvider + Header + Footer
│   ├── page.tsx                       # Home: school map, search, stats bar
│   ├── school/[moe_code]/page.tsx     # School profile (ISR 1hr)
│   ├── school/[moe_code]/edit/page.tsx # Auth-gated school edit
│   ├── constituency/[code]/page.tsx   # Constituency detail + MP card + scorecard
│   ├── constituencies/page.tsx        # Constituency index (filterable)
│   ├── dun/[id]/page.tsx              # DUN detail
│   ├── parliament-watch/page.tsx      # Meeting reports grid
│   ├── parliament-watch/[id]/page.tsx # Individual meeting report
│   ├── parliament-watch/sittings/page.tsx # Sittings list
│   ├── news/page.tsx                  # News articles (paginated)
│   ├── donate/page.tsx                # Donation form → Toyyib Pay
│   ├── donate/thank-you/page.tsx      # Payment status
│   ├── subscribe/page.tsx             # Subscribe form
│   ├── unsubscribe/[token]/page.tsx   # One-click unsubscribe
│   ├── preferences/[token]/page.tsx   # Manage subscription preferences
│   ├── claim/page.tsx                 # Claim school form
│   ├── claim/verify/[token]/page.tsx  # Token verification
│   ├── about/page.tsx                 # About page
│   ├── about-tamil-schools/page.tsx   # Tamil schools background
│   ├── contact/page.tsx               # Contact form
│   ├── data/page.tsx                  # Data provenance
│   ├── faq/page.tsx                   # FAQ
│   ├── issues/page.tsx                # Key issues
│   ├── resources/pta-toolkit/page.tsx # PTA resource toolkit
│   ├── resources/lps-toolkit/page.tsx # LPS resource toolkit
│   ├── privacy/page.tsx               # Privacy policy
│   ├── terms/page.tsx                 # Terms of service
│   └── cookies/page.tsx               # Cookie policy
│
├── components/                        # 44 components
│   ├── Header.tsx, Footer.tsx, LanguageSwitcher.tsx
│   ├── HeroSection.tsx, NationalStats.tsx
│   ├── SchoolMap.tsx, SchoolMarkers.tsx, MapFilterPanel.tsx
│   ├── SearchBox.tsx, StateFilter.tsx, PaginationBar.tsx
│   ├── SchoolProfile.tsx, SchoolImage.tsx, SchoolHistory.tsx
│   ├── SchoolEditForm.tsx, SchoolTable.tsx
│   ├── StatCard.tsx, Breadcrumb.tsx
│   ├── ClaimButton.tsx, ClaimForm.tsx, EditSchoolLink.tsx
│   ├── MiniMap.tsx, BoundaryMap.tsx
│   ├── MentionsSection.tsx, MentionsList.tsx
│   ├── NewsWatchSection.tsx, NewsCard.tsx, NewsList.tsx
│   ├── ContactMPCard.tsx, ElectoralInfluenceCard.tsx
│   ├── ScorecardCard.tsx, DemographicsCard.tsx
│   ├── ConstituencySchools.tsx, ConstituencyList.tsx
│   ├── BriefsList.tsx, MeetingReportsGrid.tsx, MeetingReportsList.tsx
│   ├── SubscribeForm.tsx, UnsubscribeConfirmation.tsx, PreferencesForm.tsx
│   ├── ContactForm.tsx, DonationForm.tsx
│   ├── SupportSchoolCard.tsx          # Bank details + DuitNow QR sidebar
│   └── ReportShareBar.tsx
│
├── i18n/                              # Internationalisation (en, ta, ms)
├── messages/{en,ta,ms}.json           # ~162 translation keys each
├── lib/
│   ├── types.ts                       # All TypeScript interfaces
│   ├── api.ts                         # API client (auto-pagination, all endpoints)
│   └── translations.ts               # MOE jargon → English mapping
└── __tests__/                         # Jest + RTL (282 tests)
```

## Data Models (key relationships)

```
Constituency (PK: code "P140")
  ├── has many DUNs (FK constituency)
  ├── has many Schools (FK constituency)
  ├── has many MPScorecards (FK constituency)
  └── has one MP (FK constituency)             ← Sprint 5.3

DUN (PK: auto ID, unique: code+constituency)
  └── has many Schools (FK dun)

School (PK: moe_code "JBD0050")
  ├── has many SchoolAliases (FK school)
  ├── has many MentionedSchools (FK school)
  ├── has many SchoolContacts (FK school)
  ├── has many SchoolImages (FK school)
  ├── has many OutreachEmails (FK school)
  ├── has many SchoolLeaders (FK school)       ← 4 roles: Chairman, HM, PTA, Alumni
  └── bank fields: bank_name, bank_account_number, bank_account_name

HansardSitting (PK: auto ID, unique: sitting_date)
  └── has many HansardMentions (FK sitting)
       └── has many MentionedSchools (FK mention)

ParliamentaryMeeting (unique: term+session+meeting_number)
  ├── has many SittingBriefs (FK meeting)      ← one per sitting date
  ├── has one MeetingIllustration (FK meeting)  ← Imagen editorial cartoon
  ├── has many QualityLogs (FK meeting)         ← evaluation audit trail
  └── quality_flag: GREEN/AMBER/RED

SittingBrief
  ├── has many QualityLogs (FK sitting_brief)
  └── quality_flag: GREEN/AMBER/RED

QualityLog                                      ← Quality Engine audit
  ├── content_type, sitting_brief FK, meeting FK
  ├── prompt_version, model_used, attempt_number
  ├── verdict (PASS/FIX/REJECT)
  ├── tier1_results, tier2_scores, tier3_flags (JSONFields)
  ├── corrections_applied (JSONField)
  └── quality_flag, created_at

MP (PK: auto ID)                                ← Sprint 5.3
  ├── FK constituency (unique)
  ├── name, party, photo_url, email, phone, facebook_url
  └── data sources: parlimen.gov.my, mymp.org.my

Subscriber (PK: auto ID, unique: email)
  └── has many SubscriptionPreferences (FK subscriber)

Broadcast (PK: auto ID, status: draft → sending → sent)
  └── has many BroadcastRecipients (FK broadcast, FK subscriber)

NewsArticle (PK: auto ID, unique: url)
  └── lifecycle: NEW → EXTRACTED → ANALYSED, review: PENDING → APPROVED/REJECTED

Donation (PK: auto ID)                          ← Sprint 4.2
  └── Toyyib Pay: bill_code, amount, donor info, status

AuditLog — standalone, tracks admin actions
```

## Key Design Decisions

- **ISR over SSG**: `revalidate = 3600` avoids build-time API dependency
- **Fail-open quality engine**: API errors → publish without evaluation, never block
- **Verdict recomputed, not trusted**: Evaluator AI returns verdict, but we recompute from tier scores
- **3-attempt circuit breaker**: Hard cap prevents runaway API costs from correction loops
- **Rubric is permanent, prompts are disposable**: Rubric survives model changes; prompts are versioned
- **Learner writes to files, not code**: Pattern flags go to markdown, agents read — no auto code changes
- **Magic Link over passwords**: Schools verify via MOE email, session-based auth
- **Brevo with console fallback**: No API key in dev → logs to console
- **WKT → GeoJSON on the fly**: Boundaries stored as WKT, converted at request time via shapely
