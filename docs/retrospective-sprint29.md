# Sprint 29 Retrospective — Security & Dependency Refresh

**Closed**: 2026-06-26
**Wall time**: ~4h end-to-end (audit + sprint together; sprint itself ~2h)
**Scope**: clear the security backlog before v2.0 release. Driven by the 2026-06-26 tech-debt audit doc (first full TD sweep since Sprint 11 prep).

## What Was Built

1. **`SuperuserRequiredMixin`** (`backend/broadcasts/views.py`) — combines `LoginRequiredMixin` + `UserPassesTestMixin` with role-aware `handle_no_permission`: anonymous → 302 to login, authenticated non-superuser → 403. Applied to all 6 broadcast admin views. Replaces undocumented "Google OAuth ≠ Django User row" invariant.
2. **Server-driven ISR revalidation** (`backend/schools/services/revalidation.py` + wiring in 3 view methods) — Django backend POSTs to the Next.js route handler after `serializer.save()`, sends shared secret in `X-Revalidate-Token` header. Frontend route handler validates the header; 401 if wrong, 503 if env unset. Browser-side trigger removed. Python slug builder mirrors `frontend/lib/urls.ts::schoolPath` for parity.
3. **Dependency upgrades** — Django 5.2.11 → 5.2.15, Pillow 11.3.0 → 12.2.0, cryptography 46.0.5 → 49.0.0, lxml 6.0.2 → 6.1.1 (Python side; minimums pinned in `requirements.txt` with CVE rationale). `ws` cleared, `next-intl` 4.9.1 → 4.13.0, `postcss` < 8.5.10 → ≥ 8.5.10 (via npm `overrides`).
4. **Cleanups** — `0013` migration comment explaining the 0013/0014 pair; stale `relabel_labu_mistags` + `migrate_images_to_storage` commands deleted; `broadcast_hero_image_view` comment documenting intentional public exposure.
5. **Audit deliverable** — `docs/tech-debt-audit-2026-06-26.md` (the document that scoped this sprint).

## What Went Well

- **Audit-driven scoping.** Spending ~1h on the TD audit before opening the sprint produced a sharp scope list with severity tagging. Each task came with cost-to-fix in the audit doc; the sprint plan inherited those numbers and the wall-time prediction matched. Compare to "what should we do next sprint?" → "let's pick from a backlog" — that loop produces vaguer plans.
- **Order: cleanups → role gate → deps → revalidate.** Doing TD-22/23/25 (5 min total) first kept the working tree clean and uncluttered for the harder work. TD-20 (role gate) was small and self-contained — quick win to build momentum. Then TD-19 deps (medium-risk, full pytest after) before TD-21 (cross-cutting BE+FE change). Failure in any layer didn't compound into the next.
- **Defense-in-depth correctly distinguished from "broken now"**. The broadcast role gate (TD-20) is currently safe in production — only one Django User row exists, no actual exploit path. Audit could have downgraded to "non-issue". Instead it stayed MEDIUM because the invariant is undocumented and one config change away from breaking. Sprint shipped the proper fix. Important to preserve this lens: don't classify findings on "is it exploited today?" but on "what's the failure mode if a future change drifts?"
- **Backend-driven revalidation pattern.** TD-21's fix replaces a client-side trigger with a backend trigger, which simultaneously (a) closes the abuse vector, (b) removes the "stale browser fails to revalidate" failure mode, (c) makes the revalidation lifecycle co-located with the data change. Two birds one stone.
- **Live smoke tests caught nothing** — confirmation that the local pytest + npm test rigor was sufficient. 401-without-token, 401-with-wrong-token, 200-with-correct-token, public page still serves: all expected on first try. No deploy ping-pong.

## What Went Wrong

