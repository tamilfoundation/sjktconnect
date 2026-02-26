# Changelog

## Sprint 0.6 — Deployment + Cloud Scheduler + Documentation (2026-02-26)

### Added
- `hansard/pipeline/scraper.py` — Discovers new Hansard PDFs via HEAD requests to parlimen.gov.my, probing date ranges for `DR-DDMMYYYY.pdf` URLs
- `check_new_hansards` management command — compares discovered PDFs against processed sittings in DB; supports `--days`, `--start`/`--end`, `--auto-process` (chains into `process_hansard`)
- Health check endpoint at `/health/` — returns `{"status": "ok"}` for Cloud Run liveness probes
- Cloud Run service `sjktconnect-api` deployed to asia-southeast1
- Cloud Run job `sjktconnect-check-hansards` — runs `check_new_hansards --auto-process --days 7`
- Cloud Scheduler `sjktconnect-daily-check` — triggers job daily at 8:00 AM MYT
- 22 new tests: test_scraper (11), test_check_new_hansards (10), test_health_check (1)

### Changed
- Database switched from planned Neon PostgreSQL to Supabase PostgreSQL (Tamil Foundation org, Singapore region, free tier)
- Production settings and docs updated from "Neon" to "Supabase"

### Infrastructure
- **Service URL**: https://sjktconnect-api-90344691621.asia-southeast1.run.app
- **Database**: Supabase PostgreSQL (transaction pooler, port 6543)
- **Reference data imported**: 222 constituencies, 613 DUNs, 528 schools, 2,106 aliases
- **Admin user**: admin@tamilfoundation.org

### Test totals
- 220 tests passing (198 from Sprint 0.5 + 22 new)

---

## Sprint 0.5 — Admin Review Queue + Content Publishing (2026-02-25)

### Added
- `MentionReviewForm` — ModelForm for editing AI analysis fields (mp_name, constituency, party, mention_type, significance, sentiment, change_indicator, ai_summary, review_notes)
- 8 Django views in `parliament/views.py`:
  - Admin (login required): ReviewQueueView, SittingReviewView, MentionDetailView, ApproveMentionView, RejectMentionView, PublishBriefView
  - Public: ParliamentWatchView, BriefDetailView
- 8 URL patterns in `parliament/urls.py` with `app_name = "parliament"`
- Root URL wiring: Django built-in LoginView/LogoutView at `/accounts/login/` and `/accounts/logout/`
- `highlight_keywords` template filter — wraps SJK(T) variants (6 regex patterns) in `<mark>` tags
- 7 templates: base.html (navbar + footer), queue, sitting_review, detail (split-screen), watch, brief, login
- `static/css/style.css` — full stylesheet with CSS variables, responsive split-screen grid, mention cards with status-coloured borders, keyword highlight styling
- 49 new tests: test_views (33), test_highlight (12), test_forms (4)

### Fixed
- Approve/reject redirect bug — was pointing to `mention-detail` with sitting ID (wrong lookup), fixed to redirect to `sitting-review`
- Empty significance field crash — IntegerField received `''` from blank ChoiceField. Fixed with `TypedChoiceField(coerce=int, empty_value=None)`

### Design decisions
- Split-screen review: left panel shows verbatim quote with keyword highlights + context; right panel shows editable AI analysis form
- Approve saves form edits + sets status in one POST; reject only saves review_notes + status
- PublishBriefView delegates to `generate_brief()` then sets `is_published=True`
- Public views have no auth requirement; admin views use `LoginRequiredMixin`
- ChoiceFields include blank option `("", "---")` so reviewers can clear AI-set values

### Test totals
- 198 tests passing (149 from Sprint 0.4 + 49 new)

---

## Sprint 0.4 — Gemini AI Analysis + MP Scorecard (2026-02-25)

### Added
- `parliament` app with `MPScorecard` and `SittingBrief` models
- Service modules in `parliament/services/`:
  - `gemini_client.py` — Gemini Flash API wrapper using `google.genai` SDK, structured JSON output, token budgeting (~1500 chars per call), response validation with enum clamping
  - `scorecard.py` — aggregates all analysed mentions per MP: total, substantive (significance >= 3), questions, commitments. Caches school count and enrolment from constituency. Idempotent recalculation with stale scorecard cleanup.
  - `brief_generator.py` — generates markdown sitting brief, renders to HTML, creates social post (<= 280 chars). Falls back to all analysed mentions if none approved yet.
- `analyse_mentions` management command — processes unanalysed mentions via Gemini, with `--dry-run`, `--limit`, `--sitting-date` options
- `update_scorecards` management command — full recalculation of all MP scorecards
- Admin registration for MPScorecard and SittingBrief
- 38 new tests: gemini_client (12), scorecard (13), brief_generator (13) — all Gemini calls mocked
- `google-genai` and `markdown` added to requirements.txt

### Design decisions
- Used `google.genai` SDK (not deprecated `google.generativeai`) — client pattern instead of global configuration
- Response validation: enum fields clamped to valid values, significance clamped 1-5, missing fields get sensible defaults
- Cross-platform date formatting helper (Windows lacks `%-d` strftime flag)
- Scorecard `update_or_create` pattern: full recalculation each run, stale records deleted
- Brief generator prefers APPROVED mentions but falls back to all analysed for early-stage use (before Sprint 0.5 review queue)

