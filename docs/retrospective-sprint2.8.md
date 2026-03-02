# Sprint 2.8 Retrospective — News Watch Live + Cloud Scheduler Automation

**Date**: 2026-03-02
**Duration**: 1 session
**Deploys**: 2 (backend + frontend)

---

## What Was Built

- Public news API for school pages (`GET /api/v1/schools/<moe_code>/news/`)
- Real `NewsWatchSection` component — replaces placeholder with actual article display (title, source, date, AI summary, sentiment badge, urgency flag)
- Cloud Scheduler automation: daily news pipeline (fetch → extract → analyse) + monthly intelligence blast (1st of month)
- `run_news_pipeline` management command — chains the three news steps for Cloud Run Jobs
- Photo gallery click-to-swap (pre-sprint work, deployed with this sprint)

## What Went Well

- **Parallel agent execution**: backend and frontend built simultaneously, both worked first try
- **All tests passed immediately** — no debugging needed on either side
- **Existing patterns made it trivial**: `SchoolMentionsView` was the template for `SchoolNewsView`, copy-and-adapt in minutes
- **SQLite compatibility handled cleanly**: vendor-specific branching for JSONField `__contains` (PostgreSQL) vs `LIKE` fallback (SQLite) — tests pass on both

## What Went Wrong

- **gcloud CLI broken due to Python 3.11 removal** — wasted time debugging `gcloud` commands failing with "python not found". Root cause: gcloud hardcodes the Python path at install time, and Python 3.11 had been removed. Fix: set `CLOUDSDK_PYTHON` env var to Python 3.13 path.
- **Auth tokens expired during deploy** — required re-authentication with `gcloud auth login` mid-session
- **NEWS_WATCH_RSS_FEEDS not configured in production settings** — the daily news pipeline won't actually fetch anything until RSS feed URLs are added to the backend Cloud Run environment variables

## Design Decisions

- **News articles are public** (no Magic Link gating) — maximises reach and SEO for school pages
- **Used JSONField `__contains` for school-article linking** — soft link via `mentioned_schools` JSON array, no FK. Acceptable for MVP where the relationship is derived from AI analysis
- **SQLite fallback with LIKE query for dev/test** — production uses PostgreSQL `__contains`. Branching on `connection.vendor` keeps tests fast without requiring PostgreSQL locally
- **No standalone `/news/` listing page** — deferred to Phase 3. News articles only appear on individual school pages for now

## Numbers

| Metric | Value |
|--------|-------|
| Backend tests | 621 (7 new) |
| Frontend tests | 179 (9 new) |
| Total tests | 800 |
| Cloud Run Jobs | 3 (was 1) |
| Cloud Scheduler Jobs | 3 (was 1) |
| Deploys | 2 (backend + frontend) |

## Phase 2 Summary

Sprint 2.8 closes Phase 2 (The Value). Over 8 sprints, we built:
- Subscriber management (subscribe/unsubscribe/preferences)
- Broadcast infrastructure (compose, preview, send via Brevo)
- News Watch pipeline (RSS fetch, article extraction, Gemini AI analysis, admin review)
- Monthly Intelligence Blast (aggregates Parliament Watch + News Watch + MP Scorecards)
- Cloud Scheduler automation for all recurring jobs
- Public news API + frontend component

Phase 3 (The Platform) is next: AI Review Layer, Field Partner role, WhatsApp channels, PIBG Registration Kit.
