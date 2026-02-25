# SJK(T) Connect — Project CLAUDE.md

## Architecture

- **Backend**: Django 5.x (backend/)
- **Database**: Neon PostgreSQL (free tier, auto-suspends after 5 min idle)
- **AI**: Gemini Flash API (Hansard analysis, Sprint 0.4+)
- **Hosting**: Google Cloud Run (GCP project: `gen-lang-client-0871147736`)
- **Domain**: tamilschool.org.my

## Project Status

- **Current Phase**: Phase 0 — Parliament Watch
- **Current Sprint**: 0.1 DONE. Next: 0.2
- **Tests**: 26 passing

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
python manage.py runserver                                    # Start dev server
python manage.py test                                         # Run tests
pytest                                                        # Run tests (pytest)

# Data Import
python manage.py import_constituencies                        # Load constituencies from CSV
python manage.py import_schools ../SenaraiSekolahWeb_Januari2026.xlsx  # Load 528 schools
python manage.py import_schools --dry-run <file>              # Preview without saving

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

## Next Sprint

Sprint 0.2 — Hansard Download + Text Extraction + Keyword Search
- Create `hansard` app with HansardSitting, HansardMention models
- Pipeline: downloader, pdfplumber extractor, text normaliser, keyword searcher
- `process_hansard <url>` management command
- Catalogue real name variants from 2-3 Hansard PDFs
- DUN model uses auto PK with unique_together(code, constituency) — remember this when creating FKs
- MOE PARLIMEN/DUN columns have names only (no codes) — school import uses name-based lookup
