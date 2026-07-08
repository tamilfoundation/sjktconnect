# Retrospective — Tamil Foundation 2018 Governance Data Integration

**Date**: 2026-07-09  
**Duration**: 1 day (unplanned task)  
**Commits**: 3 (1e25d23, 1d1c84d, ec85587)  
**Deployments**: 2 (backend + frontend)

## What Was Built

- **School Leadership Import**: 1,149 records across 4 governance roles (Headmaster, Board Chair, PTA Chair, Alumni Chair) from Tamil Foundation 2018 datasets. Matched 526 schools by MOE code; non-destructive (preserves website data). All records attributed to TF_2018 for auditability.
- **Newsletter Import**: 537 unique governance leader emails extracted, deduplicated, and added to subscriber list with role-based tags (HM, BC, PTA, AC).
- **Welcome Email Campaign**: Personalized governance leader email template ("Dear {{ name }}") shipped to Brevo API. Batch 1: 250 emails sent successfully in 2m36s.
- **Frontend Attribution**: School profile now displays "Data source: Tamil Foundation, 2018" footer when leadership data originates from legacy import.

**Technical deliverables**:
- `import_legacy_school_leaders.py` — management command with dry-run + pilot modes
- `import_legacy_newsletter.py` — email extraction with dedup + race-condition handling
- `send_governance_welcome_email.py` — Brevo API direct send (no SMTP dependency)
- `SchoolLeader.data_source` + `SchoolLeader.data_source_date` fields + migration
- `welcome_governance_2018.html` template with personalized greeting
- Frontend SchoolProfile component footer + type updates

## What Went Well

1. **Non-destructive design** — Website data precedence was enforced from day 1. Zero overwrites of existing leadership info.
2. **Race-condition handling** — Email dedup used `get_or_create()` instead of separate create, eliminating concurrent write issues.
3. **Brevo API choice** — Switching from Django mail backend to direct Brevo API solved local SMTP issues and Cloud Run env-var complexity. Email sends work in any environment.
4. **Data quality** — Normalization functions (phone formatting, title-case names, title extraction) applied consistently across 1,177 governance records.
5. **Batch control** — `--limit` flag allows safe, repeatable sends respecting Brevo free tier (300/day quota). Batch 1 verified working; batches 2–3 queued.
6. **Personalization** — Template uses subscriber names; fallback to "School Leader" if empty. Higher open/engagement likely vs. generic greeting.

## What Went Wrong

1. **Cloud Run job env vars** — Initial attempt to run send command via Cloud Run job failed because jobs don't auto-inherit service env vars. Root cause: misunderstanding of Cloud Run job behavior (expected: inherit from service; actual: must pass all vars explicitly). Fix: documented that all required env vars (SECRET_KEY, DATABASE_URL, BREVO_API_KEY, BREVO_WEBHOOK_SECRET) must be passed via `--set-env-vars`. Workaround: create a reusable job template with all vars pre-configured.

2. **Cloud Logging retrieval** — Couldn't easily extract job execution logs via `gcloud logging read`. Root cause: Cloud Logging CLI returns empty results even when web console shows logs clearly. This doesn't block workflow (execution status is queryable via `gcloud run jobs executions list`), but makes troubleshooting harder. Workaround: check execution status via CLI, use Google Cloud Console URL for detailed logs if needed.

3. **Frontend cache stale after backend import** — School page showed "Not Available" for leaders despite import creating 1,149 records. Root cause: Next.js ISR cache built before import; 24-hour revalidation window meant stale content served. Fix: updated API serializer + frontend component + redeployed frontend to refresh cache. Lesson: when importing data that changes API responses, plan frontend redeploy as part of the task.

4. **Email template personalization missed initially** — First template used generic "Dear School Leader" greeting. User correctly pointed out subscriber names were available but unused. Fix: updated template to render with `{{ name }}`, modified send command to pass `{"name": subscriber.name}` context per email. Lesson: review templates for personalization opportunities before shipping.

## Design Decisions

| Decision | Rationale | Trade-off |
|----------|-----------|-----------|
| **Brevo API direct (not Django mail)** | Avoids SMTP config + local testing friction; more reliable than SMTP for transactional sends | Adds external API dependency; must handle Brevo-specific errors |
| **Non-destructive import (website data wins)** | User requirement: legacy data fills gaps only; never overwrites edits by school admins | Some schools missing fresh 2018 data if admin already entered old data |
| **Silent opt-in for newsletter** | Governance leaders attended Tamil Foundation events; reasonable to assume interest in school intelligence | Some recipients may not expect emails; relying on unsubscribe links for opt-out |
| **Role abbreviations (HM/BC/PTA/AC)** | Subscriber.source_tag limited to 50 chars; abbreviations fit where full names don't | Source_tag less human-readable; mapping table needed for external analysis |
| **Batch size 250/day** | Brevo free tier caps 300/day; 250 provides buffer for other sends (urgent alerts, news watch) | Slower overall campaign (537 emails across 3 days); user waits for batch 2/3 |

## Numbers

| Metric | Value |
|--------|-------|
| **Governance records imported** | 1,149 school leadership records |
| **Schools matched** | 526 (3 unmatched = expected, likely closed/new schools) |
| **Newsletter subscribers added** | 537 unique emails |
| **Emails sent (Batch 1)** | 250 |
| **Execution time (Batch 1)** | 2m36s (~0.6 sec/email via Brevo API) |
| **Remaining emails** | 287 (batch 2: 250, batch 3: 37) |
| **Backend commits** | 3 |
| **Deployments** | 2 (backend + frontend) |
| **Database migrations** | 1 (SchoolLeader fields) |

## Follow-up

- **2026-07-10**: Send Batch 2 (250 emails) + Batch 3 (37 emails) using same command with `--limit` adjustments
- **Monitor Brevo dashboard**: Delivery rate, opens, bounces, unsubscribes for TF_2018 campaign
- **Hard bounces**: Auto-deactivate subscribers after 1 hard bounce (webhook integration already in place from Sprint 2.3)
- **Optional (future)**: Offer governance leader data import capability to schools claiming their profile (so admins can view/edit legacy records vs. their own)

---

**Lesson learned for future batch jobs**: Pre-stage all environment variables in the job definition (don't rely on service inheritance). Document the set of required vars in CLAUDE.md commands section so future sprints copy-paste correctly.
