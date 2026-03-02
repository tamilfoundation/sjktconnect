# Design: Monthly Intelligence Blast

**Date**: 2 March 2026
**Sprint**: 2.7
**Status**: Approved

---

## Problem

Subscribers have no way to receive a monthly summary of Tamil school-related activity. Parliament mentions and news articles are collected and analysed, but there is no automated digest that delivers highlights to subscribers.

## Solution

A monthly intelligence blast email that aggregates the top Parliament Watch mentions, News Watch articles, and MP scorecard highlights into a single broadcast. The blast is auto-drafted by a management command and reviewed by an admin before sending.

## Approach: Auto-draft + Admin Review

The system generates a draft broadcast automatically from approved data. An admin reviews the draft in the existing broadcast preview UI, then triggers sending through the existing broadcast infrastructure.

**Why this approach:**
- Reuses the existing Broadcast + BroadcastRecipient models and Brevo sender
- Admin gets final say before anything goes out
- No new models needed — just a new service, command, and email template

## Components

### 1. blast_aggregator.py (new service)

Queries the database for a given month and returns:
- **Top 5 approved HansardMentions** — sorted by AI relevance score descending
- **Top 5 approved NewsArticles** — sorted by relevance score descending, review_status=APPROVED
- **Top 3 MPScorecards** — sorted by total_mentions descending (most active MPs)

Returns a dict with three keys: `parliament`, `news`, `scorecards`. Each contains the queryset/list for template rendering.

### 2. monthly_blast.html (new email template)

Three sections:
1. **Parliament Watch** — mention title, date, summary snippet, relevance badge
2. **News Watch** — article title, source, date, AI summary snippet, sentiment badge
3. **MP Scorecard Highlights** — MP name, constituency, total mentions, sentiment breakdown

Plain HTML email (Brevo transactional), styled consistently with existing broadcast emails.

### 3. compose_monthly_blast management command

Flags:
- `--month YYYY-MM` — which month to aggregate (defaults to previous month)
- `--dry-run` — print what would be included without creating a broadcast

Behaviour:
1. Call blast_aggregator for the specified month
2. Render monthly_blast.html with the aggregated data
3. Create a DRAFT Broadcast with subject "Monthly Intelligence Blast — {Month Year}"
4. Set audience to subscribers with MONTHLY_BLAST category preference
5. Print summary: "Draft broadcast created (ID: X) with Y parliament, Z news, W scorecard items"

Admin then reviews via existing `/broadcasts/preview/<id>/` and sends via existing flow.

## What We Reuse

- **Broadcast model** — draft/sent lifecycle, recipient tracking
- **BroadcastRecipient model** — per-subscriber delivery tracking
- **sender.py** — Brevo transactional send, rate limiting
- **SubscriptionPreference** — MONTHLY_BLAST category filtering
- **Broadcast admin views** — preview, send, list

## Testing

~30-35 new tests:
- **blast_aggregator tests** — empty month, partial data, correct ordering, date filtering
- **compose_monthly_blast command tests** — dry-run output, draft creation, month parsing
- **Template rendering tests** — all sections present, empty section handling

## Out of Scope

- Automated scheduling (Cloud Scheduler) — manual command for now
- Subscriber preference UI for MONTHLY_BLAST — can be added later
- Click tracking or analytics — future enhancement
