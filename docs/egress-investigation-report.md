# SJKTConnect — Supabase Egress Investigation Report

**Date**: 29 March 2026
**Investigator**: Claude (AI)
**Status**: Investigation complete — no code modified

---

## Phase 0 — Measurement Baseline

### Supabase Egress Dashboard

**Gap**: The SJKTConnect Supabase project is under the Tamil Foundation organisation, which is not connected to the Supabase MCP integration available to this session. I cannot programmatically extract daily egress figures from the Supabase dashboard.

**From the investigation brief** (provided by user, based on dashboard readings):

| Date Range | Daily Egress | Notes |
|------------|-------------|-------|
| ~09 Mar | ~3.6 GB/day | Peak — client-side map fetch (pre-Sprint 8.3) |
| 10–26 Mar | ~0.5–1.0 GB/day | Post Sprint 8.3 (server-side map) |
| 27–29 Mar | ~1.9 GB/day | Crept back up — ISR revalidation + crawler traffic |
| 29 Mar (1 hour) | ~700 MB spike | After removing `revalidate` exports (pages became fully dynamic) |
| 29 Mar (late) | Unknown | `revalidate = false` deployed (rev 00075/00076) |

### Cloud Run Traffic Baseline (from logs)

| Date | Frontend Requests | Backend API Requests | API Response Bytes |
|------|-------------------|---------------------|-------------------|
| 22 Mar | 1,531 | 1,296 | — |
| 23 Mar | 3,989 | 5,882 | — |
| 24 Mar | 6,702 | 3,356 | — |
| 25 Mar | 3,698 | 1,816 | — |
| 26 Mar | 4,622 | 1,694 | — |
| 27 Mar | 4,129 | 2,490 | 15.5 MB |
| 28 Mar | 7,458 | 12,610 | 33.6 MB |

**Critical observation**: The API response data (33.6 MB on the busiest day) is a tiny fraction of the 1.9 GB Supabase egress. The gap (~57x) is explained in the diagnosis below.

---

## Phase 1 — Investigation Findings

### 1. Next.js ISR Caching on Cloud Run — A Fundamental Mismatch

**Finding: `revalidate = false` provides zero egress protection on Cloud Run.**

| Aspect | How Next.js Expects It | How Cloud Run Actually Works |
|--------|----------------------|----------------------------|
| Cache storage | Filesystem (`.next/`) + memory (50 MB) | Ephemeral — destroyed on container shutdown |
| Container lifecycle | Persistent server process | Scale-to-zero after idle (~15 min) |
| Cold start | Serves from disk cache | Starts from Docker image — no runtime cache |
| Multi-instance | Shared cache (Vercel) | Each instance has independent, empty cache |
| `revalidate = false` | "Cache forever, never re-fetch" | "Cache until container dies" (minutes to hours) |

**Evidence** (from official Next.js self-hosting docs):
- "By default, generated cache assets will be stored in memory (defaults to 50mb) and on disk."
- "When running multiple instances, the default file-system cache is per-instance."

**Evidence** (from Cloud Run config):
```
autoscaling.knative.dev/maxScale: '2'
minScale: (not set — defaults to 0, i.e., scale-to-zero)
containerConcurrency: 80
```

The `minScale` is not set, so containers scale to zero after idle. No custom cache handler is configured in `next.config.js`. No Redis or external cache exists.

**What this means**: Every time a Cloud Run container restarts (which happens frequently with scale-to-zero), ALL cached pages are lost. The next request for any page triggers a fresh server-side render, which fetches data from the Django API, which queries Supabase. The `revalidate = false` setting only prevents time-based re-fetching *within a running container's lifetime* — it provides no protection against container restarts.