- **`LoginRequiredMixin` + `raise_exception=True` was too blunt — 403'd anonymous users instead of redirecting them.** First implementation of `SuperuserRequiredMixin` set `raise_exception = True`, expecting it to only affect the `test_func()` failure path. Reality: `raise_exception` is read by `LoginRequiredMixin`'s `handle_no_permission` too, so anonymous users started getting 403 instead of the 302-to-login. Caught by the first pytest run (`test_requires_login` failed). **Root cause**: assumed Django mixin attributes had narrow scope without reading the source. **System change**: when combining auth mixins, override `handle_no_permission()` explicitly with an `is_authenticated` check rather than relying on `raise_exception` to do the right thing. Captured in the mixin docstring.
- **Forgot to update a sibling test file's fixture.** TD-20 promoted the `user` fixture in `broadcasts/tests/test_views.py` to superuser — but didn't notice `broadcasts/tests/test_send_views.py` had its own copy of the fixture. 7 tests failed in the full pytest run. Fixed in 30 seconds. **Root cause**: didn't grep for fixture duplication before editing. **System change**: when changing a fixture that controls auth/permissions, grep for the fixture name across all test files before declaring done. Worth a lesson.
- **gcloud auth expired non-interactively during TD-24.** Tried to pull the egress dashboard from inside the sprint to close TD-06's missed checkpoint. Couldn't — gcloud needed re-login, session was non-interactive. Documented as 1-line user follow-up. **Root cause**: not a new lesson per se (we already know gcloud auth times out), but a confirmation that any sprint that *plans* to do a GCP-console pull needs that to be a user-side step from the start, not an "I'll do it during the sprint" assumption. Adjusted TD-24 entry to make it explicit.
- **TD-19 audit overstated Python CVE count for THIS project.** Initial audit cited 103 CVEs across 17 packages. After `pip show` inspection, ~half of those packages (pyjwt, pypdf, etc.) turned out to be installed in the local venv via OTHER local projects (HalaTuju supabase-auth → pyjwt; some-other-project xhtml2pdf → pypdf), not this project's deps. The real direct/transitive set was 5 packages. **Root cause**: `pip-audit` runs against the active venv, not against `requirements.txt`. Without a clean venv check (or `pip-audit -r requirements.txt`), shared workstation venvs inflate the count. **System change**: when running `pip-audit` for a single-project audit, either use `-r requirements.txt` or run inside a project-specific venv. Captured.

## Design Decisions

(Full entries in `docs/decisions.md`.)

1. **`SuperuserRequiredMixin` as inline class, not a project-wide helper.** Could have put it in `core/permissions.py` for reuse across apps. Chose inline-in-`broadcasts/views.py` because (a) it's the only app that needs this exact gate today, (b) `community/` already has its own permission helpers, (c) premature abstraction across 3 apps that share no other code is wrong. If a second app needs the same gate, *then* extract.
2. **Backend-driven revalidation with shared secret over per-request signed token.** Considered: (a) HMAC-signed payload (caller signs request body with shared secret); (b) JWT-like time-limited token; (c) plain shared secret in header. Chose (c) for simplicity — same security posture (anyone with the secret can revalidate, no one without it can), zero crypto complexity, easy to rotate. The threat model is "DoS amplification" — replay protection isn't material.
3. **Stayed on Django 5.2 LTS rather than jumping to 6.0.** Both satisfy the CVE list. 5.2.15 is one minor patch up from 5.2.11 (zero migration risk). 6.0 is a full major (some deprecations, breaks 3rd-party plugins). Sprint goal was a surgical security fix; chose minimal change. Reconsider at v2.0+1 (next major release window).
4. **Accepted 19 moderate npm vulns deferred (jest test-chain).** All in `@jest/transform`, `babel-plugin-istanbul`, `@istanbuljs/load-nyc-config` etc. — dev-only, never bundled. The "fix" auto-recommended is a SemVer-major jest regression (29 → 25) which is *worse* than the moderate finding. Stays deferred until the jest team ships an in-major fix.
5. **`npm overrides` block over forking next.** Postcss XSS chains through `next/node_modules/postcss`. Next hasn't released a patched version pinning postcss 8.5.10+. Could have downgraded next to 9 (auto-fix recommendation) — that's a 7-major-version regression. `overrides: { "postcss": "^8.5.10" }` forces the transitive resolution without touching next. Clean.

