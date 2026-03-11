# Proposal: Cloudflare as Reverse Proxy for tamilschool.org

**Date:** 2026-03-11
**Author:** Tamil Foundation technical team
**Status:** For review

---

## Problem

SJK(T) Connect (tamilschool.org) is a community platform where users sign in with Google to suggest school data corrections, upload photos, moderate content, and earn points. The site runs on Google Cloud Run.

Cloud Run's built-in custom domain mapping has a known limitation: **HTTP cookies are not reliably preserved** during cross-origin redirects. This breaks Google OAuth sign-in, which depends on cookies to verify the authentication flow. After six deployment attempts with different cookie configurations, we confirmed that no cookies survive the OAuth round-trip on Cloud Run's domain mapping.

This is not a code issue. It is an infrastructure limitation.

## Current Architecture

```
Browser → tamilschool.org (Cloud Run domain mapping) → Cloud Run container
```

- **Hosting:** Google Cloud Run (asia-southeast1)
- **Backend:** Django REST API (sjktconnect-api)
- **Frontend:** Next.js 14 (sjktconnect-web)
- **Database:** Supabase PostgreSQL
- **Auth:** Google OAuth via NextAuth.js v5
- **Domain:** tamilschool.org (DNS managed by current registrar)
- **Cost:** ~$0/month (Cloud Run free tier)

## Proposed Change

Add Cloudflare (free tier) as a reverse proxy in front of Cloud Run.

```
Browser → Cloudflare (DNS + proxy) → Cloud Run container
```

Nothing else changes. Code, hosting, database, deployments — all remain on Google Cloud.

### What Cloudflare Does

| Function | Description |
|----------|-------------|
| **DNS** | Resolves tamilschool.org to Cloudflare's edge network |
| **Reverse proxy** | Forwards requests to Cloud Run, preserving all HTTP headers and cookies |
| **SSL/TLS** | Manages HTTPS certificates automatically (no renewal needed) |
| **CDN caching** | Caches static assets (images, CSS, JS) at 300+ edge locations worldwide |
| **DDoS protection** | Absorbs malicious traffic before it reaches Cloud Run |
| **Analytics** | Basic traffic analytics (visits, countries, threats blocked) |

### What Cloudflare Does NOT Do

- Does not host the site (Cloud Run still runs the application)
- Does not store any data (database stays on Supabase)
- Does not require code changes
- Does not affect deployments (still `gcloud run deploy` as usual)
- Does not lock us in (remove Cloudflare by pointing DNS back to Cloud Run)

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

1. Create a free Cloudflare account
2. Add tamilschool.org to Cloudflare
3. Cloudflare scans existing DNS records automatically
4. Update domain registrar nameservers to Cloudflare's (2 nameserver addresses)
5. Configure Cloudflare to proxy to Cloud Run URLs:
   - tamilschool.org → sjktconnect-web (frontend)
   - API requests continue to go directly to sjktconnect-api (backend)
6. Set SSL mode to "Full (strict)"
7. Re-enable OAuth cookie security checks in NextAuth config
8. Test sign-in end-to-end

**Estimated time:** 30 minutes
**Downtime:** None (DNS propagation happens in background, typically 5-30 minutes)

## Cost

**$0/month.** Cloudflare's free tier includes:
- Unlimited bandwidth
- CDN caching
- DDoS protection
- SSL certificates
- DNS management
- Basic analytics

Paid tiers exist ($20+/month) but are not needed.

## Risks

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| DNS propagation delay | Low | Cloudflare typically propagates in minutes. Old DNS cached for up to 24 hours. |
| Cloudflare outage | Very low | Cloudflare has 99.99% uptime SLA. Can revert DNS to Cloud Run directly. |
| Vendor dependency | Low | Fully reversible — change nameservers back and everything works as before. |
| Over-caching | Low | Configure cache rules to exclude API routes and auth pages. |

## Recommendation

Adopt Cloudflare free tier as the DNS and proxy layer for tamilschool.org. This is standard practice for production web applications and solves the immediate cookie/auth problem while adding CDN, security, and analytics at no cost.

The change is fully reversible. If Cloudflare proves unnecessary in future, revert by pointing nameservers back to the original registrar.