### Test totals
- 149 tests passing (111 from Sprint 0.3 + 38 new)

---

## Sprint 0.3 — School Name Matching (2026-02-25)

### Improved (code simplification pass)
- Hoisted `_BOUNDARY_WORDS` set and prefix regex to module-level constants in `matcher.py` (were recreated per call)
- Cached `_get_tracked_models()` in `signals.py` — was resolving on every Django signal
- Changed tracked models from `list` to `set` for O(1) membership checks
- Consolidated duplicate regex patterns for `s.j.k.(t)` / `s.j.k(t)` in `normalizer.py`
- Removed unused imports (`STOP_WORDS`, `re`) and unused variables (`all_alias_keys`, `quote`)
- Fixed f-string logging to use `%s` lazy formatting in `signals.py`

### Added
- `SchoolAlias` model — stores multiple name variants per school (official, short, common, SJKT, Hansard-discovered)
- `MentionedSchool` bridge model — links HansardMention to School with confidence score and match method
- `seed_aliases` management command — auto-generates ~4 aliases per school from official/short names
- Pipeline modules in `hansard/pipeline/`:
  - `matcher.py` — two-pass matching: exact alias lookup (100% confidence) then trigram similarity with difflib fallback
  - `stop_words.py` — 20 high-frequency words excluded from fuzzy matching (school prefixes + location words)
- pg_trgm extension migration (conditional — skips on SQLite, applies on PostgreSQL)
- Matcher integrated into `process_hansard` pipeline (Step 7, with `--skip-matching` flag)
- Admin registration for SchoolAlias and MentionedSchool
- 41 new tests: matcher (19), seed_aliases (11), stop_words (7), models (4)

### Design decisions
- Candidate extractor uses Malay boundary words (dan, di, yang, untuk, etc.) to stop capturing after the school name
- Progressive shortening: candidates trimmed word-by-word from right for exact match boundary detection
- Confidence < 80% auto-flagged as needs_review for human verification
- HANSARD alias type preserved during `--clear` re-seeding

### Test totals
- 111 tests passing (70 from Sprint 0.2 + 41 new)

---

## Sprint 0.2 — Hansard Download + Text Extraction + Keyword Search (2026-02-25)

### Added
- `hansard` app with HansardSitting and HansardMention models
- Pipeline modules in `hansard/pipeline/`:
  - `downloader.py` — HTTP download with retries, Content-Disposition support, parlimen.gov.my SSL workaround
  - `extractor.py` — pdfplumber text extraction (page by page)
  - `normalizer.py` — text normalisation: Unicode NFKC, lowercase, whitespace collapse, SJK(T) variant canonicalisation
  - `searcher.py` — keyword search with ±500 chars context extraction and verbatim quote mapping
  - `keywords.py` — primary (12) and secondary (7) keyword lists, DB school name loader
- `process_hansard <url>` management command with `--sitting-date`, `--catalogue-variants`, `--dest-dir` options
- Date extraction from Hansard filename pattern (DR-DDMMYYYY.pdf)
- Admin registration for HansardSitting and HansardMention
- 44 new tests: normaliser (13), searcher (12), downloader (10), pipeline integration (6), models (3)
- pdfplumber and requests added to requirements.txt

### Tested against real data
- 3 real Hansard PDFs processed (26 Jan, 28 Jan, 23 Feb 2026)
- 5 mentions found across 2 sittings (1 sitting had zero mentions — expected)
- Variant catalogue: "sjk(t)" (3 occurrences), "sekolah jenis kebangsaan tamil" (2 occurrences)
- Normaliser correctly handles: SJK(T), SJKT, S.J.K.(T), S.J.K(T), non-breaking spaces

### Test totals
- 70 tests passing (26 from Sprint 0.1 + 44 new)

---

## Sprint 0.1 — Project Scaffold + Reference Data Import (2026-02-25)

### Added
- Django project scaffold with split settings (base/development/production)
- `core` app: AuditLog model with post_save/post_delete signals and request middleware
- `schools` app: Constituency, DUN, School models
- `import_constituencies` management command — imports 222 constituencies and 613 DUNs from Political Constituencies CSV
- `import_schools` management command — imports 528 SJK(T) schools from MOE Excel, with GPS verification CSV override
- 26 tests across 3 test files (models, import_constituencies, import_schools)
- Project infrastructure: requirements.txt, Dockerfile, pytest.ini, .env.example, .gitignore, .dockerignore

### Fixed
- DUN model: changed from `code` as primary key to auto-generated PK with `unique_together = (code, constituency)` — DUN codes like "N01" repeat across all 13 states
- CSV encoding: Political Constituencies CSV uses cp1252, not UTF-8
- MOE Excel format: PARLIMEN/DUN columns contain names only (no codes), added name-based lookup fallback

### Data verification
- 222 constituencies, 613 DUNs, 528 schools imported
- 528/528 schools linked to constituency (100%)
- 513/528 schools linked to DUN (97% — 15 KL schools have no DUN, correct)
- 476/528 GPS coordinates verified from verification CSV
