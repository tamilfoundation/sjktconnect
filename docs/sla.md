# SJK(T) Connect — Operational SLA

**Effective**: v2.0.1 (2026-06-26) — production maintenance mode.

This is a **best-effort SLA** for a single-developer nonprofit project, not a commercial guarantee. It captures the operating posture the project is run with and what users + school admins can reasonably expect.

---

## Service availability

**Target**: 99.0% monthly availability of `tamilschool.org` (public site) and `api.tamilschool.org` (read API).

**Floor**: 95.0% — below this for two consecutive months triggers a "stability sprint" to root-cause + harden.

**Excludes**:
- Scheduled maintenance windows (announced ≥48h ahead at `tamilschool.org`)
- Upstream provider outages (Google Cloud, Supabase, Cloudflare, Brevo) where SJK(T) Connect has no remediation path
- Force majeure (DDoS, malware, supply-chain attacks, hosting-provider account suspension)

**Measurement**: Cloud Monitoring uptime check on `/health/` every 5 min. Monthly availability = (successful checks / total checks) × 100.

---

## Response time targets (Cloud Run + Supabase)

| Endpoint class | p50 | p95 | p99 |
|---|---|---|---|
| Static asset (`/_next/*`, public images via Cloudflare) | 50 ms | 200 ms | 500 ms |
| Cached server-rendered page (ISR hit, `Cache-Control: HIT`) | 100 ms | 400 ms | 1s |
| ISR miss / fresh render (school detail, constituency, DUN) | 600 ms | 1.5s | 3s |
| REST API read (`/api/v1/schools/`, `/api/v1/schools/<moe>/`) | 200 ms | 800 ms | 2s |
| REST API write (`PUT /api/v1/schools/<moe>/edit/`) | 500 ms | 1.5s | 3s |
| Search (`/api/v1/search/?q=...`) | 300 ms | 1s | 2.5s |

p99 outliers are acceptable as long as they're not part of a sustained pattern (>10/hour for >1h triggers investigation).

Cold-start: Cloud Run web service is pinned at `minScale=1` (Sprint 17, post-egress hardening), so cold-start should be invisible to users in steady state.

---

## Incident response

**Severity classification**:

