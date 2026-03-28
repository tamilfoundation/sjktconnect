# Retrospective — Sprint 8.3: Supabase Egress Optimisation (2026-03-28)

## What Was Built

- **Lightweight map API endpoint** (`/api/v1/schools/map/`): Returns 528 schools with 10 fields (~50 KB) instead of the full 23-field response (~550 KB). Non-paginated single response.
- **Server-side school data for homepage**: Homepage now fetches schools server-side via Next.js ISR (revalidate every 24 hours). SchoolMap component receives data as props instead of fetching client-side on every page load.
- **News revalidation adjustment**: Changed from 5 minutes to 24 hours (news arrives ~1-2 per week).
- **Welcome email batch tracking**: `send_welcome_email` command now tracks who already received the email, enabling safe re-runs for batch 2.
- **Subscriber ID audience filter**: Broadcasts can now target specific subscriber IDs.

## What Went Well

- Root cause analysis was thorough — traced Supabase egress from user's "20 GB used" alert all the way down to the specific client-side fetch pattern, ruling out other causes (scheduled jobs, news pipeline) with data.
- The fix is architecturally clean: server-side fetch + ISR means Supabase sees 1 request per 24h regardless of visitor count. Scales from 3 users/day to 1,000+ without hitting free tier limits.
- No new tests needed — existing 1363 tests all pass. The change was purely a data flow refactor (where data is fetched, not what is fetched).

## What Went Wrong

1. **SchoolMap was fetching all schools client-side since Sprint 1.3 (4 months ago).**
   - *Symptom*: Supabase egress exceeded 5 GB free tier (20 GB used in March).
   - *Root cause*: When the map was first built (Sprint 1.3), client-side fetch was the quick path. As Googlebot indexed 528+ school pages and the homepage, each crawl triggered a fresh API call. Nobody noticed because the site had low traffic — until the egress alert.
   - *System change*: For any component that displays static/rarely-changing data on the homepage or high-traffic pages, default to server-side fetch + ISR. Added this as a principle to the codebase. The `fetchMapSchools()` function exists specifically for the server component to use.

2. **News page was revalidating every 5 minutes for data that changes weekly.**
   - *Symptom*: Unnecessary Supabase queries every 5 minutes per edge location.
   - *Root cause*: The 5-minute revalidation was carried over from an early prototype where we expected frequent news updates. In reality, only ~15 articles appeared in all of March.
   - *System change*: Set revalidation to 24 hours. Future ISR pages should match revalidation period to actual data change frequency, not worst-case.

## Design Decisions

- **Keep SchoolMap as "use client"** — it needs interactive state (filters, search, map controls). The server component fetches data; the client component handles interactivity. This is the standard Next.js App Router pattern.
- **Added preschool_enrolment + special_enrolment to map serializer** — the "Programmes" filter mode needs these fields. Started with 8 fields, expanded to 10. Still ~90% smaller than the full serializer.

## Numbers

- Backend tests: 1073
- Frontend tests: 290
- Total: 1363
- Files changed: 9
- Estimated egress reduction: ~1000x (from per-visitor to per-day)
- Map API response size: ~50 KB (vs ~550 KB from full endpoint)
