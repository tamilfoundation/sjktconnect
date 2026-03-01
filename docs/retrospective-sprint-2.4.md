# Sprint 2.4 Retrospective — Subscribe/Unsubscribe Frontend Pages

**Date**: 1 March 2026
**Duration**: Single session
**Sprint goal**: Build Next.js pages for subscribe, unsubscribe, and preference management

## What Was Built

- `/subscribe/` page with SubscribeForm component (email, name, organisation, category preview)
- `/unsubscribe/[token]/` page with UnsubscribeConfirmation component (auto-calls API on mount)
- `/preferences/[token]/` page with PreferencesForm component (load, toggle, save)
- API client functions: subscribe, unsubscribe, fetchPreferences, updatePreferences
- TypeScript interfaces for all subscriber API shapes
- Footer "Subscribe to Intelligence Blast" link
- 33 new frontend tests (4 test files)

## What Went Well

- **Clean API contract**: Sprint 2.1 subscriber API was well-designed with clear request/response shapes. Frontend integration was straightforward — no backend changes needed.
- **Consistent patterns**: Following the existing ClaimForm/ClaimPage pattern made all three pages predictable to build (breadcrumb, metadata, card layout, loading/success/error states).
- **Fast execution**: Frontend-only sprint with no backend dependencies meant no context-switching between Django and Next.js.
- **Test-first mindset**: Writing tests immediately after components caught the HTML email validation issue (browser blocks submit for invalid emails, so API-level error test needed a valid-looking email).

## What Went Wrong

- **HTML email validation gap in test**: Initial error test used `"bad-email"` as input, but `<input type="email" required>` blocks form submission for invalid emails. The API mock was never called. Fixed by using a valid email and testing API-level errors instead.

## Design Decisions

- **Auto-unsubscribe on mount**: UnsubscribeConfirmation calls the API immediately when the page loads (via useEffect), matching the one-click unsubscribe pattern from email footers. No confirmation button needed.
- **Server components for pages, client components for forms**: Pages are server components (metadata, SEO). Interactive forms are `"use client"` components passed as children.
- **Category preview (not selection) on subscribe form**: All categories are enabled by default. The subscribe form shows what you'll receive but doesn't let you toggle — keeps the form simple. Use `/preferences/[token]/` after subscribing to customise.
- **Unsubscribe link on preferences page**: PreferencesForm includes a link to `/unsubscribe/[token]` for users who want to opt out entirely rather than just toggling categories.

## Numbers

- Files created: 9 (3 pages, 3 components, 4 test files)
- Files modified: 4 (types.ts, api.ts, Footer.tsx, Footer.test.tsx)
- Tests: 33 new frontend, 683 total (516 backend + 167 frontend)
- Lines of code: ~650 new (components + tests)
