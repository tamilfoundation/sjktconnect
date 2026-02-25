# SJK(T) Connect — Project CLAUDE.md

## Architecture

- **Backend**: Django 5.x (backend/)
- **Database**: Neon PostgreSQL (free tier, auto-suspends after 5 min idle)
- **AI**: Gemini Flash API (Hansard analysis, Sprint 0.4+)
- **Hosting**: Google Cloud Run (GCP project: `gen-lang-client-0871147736`)
- **Domain**: tamilschool.org.my

## Project Status

- **Current Phase**: Phase 0 — Parliament Watch
- **Current Sprint**: 0.2 DONE. Next: 0.3
- **Tests**: 70 passing

## Apps

| App | Purpose | Sprint |
|-----|---------|--------|
| `core` | AuditLog, middleware | 0.1 |
| `schools` | School, Constituency, DUN models + import commands | 0.1 |
| `hansard` | Hansard pipeline (download, extract, search, match) | 0.2-0.3 |
| `parliament` | MP Scorecard, review UI, content publishing | 0.4-0.5 |

## Commands

```bash
# Development
cd backend
python manage.py runserver                    # Start dev server
pytest                                        # Run tests (70 passing)

# Data Import
python manage.py import_constituencies        # Load constituencies from CSV
python manage.py import_schools ../SenaraiSekolahWeb_Januari2026.xlsx

# Hansard Pipeline
python manage.py process_hansard <url>                        # Full pipeline
python manage.py process_hansard <url> --sitting-date YYYY-MM-DD
python manage.py process_hansard <url> --catalogue-variants   # Print variant catalogue

# Deployment (verify account first!)
gcloud config set account tamiliam@gmail.com
gcloud config set project gen-lang-client-0871147736
gcloud run deploy sjktconnect-api --source . --region asia-southeast1 --allow-unauthenticated
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes (prod) | Neon PostgreSQL connection string |
| `SECRET_KEY` | Yes (prod) | Django secret key |
| `DJANGO_SETTINGS_MODULE` | Yes | `sjktconnect.settings.development` or `.production` |
| `GEMINI_API_KEY` | Sprint 0.4+ | Google AI Studio API key |
| `ALLOWED_HOSTS` | Prod | Comma-separated hostnames |
| `CSRF_TRUSTED_ORIGINS` | Prod | Comma-separated origins |

## Data Files (not in git — too large)

| File | Rows | Purpose |
|------|------|---------|
| `SenaraiSekolahWeb_Januari2026.xlsx` | 528 SJK(T) | MOE official school list |
| `Political Constituencies.csv` | 613 DUN | Constituency reference data |
| `school_pin_verification.csv` | 528 | GPS verification results |
| `பள்ளிகள் - மாநிலம்.xlsx` | 529 | TF school database |

## Database Notes

- Neon free tier: 0.5 GB storage, 190 compute hours/month
- Auto-suspends after 5 min idle, wakes in ~1s
- Supports pg_trgm (needed for Sprint 0.3 fuzzy matching)
- Django connects via `DATABASE_URL` same as Supabase

## Sprint History

| Sprint | Status | Summary |
|--------|--------|---------|
| 0.1 | Done | Scaffold + 528 schools + 222 constituencies + 613 DUNs imported. 26 tests. |
| 0.2 | Done | Hansard pipeline: download, extract, normalise, keyword search. 44 new tests (70 total). Tested on 3 real PDFs — 5 mentions found. |

## Next Sprint

Sprint 0.3 — School Name Matching
- Add SchoolAlias, MentionedSchool models to hansard app
- Enable pg_trgm extension (needs Neon PostgreSQL)
- `seed_aliases` command — auto-generate aliases per school
- `stop_words.py` — high-frequency words to exclude from fuzzy matching
- `matcher.py` — Pass 1: exact match on alias_normalized, Pass 2: trigram similarity
- Integrate matcher into process_hansard pipeline
- DUN model uses auto PK with unique_together(code, constituency) — remember this when creating FKs

## Hansard Pipeline Notes
- parlimen.gov.my has invalid SSL cert — downloader uses verify=False for that domain
- PDF date format: DR-DDMMYYYY.pdf (e.g. DR-26012026.pdf = 26 Jan 2026)
- Real variants found so far: "sjk(t)", "sekolah jenis kebangsaan tamil"
- Not every sitting mentions Tamil schools — the Jan-Mar 2026 session had 2/15 sittings with mentions
- Normaliser handles: SJK(T), SJKT, S.J.K.(T), S.J.K(T), non-breaking spaces, whitespace collapse
