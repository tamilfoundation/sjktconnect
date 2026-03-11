# Proposal: Cloudflare as Reverse Proxy for tamilschool.org

**Date:** 2026-03-11
**Author:** Tamil Foundation technical team
**Status:** For review (v2 — revised after advisor feedback)

---

## Problem

SJK(T) Connect (tamilschool.org) is a community platform where users sign in with Google to suggest school data corrections, upload photos, moderate content, and earn points. The site runs on Google Cloud Run.

Cloud Run's built-in custom domain mapping has a known limitation: **HTTP cookies are not reliably preserved** during OAuth redirect flows. After six deployment attempts with different cookie configurations (PKCE, state-based, nonce-based, secure/non-secure, custom cookie names), we confirmed that no cookies set before the Google OAuth redirect are present when Google redirects back. This breaks sign-in.

**Why cookies are lost:** Cloud Run's domain mapping uses Google's global frontend infrastructure to route custom domains to containers. Unlike a standard reverse proxy, this mapping does not preserve `Set-Cookie` response headers in the same way during redirect chains. The container sees the request as HTTP internally (TLS terminates at Google's edge), and cookies marked `Secure` are not set. Even with `Secure` disabled, the mapping's redirect handling strips or fails to return cookies to the browser. This is a documented limitation — Google's own guidance for production custom domains is to use a Cloud Load Balancer or external proxy instead of the built-in domain mapping.

**Why Cloudflare fixes this:** Cloudflare acts as a standard reverse proxy with full HTTP header passthrough. It terminates TLS at its edge, forwards the complete request (including all cookies) to Cloud Run's `.run.app` URL over HTTPS, and returns the complete response (including `Set-Cookie` headers) to the browser. The cookie round-trip is between the browser and Cloudflare's proxy — Cloud Run's domain mapping is bypassed entirely. This is the same architecture used by thousands of production sites running on Cloud Run, Cloud Functions, and similar serverless platforms.

**Has this been validated?** Not yet on tamilschool.org specifically, but the pattern (Cloudflare proxy → Cloud Run origin) is standard and well-tested across the industry. We will validate on a test subdomain (e.g., `test.tamilschool.org`) before switching the main domain.

## Current Architecture

```
Browser → tamilschool.org (Cloud Run domain mapping) → Cloud Run container
```

- **Hosting:** Google Cloud Run (asia-southeast1)
- **Backend:** Django REST API (sjktconnect-api)
- **Frontend:** Next.js 14 (sjktconnect-web)
- **Database:** Supabase PostgreSQL (Singapore region)
- **Auth:** Google OAuth via NextAuth.js v5
- **Domain:** tamilschool.org (DNS managed by current registrar)
- **Cost:** ~$0/month (Cloud Run free tier)

## Proposed Change

Add Cloudflare (free tier) as a reverse proxy in front of Cloud Run. Remove the Cloud Run domain mapping for tamilschool.org — Cloudflare replaces it.

```
Browser → Cloudflare (DNS + proxy + TLS) → Cloud Run .run.app URL (origin)
```

### Routing Architecture

Both the frontend and API will be proxied through Cloudflare on the same domain:

| URL | Routes to | Purpose |
|-----|-----------|---------|
| `tamilschool.org/*` | sjktconnect-web (Cloud Run) | Frontend pages, auth |
| `tamilschool.org/api/*` | sjktconnect-web (Cloud Run) | Next.js API routes (auth) |
| API calls from frontend | sjktconnect-api (Cloud Run) | Django REST API |

**Important:** The frontend currently calls the Django API directly at its `.run.app` URL. These API calls use session tokens passed in request headers, not cookies — so they are unaffected by the cookie issue and do not need to go through Cloudflare. If we later need cookie-based API authentication (e.g., for server-side rendering with user context), we would add `api.tamilschool.org` as a Cloudflare-proxied subdomain pointing to the Django API service. This is a future consideration, not a current requirement.

### What Cloudflare Does

| Function | Description |
|----------|-------------|
| **DNS** | Resolves tamilschool.org to Cloudflare's edge network |
| **Reverse proxy** | Forwards requests to Cloud Run, preserving all HTTP headers and cookies |
| **SSL/TLS** | Manages HTTPS certificates automatically (no renewal needed) |
| **CDN caching** | Caches static assets only (see caching rules below) |
| **DDoS protection** | Absorbs malicious traffic before it reaches Cloud Run |
| **Analytics** | Basic traffic analytics (visits, countries, threats blocked) |

### What Cloudflare Does NOT Do

- Does not host the site (Cloud Run still runs the application)
- Does not store any application data (database stays on Supabase)
- Does not require code changes (only a NextAuth config restoration)
- Does not affect deployments (still `gcloud run deploy` as usual)
- Does not lock us in (remove Cloudflare by pointing DNS back; see Rollback section)

## Why This Matters for the Community Vision

SJK(T) Connect is designed as a community-managed platform, not a one-person operation. The roadmap includes:

- **Community users** signing in to suggest data corrections for 528 Tamil schools
- **School administrators** managing their school profiles and photos
- **Moderators** reviewing and approving community suggestions
- **Points system** rewarding active contributors

All of these require reliable user sessions (sign-in, stay signed in, perform actions). Without working cookies, none of this is possible in production.

## Alternatives Considered

| Option | Cost | Complexity | Verdict |
|--------|------|------------|---------|
| **Cloudflare free proxy** | $0/month | Low (DNS change only) | **Recommended** |
| Google Cloud Load Balancer | ~$18+/month | High (serverless NEG, SSL cert, IP reservation) | Too expensive for current stage |
| Rework auth to avoid cookies | $0 | High (non-standard, fragile, fights against every auth library) | Not sustainable |
| Firebase Hosting with rewrite | $0 | Medium (new service to manage, rewrite rules) | Adds Google dependency complexity |
| Stay on Cloud Run domain mapping | $0 | None | Broken — cookies don't work |

## Implementation

### Steps

1. Create a free Cloudflare account
2. Add tamilschool.org to Cloudflare
3. Cloudflare scans existing DNS records automatically — verify all records are correct
4. **Document current nameserver values** (for rollback — see below)
5. Update domain registrar nameservers to Cloudflare's (2 nameserver addresses)
6. Wait for DNS propagation (typically 5-30 minutes, can take up to 24 hours)
7. Configure Cloudflare:
   - SSL mode: "Full (strict)"
   - CNAME record: `tamilschool.org` → `sjktconnect-web-748286712183.asia-southeast1.run.app`
   - Cache rules (see Caching section below)
8. Remove the Cloud Run domain mapping for tamilschool.org (Cloudflare replaces it)
9. Restore NextAuth OAuth security checks (re-enable PKCE, remove `checks: []` workaround)
10. Test sign-in end-to-end on tamilschool.org across Chrome, Firefox, Safari
11. Verify rollback path works (see Rollback section)

### Caching Rules (configured on Day 1)

Cloudflare's default behaviour caches based on file extension, but for a site with authenticated users, we must be explicit to prevent one user seeing another's session state:

| Rule | Action | Reason |
|------|--------|--------|
| `tamilschool.org/api/*` | **Bypass cache** | All API routes, auth callbacks |
| `tamilschool.org/_next/static/*` | **Cache everything** (long TTL) | Next.js static assets (hashed filenames, immutable) |
| `*.js`, `*.css`, `*.png`, `*.jpg`, `*.ico`, `*.woff2` | **Cache everything** | Static files |
| Everything else (HTML pages) | **Bypass cache** | Server-rendered pages may contain user-specific content |

This ensures: static assets are cached globally (fast loads), but HTML pages and API responses are never cached (no session leakage).

**Estimated time:** Half a day (DNS change is quick; SSL verification, cache rule setup, OAuth testing, and cross-browser validation take longer)

**Downtime:** None expected (DNS propagation happens in background)

## Cost

**$0/month.** Cloudflare's free tier includes:
- Unlimited bandwidth
- CDN caching
- DDoS protection
- SSL certificates
- DNS management
- Basic analytics

Paid tiers exist ($20+/month) but are not needed.

**Note on media hosting:** Cloudflare's free tier TOS historically restricted use as a primary CDN for serving large media files. Currently, school images are served from Google Places API URLs and Cloud Run API endpoints, not from Cloudflare's cache. If the platform later hosts thousands of community-uploaded photos directly, we should monitor bandwidth and review Cloudflare's current acceptable use policy. At present scale (~1,000 images, averaging 50KB each), this is well within free tier norms.

## Risks

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| DNS propagation delay | Low | Cloudflare typically propagates in minutes. Old DNS cached for up to 24 hours. |
| Cloudflare outage | Very low | 99.99% uptime SLA. Rollback path documented and tested. |
| Vendor dependency | Low | Fully reversible — change 2 nameserver records back. No code coupling. |
| Session leakage via over-caching | Low | Cache rules configured on Day 1 to bypass cache for all HTML and API responses. Only static assets cached. |
| SSL mode misconfiguration | Low | Use "Full (strict)" mode. Test HTTPS end-to-end before switching main domain. |

## Data Sovereignty

Cloudflare does not store application data. It caches only static assets (CSS, JS, images) at edge nodes and passes all dynamic requests through to Cloud Run. User PII (Google email, display name) flows through Cloudflare's proxy but is not stored or cached.

The application data remains in Supabase PostgreSQL (Singapore region, `aws-1-ap-southeast-1`). Malaysia has no data localisation law that restricts routing through CDN edge nodes, and the Tamil Foundation is an NGO, not a government body. The school data itself is public MOE data.

## Rollback Plan

If Cloudflare needs to be removed:

1. Log in to domain registrar
2. Change nameservers back to original values (documented before migration)
3. Re-create Cloud Run domain mapping for tamilschool.org
4. Wait for DNS propagation
5. Re-apply the `checks: []` workaround in NextAuth config (cookies won't work without proxy)

**Rollback test:** After implementation, we will verify that the Cloud Run `.run.app` URL still serves the site correctly as a direct-access fallback. We will document the original nameserver values in the project's operational runbook.

## Recommendation

Adopt Cloudflare free tier as the DNS and proxy layer for tamilschool.org. This is standard practice for production web applications with user authentication. It solves the immediate cookie/auth problem while adding CDN, security, and analytics at no cost.

The change is fully reversible and will be validated on a test subdomain before switching the main domain.
