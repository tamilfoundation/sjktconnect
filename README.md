# SJK(T) Connect

Public-interest intelligence and advocacy platform for Malaysia's 528 SJK(T) (national-type Tamil primary) schools. Live at **[tamilschool.org](https://tamilschool.org)**.

**Status**: v2.0.1 — production maintenance mode (tagged 2026-06-26). Tests: 1436 backend (pytest) + 367 frontend (jest).

---

## What it does

A single platform that watches Malaysian Parliament + national news for every Tamil-school mention, links those mentions to the specific school, ranks them, lets school admins claim and edit their public page, and sends a monthly intelligence digest to ~519 subscribers.

Three layers operating from one Django + Next.js codebase:

1. **Intelligence engine** — AI-powered (Gemini Flash) monitoring of Hansard PDFs + Google News RSS. Auto-classifies each mention (type, significance, sentiment, urgency). Admin-review queue before anything goes public.
2. **Advocacy platform** — Public school directory (528 schools, GPS-pinned, leadership, photos, parliamentary mentions, news mentions, MP/ADUN context, donation links) at SEO-friendly URLs like `/school/<name>-<city>-<moe-code>`.
3. **Communications hub** — Subscriber management, monthly intelligence blast, fortnightly news digest, urgent alerts, parliamentary digests. Reliable broadcast pipeline with Brevo quota awareness + duplicate guards + scheduler.

## Tech stack

- **Backend**: Django 5.2 LTS + DRF · Python 3.13
- **Frontend**: Next.js 16 (App Router) + Tailwind + next-intl (EN/MS/TA trilingual) · TypeScript
- **Database**: Supabase PostgreSQL (Pro plan, Singapore region) with `pg_trgm` fuzzy matching
- **Object storage**: Supabase Storage (`school-images` bucket, ~1500 images, S3-compat via django-storages)
- **AI**: Gemini 2.5 Flash (Hansard analysis, news triage, monthly digest clustering, MP scorecard generation)
- **Email**: Brevo transactional API (DKIM+DMARC verified senders: noreply@tamilschool.org, feedback@tamilschool.org)
- **Hosting**: Google Cloud Run (asia-southeast1) — `sjktconnect-api`, `sjktconnect-web` + 7 jobs
- **CDN/DNS**: Cloudflare (proxied tamilschool.org + api.tamilschool.org, single-redirect ruleset for www→root + legacy URL cleanup)
- **Payments**: Toyyib Pay (Malaysian payment gateway for school donations)
- **Maps**: Google Maps JavaScript API + Places + Static Maps
- **CI/observability**: Cloud Monitoring (egress dashboard, job-failure alerts), GitHub Actions

## Django apps (`backend/`)

| App | Purpose |
|-----|---------|
| `core` | AuditLog model + IP-block / user-agent-block middleware |
| `schools` | School / Constituency / DUN / SchoolLeader models + import commands + utils (`format_phone`, `format_state`, `to_proper_case`) + edit API + revalidation service |
| `hansard` | PDF download / extract / search / match pipeline + SchoolAlias (the canonical alias table — shared with newswatch) |
| `parliament` | MP scrapers + scorecards + AI-generated briefs + meeting reports |
| `accounts` | Google OAuth (NextAuth) + UserProfile + role-based permissions (USER / MODERATOR / SUPERADMIN) + auto-claim on @moe.edu.my email |
| `outreach` | SchoolImage + image harvester (Google Places + satellite) + community photo moderation |
| `subscribers` | Subscriber + SubscriptionPreference + subscribe/unsubscribe/preferences API |
| `broadcasts` | Broadcast composer + sender (Brevo, quota-aware, retry-safe) + monthly digest aggregator + topic clusterer + Send-Test admin UI (SUPERADMIN-gated) |
| `newswatch` | RSS fetcher (Google Alerts) + article extractor (trafilatura) + Gemini analysis + school matcher (Strategy 1.5 SchoolAlias lookup + variant generator with Bhg/Bahagian/Division bridge + spelling-drift aliases) |
| `donations` | DuitNow QR generator + Toyyib Pay integration |
| `community` | Suggestion workflow (3 types, 3 statuses, auto-apply on approve) + image moderation queue + photo upload with Pillow validation |

## Live deployment

