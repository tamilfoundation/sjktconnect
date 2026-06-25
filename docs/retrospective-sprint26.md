# Sprint 26 Retrospective — School Page UX Pass

**Closed**: 2026-06-26
**Wall time**: ~1.5 hours from kickoff to tests passing. 6 owner-reported bugs, ~13 files.
**Scope**: 6 concrete UX issues — 3 frontend-only, 3 with backend mirror.

## What Was Built

1. **#4 — Map state-filter crash fix** — `Number()` coercion + finite-number guard in `FitBoundsOnStateFilter`. DRF serialises `DecimalField` as string; my Sprint 24 code passed them raw to `bounds.extend()` which Google Maps rejects. Discovered the server returned 200 on every state-filter URL, so the crash was browser-side after hydration — not catchable by my deploy-time `curl` smoke.

2. **#3 — Tamil name de-duplication** — removed the row from `SchoolProfile.tsx`. The hero rendering in the page wrapper already shows the Tamil name; the second copy in the details box was Sprint-19 leftover. Single deletion + one test flip.

3. **#2 — `SelectField` + Session Type dropdown** — new constrained-select component in `FieldRow.tsx`, applied in `CoreTab.tsx`. MOE only ever publishes `Pagi Sahaja` or `Pagi dan Petang`; the free-text input was letting admins type "AM" / "Morning" / "Pagi" and breaking the `session_${value}` i18n lookup downstream. Server-side validator (`SchoolEditSerializer.validate_session_type`) enforces the same enum so `curl` users can't bypass.

4. **#6 — `firstPhoneForTelUri()` helper** — splits multi-number values on `/`, `,`, `;` and trims. Applied to MP card; the `tel:` link now contains a single phone. Visual separators (`-`, space) preserved so the value the user sees on tap matches the value they read.

5. **#5 — `isUsableMpFacebookUrl()` frontend guard + `is_generic_facebook_url()` scraper drop** — two-layer fix. Frontend hides the Facebook button when the URL matches `ParlimenMY` / `parlimenmalaysia` / `parliament` / `parlimen` slugs or is a bare-root URL; backend scraper drops the same shapes at parse time so future `import_mp_profiles` runs don't add new bad rows. Existing bad rows in DB are harmless because the frontend hides them.

6. **#1 — Phone + email validation across edit forms** —
   - `frontend/lib/validation.ts` with `isValidPhone()`, `isValidEmail()`, error helpers, exported regex constants.
   - `EditableField` extended with `error`, `pattern`, `patternTitle` props — inline red-border styling + `aria-describedby` error message + browser-native `pattern` validation on form submit.
   - `LeadersTab` refuses to flush a Save when any visible slot has invalid phone or email.
   - Server-side mirror in `SchoolEditSerializer.validate_phone` / `validate_fax` and `SchoolLeaderAdminSerializer.validate_phone`.
   - 3-locale i18n added.

## What Went Well

- **Symptom enumeration up-front saved a lot of guessing.** Owner sent 6 screenshots; each pointed at a specific file in a specific component. Compare to a "code-review pass" which would have found theoretical issues and probably missed #4 and #5 entirely (both required reproduction against live data).
- **Two-layer fix for #5** — hiding the bad URL in the frontend AND dropping it at scrape time. The frontend guard works against existing bad rows; the scraper guard prevents future regressions. Either layer alone is incomplete.
- **Helper extraction kept tests honest.** `firstPhoneForTelUri` + `isUsableMpFacebookUrl` are pure functions exported alongside `ContactMPCard`, so 8 of the 13 new tests in that file are direct unit tests without any React rendering. The component tests then verify the wiring.
- **Server-side validation mirrored every frontend rule.** Pattern lessons.md captures: "frontend validation is UX; server validation is the safety net." Both layers ship together — no curl-bypass holes.

## What Went Wrong

- **#4 was a regression from my own Sprint 24 work.** I added `FitBoundsOnStateFilter` for the state-filter bug fix held with "deploy when convenient" — and shipped it without testing it against live data. My deploy-time smoke test was `curl https://tamilschool.org/en?state=Perak → 200` which only checks server-side render. **Root cause**: I treated "server returns 200" as sufficient evidence the page works, despite the fix being a client-side feature.
  - **Fix**: deploy verification for any client-side feature MUST include opening the deployed URL in a browser and checking the DevTools console for runtime errors. `curl` is a necessary but not sufficient signal. Added to lessons.md.
- **DRF DecimalField → string is a recurring trap** — I knew `SchoolMarkers.tsx:113` does `Number(school.gps_lat)` because I'd grepped for that pattern at Sprint 24 review, but didn't apply the same coercion to the new code I added. The lesson "when extending a matcher, audit shared-state lookups before adding strategies" (Sprint 24) generalises: when extending any component that consumes API field X, audit how OTHER consumers of X type-coerce before writing the new consumer.
- **Tests for the bug fixes I held from Sprint 24 close (`SchoolMap.test.tsx`) didn't catch #4** because the test imports `filterByStateParam` (a pure function) but the crash was in `FitBoundsOnStateFilter` (a React component that uses Google Maps). The component is hard to test without mocking the Maps SDK; I'd punted on it at Sprint 24. **Fix**: when a component is "too hard to test", that's a signal to refactor — extract the bounds-build logic into a pure helper that CAN be unit-tested. Recorded as a low-priority follow-up; the Sprint 26 fix alone is enough to close the immediate bug.

## Design Decisions

(See `docs/decisions.md` for the new entries.)

1. **`tel:` link strategy: split on separators, preserve visual chars** — RFC 3966 allows `-` and space as visual separators, every dialer handles them, and the value-on-tap matches value-shown.
2. **Frontend + backend validation are BOTH required, not either-or** — codified in Sprint 26's pattern. Frontend = UX; backend = safety net.
3. **Generic-FB-URL filter at scrape time, NOT just at display time** — the display-time guard is the immediate fix, but data quality at write time is the better long-term invariant. Both ship together.

## Numbers

| Metric | Sprint 25 close | Sprint 26 close | Delta |
|---|---|---|---|
| Backend tests | 1406 | **1417** | +11 |
| Frontend tests | 328 | **349** | +21 |
| Files touched | — | 13 | — |
| Wall time | — | ~1.5h | — |

## Operational follow-ups

- **Post-deploy verification**: open `/en?state=Selangor` in browser, check DevTools console for runtime errors. Open one school's edit page (Contact tab + Leaders tab), type invalid phone, confirm red border + error message. Open a constituency page with a multi-number MP phone, confirm `tel:` link is single number.
- **Low-priority cleanup**: one-off SQL to clear `MP.facebook_url` rows matching generic shapes — frontend already hides them so users don't see, but the data is stale. Defer until next MP-area sprint.
- **Refactor follow-up**: extract `FitBoundsOnStateFilter`'s coord-build logic into a pure helper so it can be unit-tested without mocking Google Maps SDK. Logged as test-coverage debt, not currently in `tech-debt.md` because the path itself works now.

## What I'd do differently

- **Run a 5-minute browser smoke before declaring a client-side fix shipped.** My Sprint 24 close declared the state-filter "deployed" based on a curl 200; the user found the actual breakage in #4 here. Cost: one extra deploy cycle today. The fix: a standing checkbox on any FE-touching sprint's deploy step ("open the deployed URL in a browser, scan console, take screenshot if non-trivial UI"). Added to lessons.md.
