# SJK(T) Connect — Project CLAUDE.md

## Architecture

- **Backend**: Django 5.x (backend/)
- **Database**: Neon PostgreSQL (free tier, auto-suspends after 5 min idle)
- **AI**: Gemini Flash API (Hansard analysis, Sprint 0.4+)
- **Hosting**: Google Cloud Run (GCP project: `gen-lang-client-0871147736`)
- **Domain**: tamilschool.org.my

## Project Status

- **Current Phase**: Phase 0 — Parliament Watch
- **Current Sprint**: 0.3 DONE. Next: 0.4
- **Tests**: 111 passing

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
pytest                                        # Run tests (111 passing)

# Data Import
python manage.py import_constituencies        # Load constituencies from CSV
python manage.py import_schools ../SenaraiSekolahWeb_Januari2026.xlsx

# Hansard Pipeline
python manage.py process_hansard <url>                        # Full pipeline
python manage.py process_hansard <url> --sitting-date YYYY-MM-DD
python manage.py process_hansard <url> --catalogue-variants   # Print variant catalogue
python manage.py process_hansard <url> --skip-matching        # Skip school matching step

# School Name Matching
python manage.py seed_aliases                 # Generate aliases for all 528 schools
python manage.py seed_aliases --clear         # Re-seed (delete non-HANSARD aliases first)

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
| 0.3 | Done | School name matching: SchoolAlias + MentionedSchool models, seed_aliases command, matcher (exact + trigram), stop words. 41 new tests (111 total). |

## Next Sprint

Sprint 0.4 — Gemini AI Analysis + MP Scorecard
- Create `parliament` app with MPScorecard, SittingBrief models
- `gemini_client.py` wrapper for Gemini Flash (structured JSON output)
- `scorecard.py` — aggregate mentions per MP
- `brief_generator.py` — sitting brief in markdown + social post
- `analyse_mentions` and `update_scorecards` commands
- DUN model uses auto PK with unique_together(code, constituency) — remember when creating FKs

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
