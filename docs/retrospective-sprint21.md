# Retrospective — Sprint 21: Egress Hardening Round 2

**Date**: 2026-04-29 (single ~5-hour session, late afternoon → evening)
**Trigger**: User noticed Supabase still showed ~500 MB/day egress 2 days after Sprint 17 supposedly fixed it. Goal: figure out why Sprint 17's claimed ISR fix never engaged, fix it for real, and harden the second-largest leak (AwarioBot).

---

## What Was Built

### Backend
1. **`UserAgentBlockMiddleware`** in `core/middleware.py` — case-insensitive substring match against AwarioBot, AwarioRssBot, AwarioSmartBot, SemrushBot, DataForSeoBot, MJ12bot. Wired second in `MIDDLEWARE` after `IPBlockMiddleware`.
2. **`BLOCKED_USER_AGENT_SUBSTRINGS`** module-level frozen tuple alongside the existing `BLOCKED_IPS` set — same pattern, different signal.
3. **7 new backend tests** in `core/tests/test_user_agent_block.py`: 4 blocked-UA variants (AwarioBot, SemrushBot, DataForSeoBot, case-insensitive), 1 missing-UA, 1 real-browser-passes, 1 Googlebot-passes. All pass.

### Frontend (3 iterative deploys)
4. **`app/[locale]/layout.tsx`** — added `setRequestLocale(locale)` after locale validation; added `generateStaticParams()` returning `routing.locales.map(...)`. Without setRequestLocale, `getMessages()` reads cookies/headers and marks every page as dynamic.
5. **`app/[locale]/dashboard/layout.tsx`** — new file with `export const dynamic = "force-dynamic"`. Opts the entire dashboard segment out of static prerendering in one file (vs editing 4 pages individually). Fixes the `useSearchParams() should be wrapped in a suspense boundary` build error that surfaced once the parent layout went static.
6. **10 public pages** — each got `setRequestLocale(locale)` + `locale` added to params type + import update. Pages: home, constituencies, news, parliament-watch index, parliament-watch sittings index, school/[moe_code], constituency/[code], dun/[id], parliament-watch/[id], parliament-watch/sittings/[id].
7. **5 dynamic-segment pages** — added `export function generateStaticParams() { return []; }`. Empty array opts the route into ISR-on-demand caching with revalidate; without it, Next 15+ treats the route as fully dynamic.
8. **`lib/api.ts` `fetchJSON()`** — now sets `next: { revalidate: 86400 }` on every call. Was the actual root cause of the dynamic-route ISR gap: Next 15+ defaults `fetch()` to uncached, which forced every server-rendered public page into dynamic mode regardless of the page-level revalidate.
9. **`app/robots.ts`** — added 6 new Disallow rules (AwarioBot + 5 other crawlers).

### Cloud
10. **Cloud Logging metrics recreated** — `sjktconnect_api_egress_per_route` + `sjktconnect_web_egress_per_route` deleted and recreated from YAML configs. Kept as DISTRIBUTION (INT64 + valueExtractor combo rejected by GCP — necessary tradeoff).
11. **Cloud Monitoring dashboard rewritten** — all 4 widgets converted to MQL (`fetch ... | align delta(1h) | group_by [metric.X], sum(value) | top 10`). MQL returns scalar `doubleValue` per series, which the chart renders directly.
12. **Source-of-truth files** — `backend/docs/metrics/{api-egress,web-egress,dashboard}.{yaml,json}` now committed so future sprints don't have to re-discover the metric/dashboard config.

### Live verification
- All 10 ISR pages return `Cache-Control: s-maxage=86400, stale-while-revalidate=31449600` + `x-nextjs-cache: HIT` (verified via curl after deploy).
- `curl -H "User-Agent: AwarioBot/1.0" https://api.tamilschool.org/...` → 403.
- All 4 dashboard MQL queries return scalar top-N data via `timeSeries:query`.

---

## What Went Well

