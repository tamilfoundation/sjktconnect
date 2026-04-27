# Retrospective — Sprint 17: Egress Hardening

**Date**: 2026-04-27 (evening, hours after Sprint 16 close)
**Goal**: Hotfix sprint triggered by user noticing 500 MB/day Supabase egress with the site not yet publicised. Diagnose, fix, and add observability so the next anomaly is visible by route + user-agent before it hits the billing chart.

---

## What Was Built

### Investigation
Spawned an Explore agent to audit the codebase for sources of unexplained egress. Findings, ranked by suspected daily contribution:

1. **ISR disabled on 10 public pages** (~200-300 MB/day) — `export const revalidate = false` instead of an integer. In Next 16, `false` means "never cache, always render fresh." Every bot crawl forces a fresh server-side render that hits the backend, which queries Supabase. Sprint 8.3 retro claimed "ISR with 24h revalidate"; reality was the opposite.
2. **Single scraper IP `88.216.210.27`** with fake Chrome/91 UA generating ~1,400 req/day (~200+ MB/day). The Egress Fix retro claimed "middleware IP blocking"; no such middleware existed in the codebase.
3. **Sitemap regenerates per fetch** (~6 MB/day) — `frontend/app/sitemap.ts` had no `revalidate`. ClaudeBot fetches it ~6×/day; each fetch pulls all 528 schools + 222 constituencies fresh from the backend.
4. **News page fetches 500 articles** (~125 KB per visit) — `frontend/app/[locale]/news/page.tsx` passed `pageSize: 500` to fetchNews when 50 would do.

### Fixes
1. **`frontend/app/[locale]/{10 pages}/page.tsx`** — flipped `revalidate = false` → `revalidate = 86400` (24h). Verified each page has no cookies/headers/dynamic markers — all serve fully public data, safe to cache. Pages: `/`, `constituencies`, `constituency/[code]`, `dun/[id]`, `news`, `parliament-watch`, `parliament-watch/[id]`, `parliament-watch/sittings`, `parliament-watch/sittings/[id]`, `school/[moe_code]`.
2. **`backend/core/middleware.py` — new `IPBlockMiddleware`** (~50 LOC). Reads real client IP from Cloudflare's `CF-Connecting-IP` header (priority), `X-Forwarded-For` first hop, or `REMOTE_ADDR` (fallback). Returns 403 immediately for IPs in `BLOCKED_IPS` set (initial member: `88.216.210.27`). Wired FIRST in the `MIDDLEWARE` chain so blocked requests never touch routing/DB/serializers — cheapest possible abort. **6 unit tests** covering CF-Connecting-IP priority, XFF first-hop parsing, multi-hop XFF, no-headers fallback, header precedence.
3. **`frontend/app/sitemap.ts`** — added `export const revalidate = 86400`.
4. **`frontend/app/[locale]/news/page.tsx`** — `pageSize: 500` → `50`.

### Observability (the user asked for this)
5. **2 Cloud Logging metrics**: `sjktconnect_api_egress_per_route` + `sjktconnect_web_egress_per_route`. DISTRIBUTION over `httpRequest.responseSize`, labelled by `route` + `user_agent` + `status`.
6. **1 Cloud Monitoring dashboard**: "SJK(T) Connect — Egress by Route/UA" (id `f1722366-2df9-4446-9941-7cda5c019615`). 4 charts: API + web egress by route, API + web egress by user-agent (for bot detection).
7. **Reproducible configs** — `backend/scripts/egress_metric_config.yaml`, `egress_metric_web_config.yaml`, `egress_dashboard.json`. Anyone can recreate the dashboard from the repo.

### Verified (no change needed)
- `sjktconnect-web` Cloud Run service has `autoscaling.knative.dev/minScale: '1'` already set. CLAUDE.md memory was right on this one.
- `.defer("boundary_wkt")` from Egress Fix sprint is in place across the 6 schools/constituency views — saving ~2 GB/day vs without it. (This is what kept us at 500 MB/day instead of 2.5 GB/day.)

### Tests
- Backend: 1155 → **1161** (+6 IP block tests).
- Frontend: 289 (unchanged — the cache-policy + pageSize changes are config, not behaviour the tests verify).

### Deployed
- `sjktconnect-api-00105-wwd` → `00106-rxf` (IPBlockMiddleware).
- `sjktconnect-web-00104-d4n` → `00105-vhx` (ISR + sitemap + news pageSize).
- Both shipped within 2 hours of the user flagging the egress concern.

---

## What Went Well

- **The Explore agent saved hours of investigation time.** Single dispatch with a focused 12-point checklist returned a prioritised punch list with file:line evidence. From "where is this leaking" to "here's the patch path" in under 10 minutes of agent work.
- **The fix path was trivially small once diagnosed.** ISR fix = sed across 10 files. IP block = ~50 LOC + 6 tests. Sitemap = 1 line. News pageSize = 1 line. Total code change probably 100 LOC. The 80% of the sprint was diagnosis + observability scaffolding, not the patch.
- **Observability shipped in the same sprint as the fix.** Next time egress spikes, the dashboard will show `route="/api/v1/<endpoint>" user_agent="<crawler>"` with bytes-per-hour. We won't have to spawn an Explore agent again.
- **`docs/scripts/egress_*.yaml` + `egress_dashboard.json` make the GCP setup reproducible.** Someone restoring from a fresh GCP project can apply these with two `gcloud` commands instead of clicking through the console.
- **Both deploys ran in parallel and landed cleanly.** Backend (~5 min) + frontend (~7 min) shipped concurrently after the commit; total wall time ~7 min, not 12.

