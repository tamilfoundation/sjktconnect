# Sprint 2.7 Retrospective — Monthly Intelligence Blast

**Date**: 2 March 2026
**Sprint duration**: 1 session (continued from Sprint 2.6 close)

---

## What Was Built

1. **blast_aggregator.py service** — queries top 5 approved HansardMentions (by significance), top 5 approved NewsArticles (by relevance), top 3 MPScorecards (by total_mentions) for a given month
2. **compose_monthly_blast management command** — `--month YYYY-MM` and `--dry-run` flags, creates DRAFT Broadcast with rendered HTML + plain-text fallback, audience filter set to MONTHLY_BLAST
3. **monthly_blast.html email template** — three sections (Parliament Watch, News Watch, MP Scorecard Highlights) with empty-state fallback
4. **23 new backend tests** covering the aggregator service (10 tests) and management command (13 tests)

---

## What Went Well

- **Reuse is the strategy**: No new models needed. The blast creates a standard Broadcast (DRAFT), which feeds into the existing preview/send/track infrastructure from Sprint 2.3. Zero duplication.
- **TDD discipline**: Tests written first for both the aggregator and command, then implementation to pass them. All 23 tests pass.
- **Subagent parallelism**: Tasks 1-2 (aggregator) and Task 3 (template) dispatched in parallel — cut wall-clock time.
- **Clean sprint**: No crashes, no debugging detours, no unexpected issues.

---

## What Went Wrong

- Nothing significant. This was a well-scoped sprint that followed established patterns.

---

## Design Decisions

1. **Scorecards are not month-filtered**: Unlike parliament mentions and news articles, MPScorecards are cumulative aggregates. The blast shows the overall top 3, not month-specific activity. This is intentional — scorecards represent lifetime engagement.
2. **Double query in command**: The command queries once to get counts for dry-run/summary, then re-queries for template rendering. This avoids consuming the queryset slice. Acceptable for a batch command.
3. **Plain-text via strip_tags**: Rather than maintaining a separate text template, the command strips HTML tags for the plain-text fallback. Good enough for email clients that don't render HTML.
4. **Em dash in subject**: Uses the Unicode em dash (—) not hyphens, matching the project's British English style.

---

## Numbers

| Metric | Value |
|--------|-------|
| New files | 4 (service, command, template, test file) |
| Modified files | 3 (CHANGELOG, CLAUDE.md, roadmap) |
| New backend tests | 23 |
| Total tests | 781 (614 backend + 167 frontend) |
| Lines added | ~350 |
