# Retrospective — Sprint 3.3: i18n Infrastructure

**Date**: 3 March 2026
**Duration**: ~2 sessions (crashed mid-sprint, resumed)

## What Was Built

Trilingual support (English, Tamil, Malay) for the entire Next.js frontend using next-intl:

- Installed and configured next-intl with App Router integration
- Created middleware for automatic locale detection and redirect
- Moved all 17 page files under `app/[locale]/` directory structure
- Extracted ~162 hardcoded strings from 27 components into `messages/{en,ta,ms}.json`
- Built LanguageSwitcher component (EN | தமிழ் | BM) in Header
- Replaced all `next/link` imports with i18n-aware `@/i18n/navigation` Link (20 files)
- Created Jest mocks for next-intl and i18n navigation
- Added translation completeness tests (all 3 languages must have matching keys)
- Added i18n routing config tests

## Numbers

- **Strings extracted**: ~162 across 10 namespaces (common, header, footer, schoolProfile, schoolMap, constituency, dun, claim, subscribe, parliamentWatch)
- **Files modified**: ~35 (27 components/pages + 8 test/config files)
- **New files**: ~15 (3 message files, 3 i18n config files, 1 middleware, 6 test mocks, 2 i18n tests)
- **Tests**: 852 total (662 backend + 190 frontend). 6 new i18n tests.
- **Commits**: 7 (1 plan, 1 install, 5 extraction batches, 1 test fix + close)

## What Went Well

1. **14-task implementation plan** — detailed plan with exact file lists and code made execution straightforward. Each task was independently committable.
2. **Batched string extraction** — grouping by page/feature area (Header/Footer, school, map, constituency, claim/subscribe) kept context focused and commits reviewable.
3. **Test mocks worked first try** — creating `__mocks__/` files that load real English messages meant existing tests continued to pass without rewriting assertions.
4. **Translation completeness test** — catches missing keys immediately. Will prevent drift as new strings are added.

## What Went Wrong

1. **Session crash** — Claude Code process exited (code 3221226505) while running the full test suite (Task 13). Lost ~5 minutes of context. The crash happened at 100% context usage.
2. **Context pressure** — the 14-task plan with full code snippets consumed significant context. By Task 11 (test updates), context was near limits.
3. **No branch created** — despite the plan calling for risk mitigation via a branch, work was done directly on main. The 5 unpushed commits were at risk during the crash.

## Design Decisions

1. **next-intl over next-i18next**: next-intl has first-class App Router support with RSC integration. next-i18next is designed for Pages Router.
2. **Locale in URL path** (`/en/school/X`) over cookie/header detection: explicit URLs are SEO-friendly, shareable, and cacheable.
3. **Real messages in test mocks** (not key passthrough): loading actual `en.json` in mocks means tests still assert against "School Details" not "schoolDetails". Zero test rewrites needed.
4. **Three languages from day one**: EN (default), TA (community language), MS (national language). Adding a language later just means adding a JSON file + updating routing config.

## Lessons

- At high context usage (>85%), prefer smaller commits and more frequent pushes to avoid data loss on crash.
- When a plan has 14+ tasks, consider splitting into 2 sprints or using a worktree branch for safety.