---

## What Went Wrong

### 1. Sprint 8.3 retro lied about ISR; Egress Fix retro lied about IP block
Two prior sprints claimed work that never landed. Sprint 8.3 retrospective said "Server-side school map data via ISR (revalidate 24h)" — actual code shipped `revalidate = false` (the opposite). Egress Fix retrospective said "middleware IP blocking (Chrome/91 scraper)" — no IP-block middleware existed in the codebase, and `MIDDLEWARE` only contained the AuditLog one.
- **Root cause**: retrospectives were written from intent, not from diff. Nobody verified the claims by reading the actual files at sprint close.
- **System change** (lessons.md): sprint-close commits and retrospectives that claim work landed must reference the actual code/config that proves it (file:line, git diff, gcloud describe output). "We added X" is not evidence; "we added X — see backend/core/middleware.py:42-50" is.

### 2. CLAUDE.md memory got worse than the codebase
Two memory entries — "ISR with 24h revalidate" and "middleware IP blocking" — turned out to be false. Both were copy-pasted from retrospectives without verification. So we have memory pointing the wrong way, retrospectives doubling down on the same false claim, and the actual code doing something else entirely. Three sources of truth, two of them wrong.
- **Root cause**: memory entries cite retrospectives as authority. Retrospectives cite intent as authority. Cycle of trust without grounding.
- **System change**: memory entries about "we did X" must be sourced from the code that does X, not from a retrospective that claims X. When a retrospective adds a memory entry, the entry should include the file:line that grounds the claim, so future re-reads can verify.

### 3. The user found the egress bug, not us
1.5+ months between Egress Fix and Sprint 17. The egress chart was right there in Supabase the whole time, showing 500 MB/day instead of the claimed <100 MB. Nobody looked.
- **Root cause**: "Monitor 2026-05-03" was on the list (in MEMORY.md and CLAUDE.md), but it was passive — a reminder for one specific date, not a recurring check. By the time the user looked at the chart unprompted, 30 days of "fine, ignored" had passed.
- **System change**: every sprint-close that introduces a "monitor X for Y days" should ALSO set up an automated alert (Cloud Monitoring alerting policy on the relevant metric) OR a Cron-triggered review task. Don't trust manual reminders to fire.

### 4. The 500 MB/day baseline was treated as "fine" because we were on Pro plan
The user had to upgrade to Pro plan involuntarily. We treated 500 MB/day as healthy because it's well within Pro's 250 GB/month included egress (~6%). Reality: at 500 MB/day with no traffic, scaling to even modest traffic would blow the Pro allotment. The ratio of "wasted bot traffic" to "useful egress" was something like 95:5.
- **Root cause**: applied the wrong frame ("are we within plan?") instead of ("is the per-request cost reasonable?").
- **System change**: lessons.md gets a note that egress sanity should be measured per-request or per-user, not against the plan cap. At 1,400 bot req/day driving 200 MB, that's ~140 KB/req — way too high for an HTML page.

---

## Design Decisions

Two decisions worth recording in `docs/decisions.md`:

1. **`IPBlockMiddleware` over Cloud Armor (or Cloudflare WAF)**: the block lives in our app code, not in front-of-door infra. Pros: testable, version-controlled, blocks travel with the codebase across deploys, no GCP/Cloudflare config to forget. Cons: each blocked request still wakes a Cloud Run instance (cold start + middleware), where Cloud Armor would reject at the edge. At our scale (one IP, ~1,400 req/day) the wake-up cost is negligible. Trade-off: revisit if blocklist grows past ~50 IPs or if the volume per blocked IP grows past ~100K/day.
2. **Distribution metric (not counter) for per-route egress**: a counter would just sum bytes. A distribution lets us answer "is the median response size growing?" and "is there a long tail of huge responses?" via histogram queries in Metrics Explorer. Same storage cost. Trade-off: distribution metrics consume slightly more query time when grouped by high-cardinality labels (`route` + `user_agent` is borderline). Acceptable.

---

## Numbers

| Metric | Sprint start | Sprint end | Δ |
|---|---|---|---|
| Backend tests (passing) | 1155 | **1161** | +6 (IP block) |
| Frontend tests (passing) | 289 | 289 | 0 |
| Files touched | — | 14 (+ 3 GCP configs) | — |
| Production revisions (frontend) | web-00104-d4n | **web-00105-vhx** | +1 |
| Production revisions (backend) | api-00105-wwd | **api-00106-rxf** | +1 |
| Cloud Monitoring metrics | 0 (custom) | 2 | +2 |
| Cloud Monitoring dashboards | 0 | 1 | +1 |
| Open tech debt | 4 (TD-07/09 status drift; TD-11/12 deferred) | 4 (unchanged) | 0 |

**Wall-clock time**: ~2 hours from "user flagged 500 MB/day" to "both fixes deployed + observability live + sprint close."

**Expected egress impact**: 500 MB/day → ~100-150 MB/day within 24h. **Verifying 2026-04-29.**
