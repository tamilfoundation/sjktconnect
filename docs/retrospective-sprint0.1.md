# Sprint 0.1 Retrospective — Project Scaffold + Reference Data Import

**Date**: 2026-02-25
**Sprint goal**: Django project running locally with 528 schools and constituency data imported.

## What Was Built

- Django project scaffold with split settings (base/development/production)
- `core` app: AuditLog model with post_save/post_delete signals and request middleware
- `schools` app: Constituency, DUN, School models
- `import_constituencies` management command (Political Constituencies CSV)
- `import_schools` management command (MOE Excel + GPS verification CSV)
- 26 tests across 3 test files
- Project infrastructure: requirements.txt, Dockerfile, pytest.ini, .gitignore, .env.example

## What Went Well

- Split settings pattern from MySkills/HalaTuju transferred cleanly
- All 528 schools imported with 100% constituency linking on first successful run
- GPS verification CSV override worked perfectly (476/528 verified)
- Tests caught issues early (rounding in parse_indian_percentage)

## What Went Wrong

1. **DUN codes are not nationally unique** — designed DUN with `code` as primary_key, only discovered during real data import that "N01" exists in all 13 states. Had to change to auto PK with `unique_together`. Cost: recreate migrations and re-import.

2. **CSV encoding assumption** — assumed UTF-8 for Political Constituencies CSV, but it uses cp1252 (non-breaking spaces in party names like "BN\xa0(UMNO)"). Only caught at import time.

3. **MOE Excel column format assumption** — plan assumed PARLIMEN/DUN columns use "P140 SEGAMAT" format (code + name). Real data has just names (" SRI GADING") with leading spaces. Had to add name-based case-insensitive lookup.

4. **MOE JENIS/LABEL value** — expected "SJK(T)" but actual value is "SJKT" (no parentheses). Filter handles both but was initially confusing.

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| DUN auto PK + unique_together(code, constituency) | DUN codes repeat across states; composite uniqueness is correct |
| Name-based constituency lookup with code fallback | MOE Excel doesn't include constituency codes, only names |
| cp1252 encoding for Political Constituencies CSV | File contains Windows-1252 non-breaking spaces |
| SQLite locally, Neon PostgreSQL for production | Free tier sufficient; no need to set up Neon until deployment |
| 15 KL schools with no DUN link | Correct — WP Kuala Lumpur has no state assembly |

## Numbers

| Metric | Value |
|--------|-------|
| Files committed | 41 |
| Lines of code | 2,764 |
| Tests | 26 |
| Constituencies | 222 |
| DUNs | 613 |
| Schools | 528 |
| Schools with constituency link | 528 (100%) |
| Schools with DUN link | 513 (97%) |
| GPS verified | 476 (90%) |
