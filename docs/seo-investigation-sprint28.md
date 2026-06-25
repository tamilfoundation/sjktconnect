# SEO Investigation Brief (for Sprint 28 kickoff)

Created 2026-06-26 at Sprint 27 close, in response to owner-flagged GSC observations:

1. **Average position stuck at ~7.1** — example query: "sjkt subramaniya barathee" → tamilschool.org appears 7th; apac.com.my appears 3rd; Wikipedia + Facebook take the top 2 (domain authority).
2. **2.12k pages not indexed** across 9 GSC reasons.

This file is a kickoff brief — not a sprint plan. Sprint 28 should pick what to act on based on cost vs. expected lift.

---

## Part 1 — Why does apac.com.my outrank tamilschool.org?

### Quick anatomy of the live SERP

| # | Site | Why it ranks |
|---|------|---|
| 1 | `ms.wikipedia.org/wiki/Sekolah_...Subramaniya_Barathee` | Domain authority (Wikipedia >>>). Tamil schools that have Wikipedia stubs will always sit here. |
| 2 | `facebook.com/...Subramaniya Barathee` | Domain authority + community signal (6k+ followers, regular posts). The page is also Google-Maps-linked via the right-rail knowledge panel. |
| 3 | `apac.com.my/pbd1088/SJK%20T%20SUBRAMANIYA%20BARATHEE,%20GELUGOR.html` | SEO-friendly URL slug + page existed years before us + content is plain text (no React hydration). |
| ... | (other directory aggregators) | Volume of pages + age. |
| 7 | `tamilschool.org/en/school/PBD1088` | We have the data, the metadata, and JSON-LD — but the URL is just a code, the site is months old, and links pointing to us are sparse. |

### What apac.com.my does that we don't

I sampled their page; their URL is the killer feature:

```
https://www.apac.com.my/pbd1088/SJK%20T%20SUBRAMANIYA%20BARATHEE,%20GELUGOR.html
                              └─────────── school name in URL slug ─────────────┘
```

Google reads URL path as a strong relevance signal. Our URL is `/school/PBD1088` — the school code matches **nothing** a human would type, so URL relevance is zero for school-name queries. apac's URL contains "SUBRAMANIYA BARATHEE" — for a query like "sjkt subramaniya barathee", the URL ALONE matches the query intent before Google even reads the title.

The other gaps are softer:
- Plain HTML page (no React hydration cost on first paint — but our SSR + ISR should make us equivalent here).
- Page has been around for years; we're months old. Google trusts old pages more.
- Inbound links: schools and parents probably linked to apac.com.my years ago; nobody knows we exist yet.

### Concrete Sprint 28 fixes (ranked by expected lift vs. cost)

**1. Add school name to URL slug — biggest single win, ~½ day work**

Change route from `/school/[moe_code]` → `/school/[slug]` where slug is e.g. `pbd1088-subramaniya-barathee-gelugor`. Implementation:
- New page file `app/[locale]/school/[slug]/page.tsx` that splits `slug` on first `-`, takes everything up to the next `-` as moe_code, rest as decorative.
- Redirect old `/school/PBD1088` → new slug with 301 (preserves existing SERP positions).
- Update every internal link generator (`href={\`/school/${moe_code}\`}`) to use the slug shape — search + map + constituency lists + breadcrumbs.
- Update sitemap.xml + JSON-LD canonical to use the slug URL.

Validation: re-pull GSC Pages report 2 weeks after deploy; expect average position to improve by 1-3 places on school-name queries.

**2. Reduce reliance on slug-only signals — increase page text quantity, ~1 day**

Our page renders a hero + cards + sidebar. The visible body text per school is short. Google rewards pages with more contextual prose. Could add:
- A `<section>` titled "About SJK(T) Subramaniya Barathee" with a 2-3 paragraph blurb pulling town context, MP context, recent news teaser. Most of this we already have data for — it's a render-only change.
- "Frequently Asked Questions" mini-FAQ ("How many students attend SJK(T) X?", "What's the address?", "Who is the headmaster?") — Google loves Q&A schema and rewards in featured snippets.

**3. Get inbound links — out of our hands, but worth one push, ~2h to set up**