- **The post-mortem of Sprint 17 was fast**: I curl-tested `/en` headers before assuming anything, saw `no-cache, no-store`, and traced the cause to `getMessages()` opting pages out of static rendering within ~10 minutes. Sprint 17's retrospective claim "10 pages now ISR-cached" was easy to falsify with one HTTP call.
- **The IPBlockMiddleware pattern was reusable as-is**: the new `UserAgentBlockMiddleware` is 12 lines of behaviour + 7 tests, mirroring the IP-block class structure verbatim. Same wiring slot in `MIDDLEWARE`, same mental model.
- **The 3-iteration deploy progression was systematic, not panicked**: each deploy targeted a specific hypothesis (layout → fetchJSON → generateStaticParams) and the curl verification after each one confirmed or refuted the hypothesis. No guess-and-check.
- **The dashboard MQL conversion was the right escalation**: when GUI-style aggregation produced ambiguous distribution-vs-scalar results in API responses, switching to MQL gave deterministic scalar output that I could verify before pushing.
- **All claims in this retrospective are verifiable from a single deploy revision**: web-00110-vph + api-00112-k7t. Sprint 17's "documented but not verified" pattern is what I'm explicitly avoiding here.

---

## What Went Wrong

### 1. Sprint 17's retrospective claimed work that never engaged
**Symptom**: I started Sprint 21 expecting Sprint 17's ISR fix to be live and just needing tightening. It wasn't live at all — `Cache-Control` on the home page was `no-cache, no-store`, exactly as if Sprint 17 hadn't happened.
**Root cause**: Sprint 17 set `export const revalidate = 86400` on 10 pages and trusted that as proof. Nobody curl-tested the deployed Cache-Control header to confirm. The `revalidate` export is necessary but not sufficient: any uncached fetch, dynamic API call, or (in our case) `next-intl/server.getMessages()` reading cookies/headers cancels it.
**System change**: Sprint-close workflow now requires "verifies via the literal external signal" for ISR claims (curl headers, x-nextjs-cache, etc.) — not just "the export is set." This pattern was already noted in CLAUDE.md after Sprint 17 ("retrospectives that claim work is done aren't proof"); Sprint 21 is the second incident under this pattern. Adding to lessons.md.

### 2. Three deploys to fix one feature
**Symptom**: Web service ran through revisions 00108 → 00109 → 00110 in ~30 minutes.
**Root cause**: I deployed after each fix step (setRequestLocale, fetchJSON cache, generateStaticParams) instead of identifying the full set of needed changes locally first. The first deploy proved setRequestLocale worked for SSG pages but didn't expose the dynamic-route gap; only after that deploy + curl test did I realise dynamic routes also needed work.
**System change**: For caching/ISR work, always test all route classes (SSG-prebuilt, SSG-dynamic-params, ISR-on-demand) in the local build's route table BEFORE the first deploy. The build output `ƒ` vs `●` markers tell the whole story without a deploy. CLAUDE.md was updated during Sprint 17 with "Never deploy more than twice per feature" — Sprint 21 broke it. Adding to lessons.md as a stronger reminder.

### 3. INT64 + valueExtractor metric combo rejected by GCP
**Symptom**: Task #44 was specified as "recreate metrics as INT64". GCP rejected the create call: "A value extractor can only be specified for a DISTRIBUTION value type." 5 minutes wasted on the doomed approach.
**Root cause**: I assumed GCP would accept any valueType + valueExtractor combo. The constraint isn't documented prominently — the only signal is the create-call error.
**System change**: Documented in memory under "GCP DISTRIBUTION metric quirk." Future log-based metrics with byte/numeric extractors must use DISTRIBUTION; dashboards using top-N must use MQL (not GUI aggregation) because secondary aggregation is unreliable at folding distribution → scalar. Source-of-truth YAMLs for both metrics + dashboard now in `backend/docs/metrics/`.

### 4. Premature task closure on Task #45
**Symptom**: I marked Task #45 (deploy + close + 24h egress monitor) as completed before the 24h monitor part was actually checkable (which requires tomorrow's chart).
**Root cause**: Conflated "engineering done" with "task done". The 24h monitor is a calendar-bound check that can't be collapsed into the same session.
**System change**: For any task with a "monitor for N days" component, split into engineering + observation tasks at sprint-plan time, not at sprint-close. The user caught this directly ("have you completed tasks 44 and 45?") — adding a sprint-close checklist item: "for each task, can the success signal be observed today? If not, split it."

---

## Design Decisions