| Sev | Definition | Initial response | Resolution target |
|---|---|---|---|
| **SEV1** | Site completely down OR data loss / security breach | Within 4 hours of detection | Within 24 hours |
| **SEV2** | Major feature broken (broadcasts not sending, edit form unusable, search returning errors, OAuth sign-in broken) | Within 24 hours | Within 3 business days |
| **SEV3** | Minor feature degraded (one school's images failing, sidebar widget glitchy, stale data on edge cases) | Within 3 business days | Within 2 weeks |
| **SEV4** | Cosmetic / UX (typo, layout glitch on uncommon viewport, copy improvement) | Best-effort via small-change-lane | When next sprint runs |

**Detection sources** (rough priority order):
1. Cloud Monitoring alerts (uptime check, error-rate spike, egress climb, job-failure alert id `7654330557139407611`)
2. Owner manual spot-checks
3. Email to `info@tamilfoundation.org` or contact form on `tamilschool.org/contact`
4. School admin reporting via the broadcast / community channels

**Escalation contact**:
- Primary: tamiliam@gmail.com / admin@tamilfoundation.org
- Cloud Monitoring email channel: id `5279094837891825431` → admin@tamilfoundation.org

There is no on-call rotation. Single developer; response best-effort.

---

## Backup + recovery

| Asset | Backup method | RPO | RTO |
|---|---|---|---|
| Code | git remote at `github.com/tamilfoundation/sjktconnect` + per-developer clones | Per-commit | <30 min (fresh clone) |
| Database (Supabase) | Supabase Pro daily backups (7-day retention) | 24 hours | 1 hour (point-in-time restore) |
| Object storage (Supabase Storage `school-images` bucket) | Supabase Pro replication | 24 hours | 1 hour |
| Email subscribers (Brevo) | Brevo's own backups + a copy in `Subscriber` table | 24 hours | 1 hour |
| Secrets (`.env`, Cloud Run env vars) | NOT backed up — generated/rotated manually if lost | N/A | Hours (manual recovery from Cloud Run console + Cloudflare dashboard + Toyyib Pay dashboard) |
| Cloudflare ruleset (id `1af056d066e44a5885c933227a413981`) | Cloudflare's own retention + the rule JSON committed to the repo in some form | N/A | <1 hour to reapply via API |

**Disaster recovery rehearsal**: not formally scheduled. The Sprint 30 folder-move incident (2026-06-26) effectively rehearsed code-from-git recovery — total recovery time was ~30s for the clone + manual .env move.

---

## Data classification + handling

| Class | Examples | Handling |
|---|---|---|
| **Public** | School name + GPS + photos, MP scorecards, parliamentary mentions (post-approval), news articles (post-approval), aggregated stats | Cached via Cloudflare + Next.js ISR + Cloud Run; no PII concerns |
| **Internal** | UserProfile records (Google OAuth name+email of MODERATORs + SUPERADMINs + school admins), audit logs, draft broadcasts, pending suggestions | Database-only, SUPERADMIN-gated UI access, no public API exposure |
| **Sensitive** | Subscriber email addresses + unsubscribe tokens, Brevo API key, Gemini API key, Toyyib Pay credentials, Google OAuth client secret, GMAIL refresh token, Cloudflare API token, REVALIDATE_TOKEN | Cloud Run env vars only; never in source code; gitignored `.env` for local dev; rotate at any suspected compromise |
| **Financial** | Donation amounts + Toyyib Pay order IDs + donor name/email (collected at donate time) | Stored in `donations.Donation` table; PII handled per Malaysian PDPA principles; donor data NOT shared with the school (school sees aggregate only) |

**No biometric, health, government-ID, or minor-specific data** is collected.

**Email retention**: subscriber email addresses persist until unsubscribe. Subscribers auto-deactivated after 3 hard bounces (Sprint 8.5).

**Audit log retention**: `core.AuditLog` rows persist indefinitely (small volume — ~1 row per admin edit). No automatic purge.

---

## Privacy + GDPR-like obligations

The site operates in Malaysia. Malaysian PDPA applies. EU GDPR doesn't directly apply (no EU establishment, no EU user targeting). Best-effort GDPR-style controls:

- **Right to access**: subscribers can fetch their preferences via `/preferences/<token>/`. Other data subjects (school admins, donors) can email admin@tamilfoundation.org for export.
- **Right to deletion**: subscribers unsubscribe via `/unsubscribe/<token>/` — Subscriber row + SubscriptionPreference cascade-deleted. Other data subjects can request deletion at admin@tamilfoundation.org; SLA = 30 days.
- **Right to correction**: school admins can edit their school's data via the edit form. Other corrections via email.
- **Cookie policy**: documented at `/cookies/`. Session cookie + NextAuth cookie + Cloudflare analytics. No third-party trackers, no ad tech.
- **Privacy policy**: `/privacy/` (trilingual).

---

## Maintenance windows

- **Backend deploys**: Cloud Run blue/green; zero user-facing downtime. Verify ACTIVE revision via `gcloud run revisions list --service=sjktconnect-api` (don't trust exit-code-0 alone).
- **Database migrations**: applied on container startup. Migrations are reversible (RunPython `reverse_code` defined where data-modifying). Non-zero downtime risk for schema changes is mitigated by Django's atomic migration handling.
- **Scheduled job changes**: `update_jobs.sh` after every backend deploy — MANDATORY (the 2026-05-20 silent-rot incident).
- **Cloudflare ruleset changes**: applied via API, take effect <30s globally.

No fixed maintenance window — change-when-needed.

---

## Egress + cost

- **Supabase**: target <150 MB/day egress (post-Sprint-21 hardening). Pro plan 250 GB/month allowance = ~8 GB/day headroom. Per-route observability at Cloud Monitoring dashboard `f1722366-2df9-4446-9941-7cda5c019615`.
- **Cloud Run**: free-tier-leaning. ~$0-15/month including egress and revisions. Web service `minScale=1` to avoid cold-start penalty.
- **Brevo**: free tier (300 emails/day). Subscriber count ~519 means a full blast drains across 2 days; `resume-sending` job handles the second-day drain.
- **Gemini**: free tier with 1000 RPM, 10K RPD. Hansard analysis + news triage + monthly digest comfortably within this.
- **Toyyib Pay**: per-transaction fee (~2.5%); pass-through to donor amount.
- **Cloudflare**: free tier (zone-scoped API token for redirect automation).

**Budget alarm**: GCP budget alert at RM10/month on the `sjktconnect` project (Sprint 21 setup, email to admin@tamilfoundation.org).

---

## Out-of-scope (this SLA does NOT cover)

- **Tamil Foundation organisation-level service** (separate)
- **External integrations** (Toyyib Pay processing, Brevo deliverability, Google OAuth uptime, Cloudflare CDN, Supabase platform) — each has its own SLA, SJK(T) Connect inherits them
- **Custom on-demand reports** for school admins / journalists / researchers — best-effort, no SLA
- **Real-time push notifications** — not in scope; broadcasts are email-only

---

## Review cadence

This SLA reviewed at every major version bump (next: v2.1 or v3.0). Owner can revise without sprint ceremony.

Last reviewed: 2026-06-26 (v2.0.1).