- **Frontend**: [tamilschool.org](https://tamilschool.org) — also `sjktconnect-web-748286712183.asia-southeast1.run.app`
- **Backend**: `api.tamilschool.org` — also `sjktconnect-api-748286712183.asia-southeast1.run.app`
- **GCP project**: `sjktconnect` (org: tamilfoundation.org)
- **Health check**: `https://api.tamilschool.org/health/`

### Cloud Run jobs (scheduled)

| Job | Schedule | What |
|---|---|---|
| `sjktconnect-check-hansards` | Daily 08:00 MYT | Discover + process new Hansard PDFs from parlimen.gov.my |
| `sjktconnect-news-pipeline` | Daily 08:30 MYT | Fetch RSS → extract → AI-analyse → auto-triage |
| `sjktconnect-urgent-alerts` | Daily 09:30 MYT | Compose urgent-alert DRAFT (REQUIRE_REVIEW=true default) |
| `sjktconnect-fortnightly-digest` | 1st + 3rd Mon 09:00 MYT | News digest with 14-day coverage guard |
| `sjktconnect-monthly-blast` | 1st of month 09:00 MYT | Monthly intelligence digest with topic clustering + W.P. KL state normalisation + schools-by-state table |
| `sjktconnect-resume-sending` | Daily 10:00 MYT | Drain SENDING broadcasts that paused mid-burst (Brevo quota) + FAILED-sweep alert |
| `sjktconnect-process-feedback` | 4× daily MYT | Gmail fetch → classify → auto-respond on feedback@tamilschool.org |

## Local setup

```bash
git clone https://github.com/tamilfoundation/sjktconnect.git
cd sjktconnect

# Backend
cd backend
python -m venv venv
venv\Scripts\activate    # Windows (bash: source venv/bin/activate)
pip install -r requirements.txt
cp .env.example .env     # Fill in DATABASE_URL, SECRET_KEY, GEMINI_API_KEY, etc.
python manage.py migrate
python manage.py import_constituencies ../data/Political\ Constituencies.csv
python manage.py import_schools ../data/SenaraiSekolahWeb_April2026.xlsx
python manage.py seed_aliases
python manage.py createsuperuser
python manage.py runserver

# Frontend (separate terminal)
cd ../frontend
npm install
cp .env.local.example .env.local    # Fill in NEXT_PUBLIC_API_URL, Maps API key
npm run dev                          # http://localhost:3000
```

## Tests

```bash
# Backend (1436 tests)
cd backend
pytest -q                            # full suite
pytest broadcasts/tests/ -q          # one app
pytest -k test_revalidation -q       # one pattern

# Frontend (367 tests)
cd frontend
npm test                             # full suite
npm test -- --testPathPattern=lib/   # one dir
```

## Deployment

**Always** pass `--account` + `--project` flags. **Never** use `gcloud config set` (only affects current shell; background commands revert to default). **Always** use `--update-env-vars` (merges) over `--set-env-vars` (wipes silently).

```bash
# Backend
cd backend
gcloud run deploy sjktconnect-api \
  --account admin@tamilfoundation.org \
  --project sjktconnect \
  --source . \
  --region asia-southeast1 \
  --allow-unauthenticated

# Frontend
cd frontend
gcloud run deploy sjktconnect-web \
  --account admin@tamilfoundation.org \
  --project sjktconnect \
  --source . \
  --region asia-southeast1 \
  --allow-unauthenticated

# MANDATORY after any backend deploy — sync all 7 jobs to the new api image
./backend/scripts/update_jobs.sh
```

The `update_jobs.sh` step is non-negotiable. Skipping it caused the 2026-05-20 silent-news-rot incident (21 days of crashed news-pipeline runs because jobs were running pre-migration code while the api service had moved on). A Cloud Monitoring alert (id `7654330557139407611`) now fires on 2+ failed job executions in 24h.

## Required environment variables

### Backend (Cloud Run env vars + local `.env`)

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | Yes (prod) | Supabase PostgreSQL — direct connection port 5432 for bulk writes; pooler 6543 can silently drop sequential writes |
| `SECRET_KEY` | Yes (prod) | Django secret key |
| `DJANGO_SETTINGS_MODULE` | Yes | `sjktconnect.settings.production` |
| `ALLOWED_HOSTS` | Yes (prod) | Comma-separated hostnames |
| `CSRF_TRUSTED_ORIGINS` | Yes (prod) | Comma-separated origins (include `https://`) |
| `CORS_ALLOWED_ORIGINS` | Yes (prod) | Comma-separated origins for CORS |
| `GEMINI_API_KEY` | Yes | Google AI Studio API key (Hansard + news + monthly digest) |
| `BREVO_API_KEY` | Yes (prod) | Brevo transactional email |
| `BREVO_WEBHOOK_SECRET` | Optional | HMAC for Brevo delivery-event webhook |
| `GOOGLE_MAPS_API_KEY` | Yes | Backend Maps API key (image harvester) |
| `GOOGLE_OAUTH_CLIENT_ID` | Yes | Google OAuth client ID (community sign-in token verification) |
| `TOYYIBPAY_SECRET_KEY` | Yes (prod) | Toyyib Pay (donations) |
| `TOYYIBPAY_CATEGORY_CODE` | Yes (prod) | Toyyib Pay bill category |
| `GMAIL_CLIENT_ID` / `GMAIL_CLIENT_SECRET` / `GMAIL_REFRESH_TOKEN` | Feedback | OAuth2 for feedback@tamilschool.org Gmail API |
| `REVALIDATE_WEBHOOK_URL` | Yes (prod) | Next.js revalidate route URL (e.g. `https://tamilschool.org/api/revalidate`) |
| `REVALIDATE_TOKEN` | Yes (prod) | Opaque secret matching the web service's `REVALIDATE_TOKEN` (TD-21, Sprint 29) |
| `CLOUDFLARE_API_TOKEN` / `CLOUDFLARE_ZONE_ID` | Optional | Zone-scoped Cloudflare API access for redirect/DNS automation |
| `URGENT_ALERT_REQUIRE_REVIEW` | Optional | Defaults to `true` — urgent-alert job creates DRAFTs not auto-sends |
| `SJKTCONNECT_ALLOW_PROD_DB` | Local opt-in | Required to run destructive `manage.py` commands against production DB |

### Frontend (Cloud Run env vars + local `.env.local`)

| Variable | Required | Description |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | Yes | Backend API URL (`http://localhost:8000` dev) |
| `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY` | Yes | Maps JS (referrer-restricted to tamilschool.org in prod) |
| `NEXT_PUBLIC_GOOGLE_MAPS_MAP_ID` | Yes | Map ID for AdvancedMarker styling |
| `AUTH_SECRET` | Yes (prod) | NextAuth.js v5 secret |
| `AUTH_GOOGLE_ID` / `AUTH_GOOGLE_SECRET` | Yes (prod) | Google OAuth credentials |
| `REVALIDATE_TOKEN` | Yes (prod) | Server-side only (never `NEXT_PUBLIC_*`); matches the api service's `REVALIDATE_TOKEN` |

NEXT_PUBLIC_* values are baked into the JS bundle at `npm run build` — runtime env var changes have NO effect on them. To change a `NEXT_PUBLIC_*` value, rebuild the container image.

## Data sources

- **MOE School List**: `data/SenaraiSekolahWeb_April2026.xlsx` — 528 SJK(T) schools (refreshed Apr 2026)
- **Political Constituencies**: `data/Political Constituencies.csv` — 222 Parliament + 613 DUN
- **GPS Verification**: `data/school_pin_verification.csv` — Google Places-verified GPS pins
- **Hansard PDFs**: `parlimen.gov.my` (15th Parliament Dec 2022 – present)
- **News**: Google Alerts RSS feeds (configured in `newswatch/`)
- **MP profiles**: `parlimen.gov.my` + `mymp.org.my` (scraped via `import_mp_profiles`)

## Public REST API (read-only, paginated)

All endpoints under `/api/v1/`. Highlights:

- `GET /api/v1/schools/` — list with filters `?state=`, `?ppd=`, `?constituency=`, `?skm=true`, `?min_enrolment=`, `?max_enrolment=`
- `GET /api/v1/schools/map/` — minimal fields for map (528 schools, ~50 KB non-paginated)
- `GET /api/v1/schools/<moe_code>/` — full detail with leaders, photos, MP
- `GET /api/v1/schools/<moe_code>/mentions/` — approved parliament mentions
- `GET /api/v1/schools/<moe_code>/news/` — approved news mentions
- `GET /api/v1/constituencies/` and `/duns/` — listings with `school_count`
- `GET /api/v1/schools/<moe_code>/duitnow-qr/` — DuitNow QR PNG for donations
- `GET /api/v1/search/?q=<query>` — schools + constituencies + MPs (min 2 chars)
- `GET /api/v1/national-stats/` — aggregate counts for homepage

GeoJSON: `/api/v1/constituencies/geojson/`, `/api/v1/duns/geojson/` (FeatureCollection, supports `?state=`, `?constituency=` filters).

## Project documentation

| Doc | Purpose |
|---|---|
| `CLAUDE.md` | Project instructions for AI agents — architecture, commands, env vars, sprint history |
| `docs/release-notes-v2.0.1.md` | Current release narrative (v2.0 series complete) |
| `docs/decisions.md` | Architectural decision log |
| `docs/lessons.md` | Cross-cutting lessons from all prior sprints |
| `docs/tech-debt.md` | Tech debt register (TD-01 through TD-25) |
| `docs/tech-debt-audit-2026-06-26.md` | Most recent full audit |
| `docs/consolidation-log.md` | Small-change-lane pending queue |
| `docs/retrospective-sprint*.md` | Per-sprint retrospectives |
| `docs/roadmap.md` | High-level direction (post-v2.0) |
| `docs/sla.md` | Production operational SLA |
| `CHANGELOG.md` | Per-sprint + per-release line items |
| `CONTRIBUTING.md` | Contributor guide |
| `PRD-SJKTConnect.md` | Product requirements (v0.2) |

## Operating model

Sprint-driven via the workspace WAT framework (Workflows, Agents, Tools). Substantial features run via `Settings/_workflows/sprint-start.md` → coding → `sprint-close.md`. One-line fixes that touch a live system run via `small-change-lane.md` (which feeds a periodic consolidation review). Releases tagged via `release.md`. Project-complete deliverables (LICENSE, SLA, roadmap) per `project-complete.md`.

Post-v2.0.1 the project is in maintenance mode; new work runs via small-change-lane unless it crosses the sprint threshold (≥6 files, new model/feature/page, money/consent/auth/PII).

## License

See `LICENSE`.

## Contributing

See `CONTRIBUTING.md`.

## Contact

- Maintainer: tamiliam@gmail.com / admin@tamilfoundation.org
- Issues: https://github.com/tamilfoundation/sjktconnect/issues
- Feedback form on the live site at [tamilschool.org/contact](https://tamilschool.org/contact) (rate-limited 3/hour per IP)
