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
- **Database**: Neon PostgreSQL (free tier)
- **AI**: Gemini Flash API
- **PDF Processing**: pdfplumber
- **Hosting**: Google Cloud Run
- **Frontend** (Phase 1): Next.js 14

## Setup

```bash
cd backend
python -m venv venv
venv\Scripts\activate    # Windows
pip install -r requirements.txt
cp .env.example .env     # Edit with your credentials
python manage.py migrate
python manage.py import_constituencies
python manage.py import_schools ../SenaraiSekolahWeb_Januari2026.xlsx
python manage.py runserver
```

## Project Structure

```
SJKTConnect/
  backend/                  # Django application
    sjktconnect/            # Project settings
    core/                   # AuditLog, middleware
    schools/                # School, Constituency, DUN models
    hansard/                # Hansard pipeline (Sprint 0.2+)
    parliament/             # MP Scorecard, review UI (Sprint 0.4+)
  docs/                     # Roadmap, implementation plan
  PRD-SJKTConnect.md        # Product requirements
  PROJECT-IDEA.md           # Original concept
```

## Data Sources

- **MOE School List**: `SenaraiSekolahWeb_Januari2026.xlsx` (528 SJK(T) schools)
- **Political Constituencies**: `Political Constituencies.csv` (222 Parliament, 613 DUN)
- **GPS Verification**: `school_pin_verification.csv` (476 confirmed, 25 offset, 28 missing)

## Links

- Domain: [tamilschool.org.my](https://tamilschool.org.my)
- PRD: See `PRD-SJKTConnect.md`
- Roadmap: See `docs/implementation-roadmap.md`
- Detailed Plan: See `docs/detailed-implementation-plan.md`