- Add a "Wikipedia link" button on each school page when `wikipedia_url` is set (we don't currently store it).
- Reach out to district education office to link tamilschool.org as a directory in their site footer.
- Add structured discovery via `ms.wikipedia.org` editor accounts — link from school stubs back to our richer page.

**4. Submit fresh URLs to GSC manually for the lagging schools** — 10 minutes per school, one-off

For the schools that show up on page 2-3 of GSC's "Crawled - currently not indexed" report, use the URL Inspection tool's "Request Indexing" — pushes them ahead in Google's queue. Not a permanent fix but quick win for the top 20 schools by current impression count.

### What we should NOT do

- Buy backlinks. Penalises us long-term.
- Stuff keywords. Penalises us long-term.
- Switch to plain HTML / drop React. We get SEO and dynamic UX from ISR; the cost is acceptable.
- Try to outrank Wikipedia. Impossible. Aim for #3.

---

## Part 2 — 2.12k pages not indexed (9 GSC reasons)

The numbers in the GSC export, in order of "worth fixing":

| Reason | Count | Severity | What to do |
|--------|------:|----------|-----------|
| Page with redirect | 1119 | **Benign** | These are the www→root + locale-default 301s from Sprint 22's Cloudflare Single Redirect ruleset. GSC shows them but they're not a problem — the canonical version IS indexed. **No fix needed; ignore.** |
| Crawled - currently not indexed | 380 | **Worth investigating** | Google saw the page but chose not to index. Usually means "thin content" or "duplicate of higher-quality page." Pull a sample of 20 from GSC, look for a pattern. Likely candidates: DUN pages with 0 schools, constituency pages where the MP scorecard is empty, and possibly some school pages with no leadership / photos / news. Fix: beef up content on the thin pages (see Part 1 #2). |
| Discovered - currently not indexed | 200 | **Patient — wait** | Google knows about them, hasn't crawled yet. This is a crawl-budget problem. Reduces over time as Google trusts us more. Submitting via GSC URL Inspection helps. |
| Alternative page with proper canonical tag | 170 | **Benign** | These are the `/ta/` and `/ms/` locale variants of our `/en/` pages. Google correctly identified them as locale alternates and indexed the canonical (/en/). **No fix needed; this is working correctly.** |
| Not found (404) | 157 | **Worth investigating** | Real 404s. Most likely sources: (a) old `/claim/[token]/` magic-link URLs from Sprint 1.6 (removed in Sprint 11a), (b) `/dashboard/...` admin URLs we changed, (c) suggestion or image URLs that no longer exist. Fix: pull the full 404 list from GSC, identify the pattern, add redirects in Cloudflare (you have API access — see `cloudflare_api_sjktconnect.md` memory). |
| Duplicate without user-selected canonical | 53 | **Worth investigating** | Pages without an explicit `<link rel="canonical">` tag. Sprint 8.4 + 22 added canonicals to most pages, but 53 are still missing them. Pull the GSC list, grep our app for the matching routes, add `buildAlternates()` from `lib/seo.ts` to each. |
| Duplicate, Google chose different canonical than user | 34 | **Worth investigating** | We declared a canonical but Google chose a different one. Usually means our canonical hint conflicts with internal links or hreflang. Pull the GSC list per-URL and check whether the canonical we set is actually the URL we link to most. |
| Blocked by robots.txt | 5 | **Verify intentional** | 5 URLs are blocked. Probably `/admin/`, `/dashboard/`, `/api/`, `/_next/`. Spot-check that nothing legitimate is in here. |
| Soft 404 | 1 | **Trivial** | One page returns 200 but Google thinks it's empty. Open it in GSC URL Inspection, see which page, fix or accept. |
| Excluded by 'noindex' tag | 0 | None | Working as intended. |

### Quick wins (Sprint 28 ~½ day total)

1. **Pull the 157 404 URLs from GSC** → either add Cloudflare redirects (one POST per URL) OR accept (if intentionally deleted). Estimated ~80% will be old magic-link URLs that should 410-Gone.
2. **Pull the 53 + 34 = 87 canonical-issue URLs** → audit the listed routes for missing `buildAlternates()`. One PR closes most.
3. **Pull a sample of 20 "Crawled - currently not indexed"** → identify thin-content pattern; the fix probably overlaps with Part 1 #2 (add prose to school pages).

Total expected impact: 700-1000 URLs moving from "not indexed" to "indexed" within 3-4 weeks of fixes landing.

### What we should NOT do

- Try to fix the 1119 "Page with redirect" entries. They're showing correctly; trying to "fix" them would break the www→root and locale-default redirects.
- Try to fix the 170 "Alternative page with proper canonical tag". These are Sprint 8.4's intended trilingual canonical setup working correctly.
- Submit the entire sitemap for re-crawl. Wastes our crawl budget; Google's algorithm picks pages to index, not us.

---

## Sprint 28 recommended scope

Pick 2-3 of:
- **(A)** School-name URL slug + 301 redirects from old URLs (½ day) — single biggest ranking lift.
- **(B)** GSC 404 audit + Cloudflare redirect mapping (½ day) — closes ~80% of the "Not found (404)" bucket, sends a quality signal.
- **(C)** Canonical audit for the 87 conflicted URLs (½ day) — fixes ~5% of un-indexed.
- **(D)** Body-content beef-up on school pages (1 day) — addresses both ranking and "thin-content" non-indexing in one pass. Highest blast radius.

Recommended combo for biggest lift: **(A) + (D)** — both are content+structure work, both impact ranking AND indexing.

(B) and (C) are housekeeping and can ship in a follow-up.

---

## Validation plan

Whatever Sprint 28 ships, schedule a **2026-07-15 GSC re-pull** (3 weeks post-deploy) to measure:
- Average position on school-name queries: target 4-5 (from 7.1).
- Indexed pages: target 4.0k (from 3.42k).
- "Not found (404)" bucket: target <30 (from 157, if (B) shipped).
- "Crawled - currently not indexed": target <200 (from 380, if (D) shipped).

If numbers haven't moved by 4 weeks, Google didn't accept the changes — re-audit.
