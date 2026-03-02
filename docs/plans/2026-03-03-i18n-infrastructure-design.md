# Design: i18n Infrastructure (Sprint 3.3)

**Date**: 3 March 2026
**Status**: Approved
**Sprint**: 3.3
**Approach**: next-intl with Next.js 14 App Router

---

## Overview

Add trilingual support (English, Tamil, Malay) to the SJK(T) Connect frontend. All UI strings become translatable. URLs gain a locale prefix (`/en/`, `/ta/`, `/ms/`). A language switcher lets users change locale.

Backend (Django) stays English-only. School names, constituency names, and API data remain untranslated (they are official names in Malay/English).

---

## Architecture

### Library

`next-intl` — the standard i18n library for Next.js App Router. Handles locale routing, message loading, SSR/ISR, and provides `useTranslations()` hook for components.

### Locales

| Code | Language | Label in switcher |
|------|----------|-------------------|
| `en` | English (default) | EN |
| `ta` | Tamil | தமிழ் |
| `ms` | Malay | BM |

### URL Structure

- `/` → redirects to `/en/`
- `/en/school/ABC1234` → English school page
- `/ta/school/ABC1234` → Tamil school page
- `/ms/school/ABC1234` → Malay school page

Old URLs (`/school/X`, `/constituencies/`) automatically redirect to `/en/school/X`, `/en/constituencies/` via next-intl middleware (307 redirect — preserves SEO while search engines update).

### Folder Restructure

All 17 page files move from `app/` into `app/[locale]/`:

```
frontend/
  app/
    [locale]/
      layout.tsx          # Root layout (receives locale param, sets <html lang>)
      page.tsx            # Home/map
      school/[moe_code]/
        page.tsx
        edit/page.tsx
        loading.tsx
        not-found.tsx
      constituencies/page.tsx
      constituency/[code]/
        page.tsx
        loading.tsx
      dun/[id]/
        page.tsx
        loading.tsx
      parliament-watch/page.tsx
      claim/page.tsx
      claim/verify/[token]/page.tsx
      subscribe/page.tsx
      unsubscribe/[token]/page.tsx
      preferences/[token]/page.tsx
    globals.css           # Stays at app level
  i18n/
    routing.ts            # Locale list + default locale config
    request.ts            # Loads correct messages/{locale}.json per request
  middleware.ts           # Locale detection + redirect
  messages/
    en.json               # English strings (~155 keys)
    ta.json               # Tamil strings (~155 keys)
    ms.json               # Malay strings (~155 keys)
```

### New Files

| File | Purpose |
|------|---------|
| `i18n/routing.ts` | Defines locales array, default locale, pathnames |
| `i18n/request.ts` | `getRequestConfig` — loads messages JSON for current locale |
| `middleware.ts` | Detects locale from URL, redirects if missing |
| `messages/en.json` | English translation strings |
| `messages/ta.json` | Tamil translation strings |
| `messages/ms.json` | Malay translation strings |

### next.config.js Change

Wrap existing config with `createNextIntlPlugin()`:

```js
const createNextIntlPlugin = require('next-intl/plugin');
const withNextIntl = createNextIntlPlugin();

const nextConfig = {
  output: "standalone",
};

module.exports = withNextIntl(nextConfig);
```

---

## Message Structure

Three JSON files with identical keys, organised by component namespace:

| Namespace | Covers | Est. strings |
|-----------|--------|-------------|
| `header` | Nav links, site title | 5 |
| `home` | Map page title, search placeholder, filters | 10 |
| `schoolProfile` | School detail page labels, stat cards, leadership, enrolment | 35 |
| `constituency` | Constituency/DUN page labels, scorecard, demographics | 20 |
| `parliamentWatch` | Parliament watch page | 10 |
| `subscribe` | Subscribe/unsubscribe/preferences pages | 15 |
| `claim` | Claim flow pages | 10 |
| `schoolEdit` | Edit form labels | 15 |
| `common` | Shared: "Loading...", "Back", "Search", "No results", footer text | 20 |
| `metadata` | Page titles + descriptions for SEO | 15 |

**Total**: ~155 strings x 3 languages = ~465 translation entries.

### What stays English (untranslated)

- School names (official MOE names in Malay)
- Constituency/DUN names (official names)
- API data (addresses, phone numbers)
- Backend / Django admin

---

## Language Switcher

Inline text links in the Header, right side of nav bar:

- **Desktop**: `EN | தமிழ் | BM` — active locale bold/underlined
- **Mobile**: Same row in the mobile menu dropdown
- Clicking navigates to the same page in the target locale (e.g. `/en/school/X` → `/ta/school/X`)
- Uses next-intl's `usePathname()` + `Link` with locale param

---

## Migration & Redirects

- Old URLs automatically redirect to `/en/...` via next-intl middleware (307)
- ISR continues to work — each `[locale]/school/[moe_code]` generates a separate static page
- Google-indexed URLs get temporary redirect, preserving SEO while search engines update

---

## Testing

- Update existing ~184 frontend tests for `[locale]` route structure
- New tests:
  - Middleware redirects (no locale → `/en/`)
  - Language switcher navigation
  - Translation rendering (Tamil/Malay strings appear when locale changes)
  - SEO metadata per locale

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Moving 17 page files breaks imports | High | Mechanical move, test after each batch |
| Existing tests break from route changes | Medium | Update test routing mocks in one pass |
| Tamil/Malay translations have errors | Low | Tamil follows style guide; Malay reviewed later |
| ISR cache invalidation with locales | Low | next-intl handles natively |
| Malay translations delay sprint | Medium | Ship EN + TA complete, MS best-effort |

---

## Dependencies

- `next-intl` (npm package)
- No backend changes required
- No database changes
- Frontend-only deploy