### MQL over GUI-style aggregation for distribution metrics
**Why**: GUI aggregation pipeline (perSeriesAligner: ALIGN_DELTA + crossSeriesReducer: REDUCE_SUM + secondary ALIGN_SUM + pickTimeSeriesFilter) is fragile on DISTRIBUTION metrics — the secondary aggregation doesn't always fold the distribution into a scalar, and pickTimeSeriesFilter then errors with "input cannot be a distribution." MQL's `group_by [metric.X], sum(value) | top N` is explicit and deterministic.
**Trade-off**: MQL queries are harder to edit in the dashboard's GUI builder. Future dashboard tweaks need YAML-style edits or careful UI use.
**Revisit if**: GCP fixes the secondary-aggregation distribution-folding behaviour, or we move to a different observability stack.

### `fetchJSON()` opts into ISR by default
**Why**: Every server-rendered public page expects 24h ISR caching. Forcing every caller to remember `next: { revalidate: 86400 }` is noisy and easy to miss; the helper is the right abstraction layer. Auth endpoints (which need fresh data) bypass `fetchJSON` and use direct `fetch()` with `credentials: "include"`, so the default is safe.
**Trade-off**: A future endpoint that needs uncached data but goes through `fetchJSON` would silently get cached. Mitigated by the auth split being clear at the call site (different code path).
**Revisit if**: We add a public endpoint that needs sub-24h freshness (e.g. live counter), at which point `fetchJSON` should grow an `options` parameter.

### Empty `generateStaticParams()` over pre-building all 528 schools
**Why**: Pre-building 528 × 3 locales = 1584 school pages adds ~5 minutes to build time and forces Cloud Build to reach the API for each one. Empty-array generateStaticParams is one line per page and gives identical runtime caching once each URL is hit once. The only loss is the first-hit latency for each unique URL, which is acceptable for a low-traffic site.
**Trade-off**: First hit on a given URL is uncached (~300ms). With 528 schools × 3 locales × low traffic, most URLs may never be hit, so pre-building would mostly be wasted work.
**Revisit if**: Traffic increases such that first-hit latency becomes user-visible, or if Cloudflare cache hit rate drops because edges aren't seeing repeat traffic on the same URLs.

### Image proxy approach for Supabase Storage hot-link protection (deferred but recommended)
**Why**: Cloudflare can't be put in front of `supabase.co` (not our domain), so Referer checks must happen at our own backend. An image proxy on `api.tamilschool.org/img/<key>` lets us check Referer + emit `Cache-Control: s-maxage=31536000, immutable` so Cloudflare absorbs most repeat hits.
**Alternatives**: (a) make bucket private + signed URLs — short URL TTL breaks ISR caching; (b) Supabase Edge Function — adds dependency on Supabase compute pricing; (c) Cloudflare Workers in front — can't because the bucket isn't on our domain.
**Trade-off**: Egress shifts from Supabase Pro ($0.09/GB) to Cloud Run egress (1 GB/day free, then $0.12/GB). Cloud Run can buffer most via Cloudflare's `s-maxage` cache, so net cost should be lower.
**Revisit if**: Sprint 22 starts and we re-evaluate; or if Supabase introduces native hot-link protection.

---

## Numbers

- **Wall time**: ~5 hours (single session, late afternoon → ~10 PM)
- **Commits on the feat branch**: 5 (`46ddccc`, `345dffc`, `c9d528d`, `45031f4`, then squash-merged as `77a5f84` to main; follow-up `19dd59a` for MQL dashboard)
- **Files changed**: 21 (PR diff stats)
- **Insertions / deletions**: 486 / 26
- **Backend tests**: 1191 → **1198** (+7 in `core/tests/test_user_agent_block.py`)
- **Frontend tests**: 297 (unchanged — frontend changes were all server-side caching config, not new components)
- **Cloud Run revisions**: api 00111 → **00112-k7t**; web 00107 → 00108 → 00109 → **00110-vph**
- **GCP changes**: 2 metrics deleted + recreated; 1 dashboard updated twice (etag conflict on the second push)
- **Live verification calls**: 8 curl commands against tamilschool.org + api.tamilschool.org confirming Cache-Control, x-nextjs-cache, and 403 on AwarioBot UA
- **Tasks**: 5 planned → 4 completed + 1 deferred (Task #43 → Sprint 22)

---

## Key takeaway

> **Curl-test the external signal before claiming a caching fix is done.** Sprint 17's ISR claim was based on the export being set; Sprint 21's first observation was that the export was set AND the response was uncached. The export is necessary but not sufficient. From now on, "ISR fix done" means a curl shows the expected Cache-Control header on the deployed revision.
