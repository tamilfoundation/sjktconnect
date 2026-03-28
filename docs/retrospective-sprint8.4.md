# Retrospective — Sprint 8.4: SEO Improvements (2026-03-28)

## What Was Built

- **Hreflang alternate links and canonical URLs** on all 22 pages, fixing 69 "Duplicate without user-selected canonical" errors reported by Google Search Console.
- **Dynamic sitemap.xml** with locale alternates for all static pages + 528 school pages + constituency pages.
- **robots.txt** blocking /api/, /dashboard/, and /claim/verify/ from crawlers.
- **Richer meta titles for school pages**: "SJK(T) Name | 450 Students, Grade A | Selangor" format includes enrolment, grade, and state — more useful in search results.
- **Richer meta descriptions for school pages**: now include city/location, preschool/special ed availability, and a call to action.
- **Richer meta titles for constituency pages**: "Name (Code) | 5 Tamil Schools | State" format.
- **`lib/seo.ts` helper** with `buildAlternates()` function for consistent hreflang/canonical generation.

## What Went Well

- **Clean, focused sprint**: All changes were frontend-only metadata and static files. No backend changes, no database migrations, no API changes.
- **No test impact**: SEO metadata is verified at build time by Next.js. No new runtime tests needed — the build itself validates that metadata functions return valid objects.
- **Single commit**: The entire sprint was small enough to fit into one well-scoped commit (aee8f61).
- **Directly addresses a real GSC issue**: 69 duplicate-without-canonical warnings were the motivation, and this sprint fixes all of them.

## What Went Wrong

- Nothing significant. This was a straightforward, well-scoped sprint with no surprises.

## Design Decisions

1. **`buildAlternates()` centralises locale URL generation** rather than repeating hreflang logic in each page's `generateMetadata()`. This keeps the 22 pages DRY and ensures consistency if locale list changes.
2. **Dynamic sitemap over static**: The sitemap is generated at request time (with ISR caching) rather than at build time, so new school or constituency pages are picked up without redeployment.
3. **robots.txt blocks internal paths**: `/api/`, `/dashboard/`, and `/claim/verify/` are excluded from crawling to prevent indexing of API responses and authenticated-only pages.

## Numbers

- Pages with hreflang/canonical: 22
- GSC "Duplicate without user-selected canonical" errors fixed: 69
- Sitemap URLs: ~550+ (static pages x 3 locales + 528 schools x 3 locales + constituencies x 3 locales)
- Tests: 1363 (unchanged — 1073 backend + 290 frontend)
- Backend changes: 0
- Commits: 1 (aee8f61)
- Deploy: frontend revision sjktconnect-web-00070-mgx
