# Egress Fix Retrospective — Supabase Egress Optimisation

**Date**: 2026-03-29
**Duration**: ~2 hours (investigation + implementation + deploy)

## What Was Built

1. **Backend ORM optimisation**: Added `.defer("boundary_wkt")` to 6 non-GeoJSON views (`SchoolListView`, `SchoolDetailView`, `ConstituencyListView`, `ConstituencyDetailView`, `DUNListView`, `DUNDetailView`). This stops Django from fetching 5-8 KB WKT polygon data per row that serializers discard.

2. **Bot IP blocking**: Next.js middleware now blocks known scraper IPs. Chrome/91 bot at 88.216.210.27 was generating ~1,413 requests/day (87% of frontend traffic).

3. **robots.txt bot exclusions**: Blocked AhrefsBot, GPTBot, OAI-SearchBot, Amazonbot, and ClaudeBot — together ~95% of frontend traffic but no value.

4. **Cloud Run minScale=1**: Frontend container kept warm to preserve Next.js ISR cache (broken by scale-to-zero on ephemeral containers).

5. **Investigation report**: Full egress analysis at `docs/egress-investigation-report.md` with measured payload sizes, traffic patterns, and ranked fix proposals.

## What Went Well

- **Root cause identification was systematic**: Measured actual payload sizes from API responses, sampled Cloud Run logs for traffic patterns, and cross-referenced with Django ORM behaviour. The `.defer()` fix was high-confidence before implementation.
- **GeoJSON endpoints unaffected**: The fix correctly targeted only non-GeoJSON views. GeoJSON endpoints use `.only()` with explicit field lists and were verified byte-identical after deploy.
- **All 3 deploys succeeded first try**: Backend, frontend code changes, and frontend infra change (minScale) each deployed cleanly.

## What Went Wrong

1. **Cannot access Supabase dashboard programmatically**: SJKTConnect's Supabase project is under Tamil Foundation org, not connected to the MCP integration. Only HalaTuju/tamilnadai/Lentera were listed. This meant we couldn't verify baseline egress numbers directly and had to estimate from API response sizes × traffic counts.
   - **Root cause**: MCP Supabase integration is per-org, and Tamil Foundation org wasn't connected.
   - **Fix**: Manual dashboard check required. Document this as an observability gap.

2. **Cloud Run log sampling capped at 10,000 entries**: Mar 28 had 12,610 API requests but we could only sample 10,000. Traffic patterns may be slightly off.
   - **Root cause**: Cloud Run logging default retention/query limits.
   - **Fix**: For future traffic analysis, query Cloud Run metrics (request_count) instead of raw logs.

3. **35% gap between estimated and observed egress**: Estimated ~1.23 GB/day from API analysis but observed 1.9 GB/day. The gap may be connection overhead, PostgreSQL wire protocol framing, or unidentified egress sources.
   - **Root cause**: Estimation methodology only accounts for response body bytes, not protocol overhead.
   - **Fix**: Monitor post-fix egress to validate. If still high, investigate connection-level overhead.

## Design Decisions

- **`.defer()` over `.only()`**: `.defer()` is safer — it excludes specific fields while keeping everything else. `.only()` requires listing every field you want, which breaks when new fields are added. `.defer()` is the right choice when you want to exclude a few known-large fields.
- **Middleware IP blocking over WAF**: Simple `Set` lookup in middleware is zero-cost, zero-infra. A WAF would be overkill for blocking a single known IP.
- **minScale=1 over Redis cache handler**: Keeping one container warm preserves Next.js built-in cache without adding infrastructure complexity. Redis would be the right move if we needed multi-container cache sharing.

## Numbers

| Metric | Before | After (expected) |
|--------|--------|-------------------|
| Supabase egress | ~1.9 GB/day | <100 MB/day |
| boundary_wkt bytes per SchoolList request | ~625 KB (50 rows × 12.5 KB) | 0 KB |
| Frontend bot traffic | ~95% of requests | ~0% (blocked) |
| Cloud Run frontend min instances | 0 (scale-to-zero) | 1 (warm cache) |
| API responses | Byte-identical | Byte-identical |