**Additionally**: During `next build` in the Docker multi-stage build, the backend API is not available (it's a separate service). The build-time cache contains no pre-rendered dynamic pages. So every cold start begins with a completely empty cache.

### 2. Traffic Analysis — Crawlers Are 95% of Your Traffic

**Frontend request breakdown (last 24h sample, 1,000 requests)**:

| User Agent | Requests | % | Type |
|------------|----------|---|------|
| Chrome/91.0 (single IP: 88.216.210.27) | 874 | 87.4% | **Bot** (outdated UA) |
| Chrome/146.0 (real users) | 42 | 4.2% | Human |
| AhrefsBot/7.0 | 31 | 3.1% | SEO crawler |
| OAI-SearchBot/1.3 | 20 | 2.0% | OpenAI crawler |
| Amazonbot/0.1 | 12 | 1.2% | Amazon crawler |
| GPTBot/1.3 | 6 | 0.6% | OpenAI crawler |
| Other | 15 | 1.5% | Mixed |

The Chrome/91 bot systematically crawls every school page (528 × 3 locales), every DUN page, every constituency page, and parliament-watch pages from a single IP. It accounts for ~1,413 requests/day.

**Sitemap fetches (critical finding)**:

| Bot | Sitemap Fetches/Day | Response Size |
|-----|---------------------|--------------|
| ClaudeBot | ~6/day | 1,044 KB each |
| Googlebot | ~2/day | 269 KB each |
| AhrefsBot | ~1/day | 269 KB each |
| Others | ~3/day | 269 KB each |

Each sitemap generation triggers 2 API calls to the backend (schools/map + paginated constituencies), adding to egress. The sitemap itself is 269 KB–1 MB (size varies, possibly due to caching).

**What crawlers do**: Each crawler request hits a Next.js page, which (because the ISR cache is empty after container restart) triggers fresh API calls to the Django backend, which queries Supabase. With ~4,000–7,500 frontend requests/day (95% bots), this is thousands of unnecessary Supabase queries.

### 3. The Real Egress Source — `boundary_wkt` Data Fetched and Discarded

**This is the primary finding of this investigation.**

The Django ORM views fetch full database rows including large `boundary_wkt` polygon data (WKT strings), then the serializers discard this data because they only output compact fields.

#### The Problem Views

| View | ORM Query | Uses `.only()` or `.defer()`? | Fetches `boundary_wkt`? |
|------|-----------|-------------------------------|------------------------|
| `SchoolListView` | `select_related("constituency", "dun")` | **No** | **Yes** — via JOINed constituency AND DUN rows |
| `SchoolDetailView` | `select_related("constituency", "dun")` | **No** | **Yes** — via JOINed constituency AND DUN rows |
| `ConstituencyListView` | `Constituency.objects.annotate(...)` | **No** | **Yes** — full constituency row |
| `ConstituencyDetailView` | `prefetch_related("schools", "scorecards")` | **No** | **Yes** — full constituency row |
| `DUNListView` | `select_related("constituency")` | **No** | **Yes** — full DUN row + JOINed constituency |
| `DUNDetailView` | `select_related("constituency")` | **No** | **Yes** — full DUN row + JOINed constituency |
| `SchoolMapView` | `.only(10 fields)` | **Yes** | **No** — correctly optimised |

Only `SchoolMapView` uses `.only()` to limit fetched fields. Every other view fetches the full row.

#### Measured WKT Sizes

From sampling 10 constituency GeoJSON endpoints (which are derived from the WKT data):

| Metric | Constituencies | DUNs |
|--------|---------------|------|
| Count with boundary | ~155 / 222 | ~430 / 613 (estimated) |
| Average WKT size | ~7.8 KB | ~4.7 KB (estimated) |
| Total WKT data | ~1.7 MB | ~2.8 MB |

#### Egress Calculation for 28 March (peak day, 12,610 API requests)

**`SchoolListView` (`select_related` → JOINs constituency + DUN)**:
- 1,433 paginated requests × 50 schools/page
- Each school row includes full JOINed constituency (~7.8 KB WKT) + DUN (~4.7 KB WKT) = ~12.5 KB wasted per row
- 1,433 × 50 × 12.5 KB = **~895 MB of discarded WKT data**

**`ConstituencyListView`**:
- 190 paginated requests × ~35 constituencies with WKT per page × 7.8 KB
- 190 × 273 KB = **~52 MB**

**`DUNListView`**:
- 542 requests × ~30 DUNs with WKT per page × 4.7 KB
- 542 × 141 KB = **~76 MB**

**`ConstituencyDetailView` + `DUNDetailView`**:
- 543 constituency details × 7.8 KB + 792 DUN details × (4.7 + 7.8) KB
- **~14 MB**

**`SchoolDetailView` (select_related)**:
- 1,359 requests × 12.5 KB = **~17 MB**

| Source | Estimated Supabase Egress | % of Total |
|--------|--------------------------|-----------|
| SchoolListView boundary_wkt | ~895 MB | 73% |
| DUNListView boundary_wkt | ~76 MB | 6% |
| ConstituencyListView boundary_wkt | ~52 MB | 4% |
| Actual useful API data | ~33 MB | 3% |
| Detail views boundary_wkt | ~31 MB | 3% |
| PG wire protocol overhead (~10%) | ~109 MB | 9% |
| Other (health checks, admin, etc.) | ~30 MB | 2% |
| **TOTAL ESTIMATED** | **~1,226 MB** | **100%** |

**This accounts for ~65% of the 1.9 GB observed.** The remaining gap may be explained by:
1. PostgreSQL wire protocol overhead being higher than my 10% estimate
2. The 10,000-entry log limit missing some requests on Mar 28 (there were 12,610 total)
3. Cloud Run health checks or internal Next.js requests not visible in access logs
4. Django's connection setup overhead (transaction pooler handshake, `SET` statements)

### 4. Per-Page Egress Audit

#### Measured API Response Payloads (what the frontend receives)

| Page | Data Fetched | API Response Size | DB→API Overhead |
|------|-------------|------------------|-----------------|
| **Parliament Watch** `/parliament-watch` | briefs (147 KB) + all mentions 4 pages (98 KB) + meetings (91 KB) | **339 KB** | Low — no JOINed WKT |
| **News** `/news` | news articles pageSize=500 (138 KB) | **135 KB** | Low |
| **Home** `/` | national stats (0.2 KB) + map schools (122 KB) | **123 KB** | Low — uses `.only()` |
| **Constituencies Index** `/constituencies` | all 222 constituencies, 5 pages (27 KB) | **27 KB** | **HIGH — full rows with WKT** |
| **Constituency Detail** `/constituency/[code]` | detail (2 KB) + GeoJSON (17 KB) + DUNs + mentions | **25 KB** | HIGH — full row with WKT |
| **School Detail** `/school/[moe_code]` | detail (4 KB) + constituency schools (6 KB) + mentions + news | **11 KB** | HIGH — `select_related` fetches WKT |
| **DUN Detail** `/dun/[id]` | detail + schools | ~15 KB | HIGH — full row with WKT |
| **Sitemap** `/sitemap.xml` | map schools (122 KB) + paginated constituencies (27 KB) | **149 KB backend** | Moderate |

#### Request Frequency by Endpoint (28 March)

| Endpoint Pattern | Requests | Total API Response | Estimated DB Egress |
|-----------------|----------|-------------------|-------------------|
| `/api/v1/schools/` (list, paginated) | 1,433 | 9.81 MB | **~905 MB** |
| `/api/v1/schools/{moe}/` (detail) | 1,359 | 4.04 MB | ~21 MB |
| `/api/v1/schools/{moe}/mentions/` | 1,359 | 0.54 MB | ~0.6 MB |
| `/api/v1/schools/{moe}/news/` | 1,359 | 0.77 MB | ~0.8 MB |
| `/api/v1/duns/{id}/` (detail) | 792 | 1.59 MB | ~11 MB |
| `/api/v1/duns/{id}/geojson/` | 793 | 1.91 MB | ~2 MB |
| `/api/v1/constituencies/{code}/` (detail) | 543 | 2.72 MB | ~7 MB |
| `/api/v1/constituencies/{code}/geojson/` | 543 | 2.37 MB | ~2.5 MB |
| `/api/v1/constituencies/{code}/mentions/` | 543 | 0.45 MB | ~0.5 MB |
| `/api/v1/duns/` (list, paginated) | 542 | 0.37 MB | **~76 MB** |
| `/api/v1/constituencies/` (list, paginated) | 190 | 1.05 MB | **~52 MB** |
| `/api/v1/meetings/` | 34 | 2.97 MB | ~3 MB |
| `/api/v1/mentions/` (all, paginated) | 24 | 0.58 MB | ~0.6 MB |
| `/api/v1/briefs/` | 12 | 1.69 MB | ~1.7 MB |
| `/api/v1/news/` | 7 | 0.89 MB | ~0.9 MB |
| Other | ~70 | 1.48 MB | ~2 MB |

### 5. `fetchAllMentions` and News `pageSize=500` Assessment

#### fetchAllMentions()
- **Payload**: 98 KB total (4 paginated pages of 50, 182 mentions)
- **Requests on 28 Mar**: 24 (= 6 full pagination cycles, i.e., 6 parliament-watch page renders)
- **Daily egress contribution**: ~0.6 MB — **not significant**
- The concern in the brief about "200+ parliament mentions with nested school prefetch" is overstated. The mentions endpoint returns compact data (~540 bytes per mention).

#### News pageSize=500
- **Payload**: 138 KB per request
- **Requests on 28 Mar**: 7
- **Daily egress contribution**: ~0.9 MB — **not significant**
- However, the payload is unnecessarily large. Most users won't scroll through 500 articles.

### 6. Other Potential Egress Sources

- **Client-side fetches**: Minimal. Only auth-related pages (dashboard, edit, profile) and the search typeahead make client-side API calls. These are low-volume and small-payload.
- **Supabase Realtime subscriptions**: None found. No Supabase client library is used in the frontend.
- **Supabase Storage**: Not used. School images are served directly from Google Places API.
- **API routes proxying large queries**: Only one API route exists (`/api/auth/[...nextauth]`) for NextAuth — minimal.
- **Background Cloud Run jobs**: 6 scheduled jobs run daily (news pipeline, hansard check, etc.). These primarily WRITE to the database. Egress from reads is minimal. The Brevo webhook endpoint had 113 requests on Mar 28 — tiny payloads.
- **WordPress exploit probes**: Several requests for `/wp-includes/sitemaps/` were observed — these return small error pages, negligible egress.

---

## Phase 2 — Diagnosis

### Ranked Egress Sources

| Rank | Source | Estimated Daily Egress | Evidence |
|------|--------|----------------------|----------|
| **1** | **`boundary_wkt` fetched via `select_related` on SchoolListView** | **~895 MB** (peak) | 1,433 requests × 50 rows × 12.5 KB discarded WKT |
| **2** | **`boundary_wkt` on DUNListView** | **~76 MB** | 542 requests × full DUN rows with WKT |
| **3** | **`boundary_wkt` on ConstituencyListView** | **~52 MB** | 190 requests × full rows with WKT |
| **4** | **Detail views with `select_related`** | **~31 MB** | 2,694 detail requests fetching JOINed WKT |
| **5** | **Parliament Watch page** (3 heavy endpoints) | **~3 MB** | 339 KB × ~9 renders/day |
| **6** | **Actual useful API data** | **~33 MB** | All other API responses |
| **7** | **News page (pageSize=500)** | **~1 MB** | 138 KB × ~7 renders/day |

### Root Cause Summary

**The egress problem has three compounding causes:**

1. **Django ORM fetches `boundary_wkt` on every query** (except SchoolMapView). The WKT polygon data is large (5–8 KB per row) and transferred via PostgreSQL wire protocol from Supabase to Cloud Run, then discarded by the serializer. This is ~85% of estimated Supabase egress.

2. **Crawlers generate 95% of page requests**, each triggering fresh API calls because there's no effective cache. A single bot (Chrome/91 from 88.216.210.27) alone generates ~1,413 requests/day, systematically crawling every page.

3. **Next.js ISR caching is broken on Cloud Run** because containers are ephemeral (scale-to-zero) and no external cache handler is configured. `revalidate = false` only works within a running container's lifetime. Every cold start = empty cache = fresh DB queries for every page.

### How Next.js Caching Works (or Doesn't) on This Setup

```
User/Crawler Request
        ↓
Cloud Run (Next.js container)
  ├── Cache hit? → Serve cached HTML (rare — cache lost on restart)
  └── Cache miss? → Server-side render
        ↓
        Fetch from Django API (Cloud Run backend)
        ↓
        Django ORM: SELECT * FROM schools_school
                    LEFT JOIN schools_constituency ...   ← fetches boundary_wkt!
                    LEFT JOIN schools_dun ...            ← fetches boundary_wkt!
        ↓
        Supabase PostgreSQL → sends full rows over wire → Cloud Run backend
        ↓
        Serializer: discards boundary_wkt, returns 3 KB JSON
        ↓
        Next.js: renders HTML, stores in ephemeral cache
        ↓
        Serve to user
        ↓
        [Container scales to zero → cache destroyed → repeat]
```

### Observability Gaps

1. **No direct Supabase dashboard access** — Tamil Foundation org Supabase is not connected to this session's MCP tools.
2. **Cloud Run logs capped at 10,000 entries** — Mar 28 had 12,610 API requests but I could only sample 10,000.
3. **No `pg_stat_statements`** — Cannot directly measure per-query database egress. The WKT estimates are derived from GeoJSON endpoint sampling (×1.5 factor), not direct measurement.
4. **Cannot distinguish container restart frequency** — Cloud Run logs don't directly show when containers scale to zero and restart.

---

## Phase 3 — Proposed Solutions

### Fix 1: Add `.defer('boundary_wkt')` to All Non-GeoJSON Views

**Impact**: HIGH (~85% of egress eliminated)
**Effort**: LOW (4 lines changed)
**Risk**: LOW

```python
# SchoolListView
qs = School.objects.select_related("constituency", "dun").prefetch_related("images").filter(is_active=True).defer("constituency__boundary_wkt", "dun__boundary_wkt")

# ConstituencyListView
qs = Constituency.objects.defer("boundary_wkt").annotate(...)

# DUNListView
qs = DUN.objects.select_related("constituency").defer("boundary_wkt", "constituency__boundary_wkt")

# SchoolDetailView
queryset = School.objects.select_related("constituency", "dun").prefetch_related("leaders").defer("constituency__boundary_wkt", "dun__boundary_wkt")

# ConstituencyDetailView
queryset = Constituency.objects.defer("boundary_wkt").prefetch_related("schools", "scorecards")

# DUNDetailView
queryset = DUN.objects.select_related("constituency").prefetch_related("schools").defer("boundary_wkt", "constituency__boundary_wkt")
```

**What it does**: Tells Django to exclude `boundary_wkt` from the SQL SELECT clause. The data is never fetched from Supabase, never transferred over the wire.

**Expected reduction**: ~1,050 MB/day on a peak day (Mar 28 baseline). On a normal day (~2,500 API requests), ~250-400 MB/day.

**What could go wrong**: If any code accesses `obj.boundary_wkt` on a deferred object, Django will issue a separate query to fetch it (lazy loading). But only the GeoJSON views need this field, and they already use `.only()` to explicitly include it.

**Requires**: Backend deploy only.

---

### Fix 2: Block or Rate-Limit Aggressive Crawlers

**Impact**: HIGH (~87% of frontend traffic eliminated)
**Effort**: LOW (update robots.txt + Cloud Run config)
**Risk**: LOW-MEDIUM (may affect SEO discoverability)

**Step 2a**: Update `robots.txt` to block non-essential crawlers:
```
User-Agent: AhrefsBot
Disallow: /

User-Agent: GPTBot
Disallow: /

User-Agent: OAI-SearchBot
Disallow: /

User-Agent: Amazonbot
Disallow: /

User-Agent: ClaudeBot
Disallow: /

User-Agent: *
Allow: /
Disallow: /api/
Disallow: /dashboard/
Disallow: /claim/verify/
Crawl-delay: 10

Sitemap: https://tamilschool.org/sitemap.xml
```

**Step 2b**: Block the Chrome/91 bot (88.216.210.27) via Cloud Armor or middleware:
- This single IP generates ~1,413 requests/day
- Uses an outdated Chrome/91 UA — not a real browser
- Systematically crawls every page variant

**Step 2c**: Add `Crawl-delay: 10` for Googlebot (or use Google Search Console to set crawl rate).

**Expected reduction**: ~60-80% of frontend requests eliminated → proportional reduction in API calls → proportional reduction in Supabase egress.

**What could go wrong**: Blocking AI crawlers (GPTBot, ClaudeBot) means the site won't appear in AI search results. Blocking AhrefsBot means losing SEO analysis tools. These trade-offs may be acceptable for a niche educational site.

**Requires**: Frontend deploy (robots.txt) + optional Cloud Armor rule.

---

### Fix 3: Set Cloud Run `minScale=1` (Keep One Container Always Warm)

**Impact**: MEDIUM (prevents cache loss from scale-to-zero)
**Effort**: LOW (one CLI command)
**Risk**: LOW (small cost increase)

```bash
gcloud run services update sjktconnect-web \
  --account admin@tamilfoundation.org \
  --project sjktconnect \
  --region asia-southeast1 \
  --min-instances 1
```

**What it does**: Keeps at least one container always running, so the Next.js in-memory/filesystem cache persists between requests. Combined with `revalidate = false`, pages are cached indefinitely within that container.

**Expected reduction**: Difficult to quantify precisely. If one container handles all traffic (within 80 concurrent requests), most pages would be served from cache after the first render. Estimated ~50-70% reduction in API calls.

**What could go wrong**:
- Cost: ~$5-10/month for one always-on container (vCPU + memory). Worth it if it saves 50%+ of egress.
- Cache is still per-instance and in-memory (50 MB limit). If traffic exceeds one instance's capacity, the second instance starts with an empty cache.
- Not a substitute for Fix 1 — the first render still fetches all data including WKT.

**Requires**: Cloud Run config change (no deploy needed).

---

### Fix 4: Reduce Parliament Watch Page Payload

**Impact**: LOW (3 MB/day → <1 MB/day)
**Effort**: LOW
**Risk**: LOW

Currently, the Parliament Watch page fetches:
- `fetchBriefs()` → 147 KB (all briefs, but only shows 4)
- `fetchAllMentions()` → 98 KB (all 182 mentions, 4 paginated pages)
- `fetchMeetingReports()` → 91 KB

**Proposed changes**:
1. Fetch only the 4 most recent briefs: `GET /api/v1/briefs/?page_size=4`
2. Don't fetch all mentions — compute stats server-side via a new `/api/v1/mentions/stats/` endpoint
3. Meeting reports are legitimately needed for the grid display

**Expected reduction**: 147 KB + 98 KB → ~20 KB per render. Saves ~200 KB per render × 9 renders/day = ~1.8 MB/day.

**Requires**: Backend + frontend changes.

---

### Fix 5: Reduce News Page Size

**Impact**: LOW (~0.9 MB/day → ~0.2 MB/day)
**Effort**: LOW
**Risk**: LOW

Change `fetchNews({ pageSize: 500 })` to `fetchNews({ pageSize: 20 })` with client-side pagination.

**Expected reduction**: 138 KB → ~6 KB per initial render. With only 7 renders/day, saves ~0.9 MB/day.

**Requires**: Frontend change only.

---

### Fix 6: Implement External Cache Handler (Long-Term)

**Impact**: HIGH (eliminates the ISR problem entirely)
**Effort**: HIGH
**Risk**: MEDIUM

Options:
1. **Redis via Cloud Memorystore**: Add a Redis instance, configure `cacheHandler` in `next.config.js`. All ISR cache writes go to Redis, persist across container restarts.
2. **Google Cloud Storage FUSE mount**: Mount a GCS bucket as filesystem on Cloud Run. The default Next.js filesystem cache persists across container restarts.

**Expected reduction**: Combined with `revalidate = false`, pages would be cached truly "forever" across container restarts. Only the first-ever render of each page triggers API calls. Estimated 90%+ reduction in API calls.

**What could go wrong**: Redis costs ~$10-30/month (Cloud Memorystore minimum). GCS FUSE adds latency. Both add infrastructure complexity.

**Not recommended now**: Fix 1 (defer WKT) + Fix 2 (block crawlers) + Fix 3 (minScale=1) should reduce egress to <100 MB/day, well within free tier limits.

---

## Priority Matrix

| Priority | Fix | Impact | Effort | Expected Reduction |
|----------|-----|--------|--------|-------------------|
| **P0** | Fix 1: `.defer('boundary_wkt')` | HIGH | 30 min | ~85% of DB egress |
| **P0** | Fix 2: Block aggressive crawlers | HIGH | 30 min | ~60-80% of traffic |
| **P1** | Fix 3: `minScale=1` | MEDIUM | 5 min | ~50-70% of remaining |
| **P2** | Fix 4: Parliament Watch payload | LOW | 1 hour | ~2 MB/day |
| **P2** | Fix 5: News pageSize=20 | LOW | 10 min | ~1 MB/day |
| **P3** | Fix 6: External cache handler | HIGH | 1-2 days | 90%+ (long-term) |

**Recommendation**: Implement Fix 1 + Fix 2 first. These two changes alone should reduce Supabase egress from ~1.9 GB/day to under 100 MB/day. Monitor for 3 days, then decide if Fix 3 or Fix 6 is needed.

---

## Appendix A: Full fetchAllMentions Trace

```
Parliament Watch page render → Promise.all([
  fetchMeetingReports()    → GET /api/v1/meetings/           → 91 KB
  fetchBriefs()            → GET /api/v1/briefs/             → 147 KB
  fetchAllMentions()       → GET /api/v1/mentions/           → 29 KB (page 1)
                           → GET /api/v1/mentions/?page=2    → 27 KB
                           → GET /api/v1/mentions/?page=3    → 24 KB
                           → GET /api/v1/mentions/?page=4    → 18 KB
                                                    Total:     98 KB (4 pages, 182 mentions)
])
Total per render: 339 KB API response
```

## Appendix B: Chrome/91 Bot Analysis

- **IP**: 88.216.210.27
- **User-Agent**: `Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36`
- **Behaviour**: Systematically crawls all pages via `www.tamilschool.org` (note: www subdomain, not bare domain)
- **Pages hit**: school pages, DUN pages, constituency pages, parliament-watch pages, sitting pages
- **Rate**: ~1,413 requests/day (sustained)
- **Classification**: Likely a scraper bot — Chrome 91 was released in 2021 and is not a current browser version
