# Sprint 2.6 Retrospective — News AI Analysis + Rapid Response + Review UI

**Date**: 2 March 2026
**Sprint duration**: 1 session (crashed mid-session, completed in next session)

---

## What Was Built

1. **Gemini Flash AI analysis service** (`news_analyser.py`) — analyses extracted news articles for relevance (1-5), sentiment (POSITIVE/NEGATIVE/NEUTRAL/MIXED), AI summary, mentioned school extraction, and urgency flagging
2. **Management command** (`analyse_news_articles`) — processes EXTRACTED articles in configurable batches, warns about urgent articles pending review
3. **Admin review queue** (`/dashboard/news/`) — filterable by review status and urgency, sorted urgent-first then by relevance score
4. **Article detail view** (`/dashboard/news/<pk>/`) — split-screen layout mirroring the Hansard review UI: article body on the left, AI analysis + approve/reject/toggle-urgent actions on the right
5. **NewsArticle model extension** — 9 new fields for AI analysis + review workflow, new migration, ANALYSED status added to lifecycle
6. **39 new backend tests** covering the analyser service, management command, admin views, and model fields

---

## What Went Well

- **Pattern reuse**: The news analyser closely follows the existing `parliament/services/gemini_client.py` pattern — structured JSON response, validation with enum clamping, token budgeting. This made development fast and predictable.
- **Review UI reuse**: The split-screen layout and approve/reject workflow mirror the Hansard review queue from Sprint 0.5. Consistent admin experience.
- **Clean lifecycle extension**: Adding ANALYSED status and review fields to the existing NewsArticle model was straightforward — no new models needed, just a migration.
- **Test coverage**: 39 new tests (all mocked Gemini calls) — good coverage of the analyser service, command, and all 5 views.

---

## What Went Wrong

- **Session crash**: The previous session crashed mid-sprint, leaving uncommitted work. All code was intact on disk but nothing was committed. This is the second time this has happened — sprint close is the safety net.
- **No issues otherwise**: This was a clean, well-scoped sprint that followed established patterns.

---

## Design Decisions

1. **Token budgeting**: Send article title + first 3000 chars of body text (not the full article). Follows the same principle as Hansard analysis — deterministic extraction is free, AI only classifies.
2. **Urgency criteria**: Defined five specific criteria (school closure, safety crisis, student/teacher safety, funding cut, political controversy) rather than letting the AI decide freely. This makes urgency flagging auditable.
3. **Review workflow**: PENDING → APPROVED/REJECTED with reviewer tracking (who + when). Matches the Hansard mention review pattern.
4. **Toggle urgent**: Separate from approve/reject — reviewers can flag/unflag urgency independently of approval status.
5. **Django template views** (not DRF API): Admin review UI is Django templates with LoginRequiredMixin, consistent with the Hansard review queue and verification dashboard.

---

## Numbers

| Metric | Value |
|--------|-------|
| New files | 7 (service, command, migration, 2 test files, URLs, 2 templates) |
| Modified files | 7 (models, admin, views, base template, URLs, 2 test files) |
| New backend tests | 39 |
| Total tests | 758 (591 backend + 167 frontend) |
| Lines added | ~500 |
