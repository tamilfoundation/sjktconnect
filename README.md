# SJK(T) Connect

Intelligence and advocacy platform for Malaysia's 528 Tamil primary schools (SJK(T)).

## What It Does

SJK(T) Connect monitors Malaysian parliamentary proceedings (Hansard) for Tamil school mentions, analyses them with AI, and publishes reports. It operates as three layers:

1. **Intelligence Engine** — AI-powered monitoring of Parliament and news media
2. **Advocacy Platform** — Public school map and directory at tamilschool.org.my
3. **Communications Hub** — Automated broadcasts to schools and stakeholders

## Phase 0: Parliament Watch

The first product. Standalone Hansard intelligence pipeline:

- Downloads Hansard PDFs from parlimen.gov.my
- Extracts text and finds Tamil school mentions
- Links mentions to specific schools using alias + trigram matching
- AI classifies each mention (type, significance, sentiment)
- Admin reviews and approves before publishing
- Published at `/parliament-watch/`

## Tech Stack

- **Backend**: Django 5.x + Django REST Framework
- **Database**: Supabase PostgreSQL (free tier)
- **AI**: Gemini Flash API
- **PDF Processing**: pdfplumber
- **Hosting**: Google Cloud Run
- **Frontend** (Phase 1): Next.js 14

## Local setup

```bash
cd backend
python -m venv venv
venv\Scripts\activate    # Windows
pip install -r requirements.txt
cp .env.example .env     # Edit with your credentials
python manage.py migrate
python manage.py import_constituencies ../Political\ Constituencies.csv
python manage.py import_schools ../SenaraiSekolahWeb_Januari2026.xlsx
python manage.py seed_aliases
python manage.py createsuperuser
python manage.py runserver
```

## Processing Hansards

```bash
# Process a single PDF
python manage.py process_hansard https://www.parlimen.gov.my/files/hindex/pdf/DR-26012026.pdf

# Discover new PDFs (last 14 days)
python manage.py check_new_hansards

# Discover and auto-process
python manage.py check_new_hansards --auto-process

# Custom date range
python manage.py check_new_hansards --start 2026-01-01 --end 2026-03-31

# AI analysis (requires GEMINI_API_KEY)
python manage.py analyse_mentions
python manage.py update_scorecards
```

## Admin review workflow

1. Log in at `/accounts/login/`
2. Review queue at `/review/` — sittings listed with pending/approved counts
3. Click a sitting to see all mentions
4. Split-screen review: Hansard excerpt (left) + editable AI analysis (right)
5. Approve or reject each mention
6. Publish a sitting brief — appears at `/parliament-watch/`

## Deployment (Cloud Run)

```bash
# Verify GCP account
gcloud config set account tamiliam@gmail.com
gcloud config set project gen-lang-client-0871147736

# Deploy from backend/
cd backend
gcloud run deploy sjktconnect-api \
  --source . \
  --region asia-southeast1 \
  --allow-unauthenticated \
  --set-env-vars "DJANGO_SETTINGS_MODULE=sjktconnect.settings.production"
```

Required environment variables (set in Cloud Run console):

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | Supabase PostgreSQL connection string (transaction pooler, port 6543) |
| `SECRET_KEY` | Django secret key (generate with `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`) |
| `DJANGO_SETTINGS_MODULE` | `sjktconnect.settings.production` |
| `GEMINI_API_KEY` | Google AI Studio API key |
| `ALLOWED_HOSTS` | Comma-separated hostnames |
| `CSRF_TRUSTED_ORIGINS` | Comma-separated origins (include `https://`) |

## Running tests

```bash
cd backend
pytest -q       # 220+ tests
```

## Project structure

```
SJKTConnect/
  backend/                  # Django application
    sjktconnect/            # Project settings (base/dev/prod)
    core/                   # AuditLog model + middleware
    schools/                # School, Constituency, DUN models
    hansard/                # Hansard pipeline (download, extract, search, match, discover)
    parliament/             # AI analysis, scorecards, review UI, content publishing
    templates/              # Django templates (base, review, public)
    static/                 # CSS stylesheet
  docs/                     # Roadmap, retrospectives, lessons
  PRD-SJKTConnect.md        # Product requirements
```

## Data sources

- **MOE School List**: `SenaraiSekolahWeb_Januari2026.xlsx` (528 SJK(T) schools)
- **Political Constituencies**: `Political Constituencies.csv` (222 Parliament, 613 DUN)
- **GPS Verification**: `school_pin_verification.csv` (476 confirmed, 25 offset, 28 missing)

## Links

- Domain: [tamilschool.org.my](https://tamilschool.org.my)
- PRD: See `PRD-SJKTConnect.md`
- Roadmap: See `docs/implementation-roadmap.md`
