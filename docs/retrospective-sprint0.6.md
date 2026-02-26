# Sprint 0.6 Retrospective — Deployment + Cloud Scheduler

**Date**: 2026-02-26
**Duration**: 1 session
**Sprint goal**: Get SJK(T) Connect live on Cloud Run with automated Hansard discovery

---

## What Was Built

1. **Hansard PDF discovery** — `scraper.py` probes parlimen.gov.my via HEAD requests for `DR-DDMMYYYY.pdf` URLs across a date range. `check_new_hansards` management command compares discoveries against DB and optionally auto-processes.

2. **Cloud Run deployment** — Service deployed with Dockerfile (Python 3.11-slim, gunicorn, WhiteNoise). Health check at `/health/`. Migrations run on startup.

3. **Cloud Run job + Cloud Scheduler** — `sjktconnect-check-hansards` job runs `check_new_hansards --auto-process --days 7`. Scheduled daily at 8:00 AM MYT via `sjktconnect-daily-check`.

4. **Production database** — Supabase PostgreSQL (Tamil Foundation org, Singapore region, transaction pooler port 6543). All reference data imported: 222 constituencies, 613 DUNs, 528 schools, 2,106 aliases.

5. **Health check endpoint** — `/health/` returns `{"status": "ok"}`.

## What Went Well

- **Existing infrastructure paid off** — Dockerfile, production settings, and requirements.txt were already set up from Sprint 0.1. Deployment was config + deploy, not build-from-scratch.
- **Database switch was painless** — Changed from planned Neon to Supabase with zero code changes. `dj-database-url` + `DATABASE_URL` abstraction worked exactly as designed.
- **Tests provided confidence** — 220 tests passing before deploy. No surprises in production.
- **Cloud Scheduler setup was straightforward** once the prerequisite APIs were enabled.

## What Went Wrong

1. **Shell escaping on Windows** — Setting environment variables via PowerShell from bash was a recurring nightmare. `$env:VAR` syntax doesn't survive bash → PowerShell escaping. Had to create a temp Python script (`temp_import.py`) to read `.env` and run management commands. Wasted ~15 minutes on escaping issues.

2. **URL-encoded characters in DATABASE_URL** — Supabase generated a password with `?` and `+` which break URI parsing. Had to manually URL-encode (`%3F`, `%2B`). Easy to miss.

3. **Cloud Scheduler required App Engine app** — Even though we only use Cloud Run, Cloud Scheduler needs an App Engine placeholder in the project. Added ~5 minutes to setup.

4. **RLS not implemented** — Roadmap called for PostgreSQL RLS policies. Dropped because Django handles auth/permissions at the application layer, not the database layer. Supabase RLS would only matter if clients connect directly to the database (they don't — everything goes through Django).

5. **"First 5 reports published" acceptance criteria deferred** — The roadmap's exit criteria for Phase 0 requires publishing 5 Parliament Watch reports. This is a content task, not a code task. Deferred to Sprint 0.7 where we'll process real Hansards.

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| Supabase instead of Neon | Tamil Foundation org had a free slot. Same region as Cloud Run (Singapore). Simpler to manage under one org. |
| Transaction pooler (port 6543) | Cloud Run's serverless model opens/closes connections frequently. Session pooler would waste connections. |
| HEAD requests for PDF discovery | Lightweight — doesn't download the PDF, just checks if it exists. parlimen.gov.my returns 200 for existing PDFs and 404 for missing ones. |
| `--auto-process` flag | Keeps discovery and processing as separate concerns but allows chaining for automation. Manual discovery is useful for debugging. |
| Daily at 8:00 AM MYT | Parliament sessions are during working hours. Running at 8 AM catches any PDFs published the previous evening. 7-day lookback handles delays in PDF publication. |
| ALLOWED_HOSTS locked down after first deploy | First deploy used `*` to get the URL, then immediately updated to the actual hostname. |
| No GEMINI_API_KEY in production yet | AI analysis requires the key but isn't needed for deployment verification. Will add in Sprint 0.7 when processing real data. |

## Numbers

| Metric | Value |
|--------|-------|
| Tests added | 22 (11 scraper, 10 command, 1 health check) |
| Tests total | 220 |
| Files created | 4 (scraper.py, check_new_hansards.py, test_scraper.py, test_check_new_hansards.py) |
| Files modified | 4 (urls.py, production.py, CLAUDE.md, README.md) |
| Deploy attempts | 1 (first deploy succeeded) |
| Cloud Run revisions | 2 (initial + ALLOWED_HOSTS lockdown) |
| Reference data | 222 constituencies + 613 DUNs + 528 schools + 2,106 aliases |