## Numbers

| Metric | Sprint 28.1 close | Sprint 29 close | Delta |
|---|---|---|---|
| Backend tests | 1424 | **1436** | +12 (TD-20 role gate ×6, TD-21 revalidation ×6) |
| Frontend tests | 367 | **367** | 0 (removed 2 mock-references, no new cases — the rest are mock plumbing) |
| Python deps with known CVEs | 5 direct | **0 direct** | -5 |
| npm vulns | 28 (3 high, 22 mod, 3 low) | **19** (all moderate, jest dev-chain) | -9, -3 high, -3 low |
| api revisions | 00133-2cf | **00135-kxm** | +2 (env-var + code) |
| web revisions | 00125-9jl | **00127-vhh** | +2 (env-var + code) |
| Jobs synced | 7/7 | 7/7 | (re-synced after api code deploy) |
| Files touched | — | 27 (incl. 3 deletes) | within the 40-cap |
| Wall time (sprint only) | ~3h | ~2h | (audit prep took the difference) |

### Audit findings delta

| ID | Severity | Closed in Sprint 29? |
|---|---|---|
| TD-19 (Python+npm CVE backlog) | 🔴 high | ✅ |
| TD-20 (broadcast role gate) | 🟡 medium | ✅ |
| TD-21 (revalidate auth) | 🟡 medium | ✅ |
| TD-22 (migration pair comment) | 🟢 low | ✅ |
| TD-23 (stale commands) | 🟢 low | ✅ |
| TD-24 (egress checkpoint) | 🟢 low | ⏳ documented as user-side 1-line follow-up |
| TD-25 (hero-image endpoint comment) | 🟢 low | ✅ |
| TD-12 (hansard extractor coverage) | 🟢 low | ⏳ no change — `pypdf` is NOT a direct dep of this project (was a local-venv-shared-with-other-project false flag); urgency reason doesn't apply |

## Operational state

- **Prod api**: `sjktconnect-api-00135-kxm` (Sprint 29 — SuperuserRequiredMixin + backend revalidation + Django 5.2.15 / Pillow 12.2 / cryptography 49 / lxml 6.1)
- **Prod web**: `sjktconnect-web-00127-vhh` (Sprint 29 — token-gated revalidate route + browser-side trigger removed + next-intl 4.13 + postcss override)
- **Env vars set on both Cloud Run services**: `REVALIDATE_TOKEN=<opaque>` (matching). api also has `REVALIDATE_WEBHOOK_URL=https://tamilschool.org/api/revalidate`.
- **Jobs**: 7/7 synced to api-00135-kxm.
- **Smoke**: 4/4 post-deploy curl checks green (401-without, 401-wrong, 200-correct, school-page-still-serves).

## Pending follow-ups (out of sprint scope)

- **TD-24 (egress dashboard pull)** — user to visit `console.cloud.google.com/monitoring/dashboards/builder/f1722366-2df9-4446-9941-7cda5c019615?project=sjktconnect`, record last-7-day MB/day. Flip TD-06 to ✅ if <150 MB/day; pull Task #43 otherwise.
- **19 jest dev-chain vulns** — wait for upstream patch.
- **TD-12 (hansard extractor coverage)** — leave deferred per decisions.md.

## What I'd do differently

- **At audit time, run `pip-audit -r requirements.txt` (or in a clean venv) rather than against the active workstation venv.** Would have surfaced the real 5-package CVE list immediately, not the inflated 17-package one. The TD-19 estimate was right-sized in the end (the false-flag packages were correctly excluded), but the initial framing was misleading.
- **Before promoting a fixture, grep for its name across all test files in the same app.** Saves the 7-test re-run cycle.
- **Default `raise_exception = True` is a trap when combining `LoginRequiredMixin` + `UserPassesTestMixin`.** Always override `handle_no_permission()` explicitly when both mixins are present. Now in lessons.md.
