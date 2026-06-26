# SJK(T) Connect — Tech Debt Audit (2026-06-26)

**Trigger**: pre-release sweep. Last full audit ran 2026-04-22 (Sprint 11 prep). The interim TD register (`docs/tech-debt.md`) has been triaged each sprint, but every sprint from 19 → 28.1 was logged as "no TDs touched" with no inspection. Sprints 19–28.1 shipped substantial new surface area (leader CRUD, egress hardening v2, alias bridge, monthly digest v2, SEO slugs, ISR revalidation route, broadcast send-test admin, GPS edit pipeline, phone normalisation). This audit verifies the "no TDs touched" claim mechanically.

**Scope**: dependency CVEs, security spot-check, code-level smell sweep, verification of supposedly-resolved TD items, dead-code candidates.

**Owner**: tamiliam · **Audit completed by**: Claude Code (Opus 4.7) · **Files referenced**: `[docs/tech-debt.md](tech-debt.md)`, `[backend/broadcasts/views.py](../backend/broadcasts/views.py)`, `[backend/broadcasts/urls.py](../backend/broadcasts/urls.py)`, `[frontend/app/api/revalidate/route.ts](../frontend/app/api/revalidate/route.ts)`, `[backend/schools/migrations/0013_normalise_leader_phones.py](../backend/schools/migrations/0013_normalise_leader_phones.py)`.

---

## Executive summary

7 new TD items surfaced. None are currently exploited, but two carry meaningful exposure once the project moves to `Production/` and gets the v2.0 release narrative around it.

| Item | Severity | Type | Blocks v2.0 release? |
|---|---|---|---|
| **TD-19** Dependency CVE backlog (Python: 103 CVEs across 17 packages; npm: 28 vulns / 3 high) | 🔴 high | security | **YES — should ship before release** |
| **TD-20** Broadcast admin views rely on undocumented invariant for role gating | 🟡 medium | defense-in-depth | Recommended before release |
| **TD-21** `/api/revalidate` Next.js route unauthenticated — DoS amplifier (528 × 3 locales) | 🟡 medium | abuse-vector | Recommended before release |
| **TD-22** Migrations 0013 + 0014 (leader phones) — pair effect, but 0014 is now no-op on fresh installs | 🟢 low | bookkeeping | No |
| **TD-23** Stale one-off management commands not deleted (`relabel_labu_mistags`, `migrate_images_to_storage`) | 🟢 low | cleanup | No |
| **TD-24** TD-06 egress checkpoint (2026-05-08) was never recorded as performed | 🟢 low | governance | No |
| **TD-25** `broadcast_hero_image_view` returns DB bytes with no auth + sequential pk enumeration | 🟢 low | minor info-disclosure | No |

Plus 1 prior open item (TD-12) still parked.

**Pre-release recommendation**: address TD-19 in a focused sprint (Sprint 29 candidate); resolve TD-20 + TD-21 alongside as 1-file fixes; defer the rest to backlog. Then proceed with SEO sprint, then v2.0 release + folder move.

---

## Methodology

1. Read the TD register (TD-01 → TD-18) and CHANGELOG.md (Sprints 19 → 28.1).
2. Ran `npm audit` on `frontend/` and `pip-audit` + `pip list --outdated` on `backend/`.
3. Grepped for `TODO|FIXME|XXX|HACK|TEMP:|TEMPORARY` across both stacks — surfaced almost nothing (a sign of healthy ongoing hygiene).
4. Reviewed code added in Sprints 25, 27, 28, 28.1 (the largest new surfaces):
   - `[backend/broadcasts/views.py](../backend/broadcasts/views.py)` — send-test admin endpoint
   - `[backend/broadcasts/urls.py](../backend/broadcasts/urls.py)` — mount + hero-image view
   - `[frontend/app/api/revalidate/route.ts](../frontend/app/api/revalidate/route.ts)` — ISR busting
   - `[backend/schools/migrations/0013_normalise_leader_phones.py](../backend/schools/migrations/0013_normalise_leader_phones.py)` + `0014` — pair
5. Verified the architectural invariant the broadcast views rely on (Google OAuth ≠ Django User row) by tracing `accounts/api/views.py:183` (`session["user_profile_id"]`, not `auth.login()`).
6. Spot-checked supposedly-resolved TD items via the live register text vs current code.

---

## New findings — detail

### 🔴 TD-19 — Dependency CVE backlog

**What** (Python — `pip-audit`):
- **103 known vulnerabilities across 17 packages**. Highlights:
  - **Django 5.2.11** — 16 CVEs across PYSEC-2026-48/49/50/51/52/53/54/55/197/198/199/200/201 + CVE-2026-25673/25674. Fix: 5.2.15 (latest 5.2.x patch) or 6.0.6 (LTS path).
  - **pyjwt 2.11.0** — 10 CVEs. Fix: 2.13.0. Critical because PyJWT validates OAuth ID tokens in `accounts/services/google.py`.
  - **pypdf 5.9.0** — 17 CVEs. Fix: 6.10.0. Used by `hansard/pipeline/extractor.py` (PDF parsing of Hansard documents — directly accepts untrusted external PDFs).
  - **pillow 11.3.0** — 7 CVEs including CVE-2026-25990 / 40192 / 42309-11. Fix: 12.2.0. Used in `outreach/services/image_processor.py` for community photo uploads — directly exposed.
  - **cryptography 46.0.5** — 5 CVEs. Fix: 46.0.7 (or 48.0.1 for full set).
  - Smaller: lxml, msgpack, idna, pyasn1, pygments, django-allauth.

**What** (npm — `npm audit`):
- **28 vulnerabilities (3 high / 22 moderate / 3 low)**. Highlights:
  - **ws 8.0.0–8.20.1** (high) — uninitialised memory disclosure (GHSA-58qx-3vcg-4xpx) + memory exhaustion DoS (GHSA-96hv-2xvq-fx4p).
  - **next-intl ≤ 4.9.1** (moderate) — prototype pollution via translation catalog keys. Catalogs are checked-in JSON in our case (low real exposure), but trivial to fix.
  - **postcss < 8.5.10** (moderate) — XSS via unescaped `</style>` in CSS Stringify Output.
  - **@babel/core ≤ 7.29.0** (low) — file read via sourceMappingURL.
  - Jest / ts-jest transitive chain (test-only, low priority).

**Why we accepted this**: organic drift since Sprint 16's `npm audit fix` (2026-04-27) and Sprint 11a's `pip install -U` round. Two months of pinned dependencies in a security-active ecosystem.

**What it blocks**: shipping v2.0 with a clean security narrative. PyJWT + Pillow + pypdf are all on the data-ingest path for OAuth, community uploads, and Hansard PDFs respectively — each accepts untrusted external input, which is exactly where CVE-bearing parsers bite.

**Cost to fix**: 1 focused sprint. Mostly mechanical:
1. `pip install -U django pyjwt pypdf pillow cryptography lxml msgpack idna pyasn1 pygments django-allauth` + run pytest, fix any breakage.
2. `cd frontend && npm audit fix` for the auto-fixable subset; review the breaking-change ones (jest 25 SemVer-major fix is probably skippable as test-only).
3. Re-run `pip-audit` and `npm audit` to confirm.
4. Smoke-test critical paths: OAuth sign-in, community image upload, hansard PDF ingest, monthly blast composition.

**Approach gotchas**:
- Django 5.2.15 (patch within 5.2.x line) is safer than jumping to 6.0.6 (major upgrade). Stay on 5.2 unless we want to spend the upgrade time.
- pypdf 5.9 → 6.x is a major version. The Hansard extractor path tests will tell us if anything broke (TD-12 still at 26% coverage — be cautious).
- next-intl already past the vulnerable range in latest 4.x; trivial bump.

---

### 🟡 TD-20 — Broadcast admin views rely on undocumented architectural invariant for role gating

**What**: `BroadcastListView`, `BroadcastComposeView`, `BroadcastPreviewView`, `BroadcastSendView`, `BroadcastSendTestView`, `BroadcastDetailView` ([backend/broadcasts/views.py:19-251](../backend/broadcasts/views.py#L19-L251)) all use only `LoginRequiredMixin` — no role check.

In production this is **currently safe** because:
- The only path that creates a Django `User` row is `manage.py createsuperuser`. The single Django user is `admin@tamilfoundation.org`.
- Google OAuth (`accounts/api/views.py:183`) writes `request.session["user_profile_id"]` directly. It does **not** call `django.contrib.auth.login()`. So OAuth users have `request.user == AnonymousUser` and `LoginRequiredMixin` blocks them.

**Why this is debt**: the invariant "Google OAuth never creates a Django User row" is undocumented and not enforced by tests. If a future change introduces `django-allauth` Google flow (which DOES create User rows), or if someone runs `createsuperuser` for a second admin, the broadcast views silently become accessible. The blast radius is large:
- Send any DRAFT broadcast to all ~519 subscribers (`POST /broadcast/send/<pk>/`)
- Send to 5 arbitrary emails per request, bypassing Brevo quota (`POST /broadcast/send-test/<pk>/`) — spam relay
- Enumerate broadcast contents + subscriber email addresses (`GET /broadcast/<pk>/`)

**What it blocks**: nothing immediately. But "production-ready" should mean defense-in-depth, not "safe-by-architectural-coincidence."

**Cost to fix**: 1 hour. Add an `IsSuperAdminUser` mixin that checks `request.user.is_authenticated and request.user.is_superuser`, apply to all 6 views. Update test_views.py to verify a regular `User` (`is_superuser=False`) is 403'd. 0 production behaviour change.

---

### 🟡 TD-21 — `/api/revalidate` Next.js route unauthenticated — DoS amplifier

**What**: [frontend/app/api/revalidate/route.ts](../frontend/app/api/revalidate/route.ts) POST endpoint accepts `{type: "school", key: "ABC1234", slug?: "..."}` and calls `revalidatePath()` for 6 paths (3 locales × bare-code-URL × slug-URL) per request. No auth. Validates `key` and `slug` regex shapes only.

The docstring's reasoning ("worst a malicious caller can do is flush the cache for the school detail segment, which is the same as a normal ISR miss") is correct for **single-shot** abuse. But:
- A scripted attacker hitting this 10 req/s with a rotating valid `key` triggers **10 × 6 = 60 ISR regenerations/s** — each regeneration runs the full SchoolDetailPage component, which fetches from the Django API, which queries Supabase.
- This project has **two prior egress incidents** (Sprint 17, Sprint 21) where Supabase egress climbed past free-tier limits from very modest unintended request volumes.
- An unauthenticated, scriptable cache-bust amplifier is exactly the kind of vector that recreates those incidents.

**Why we accepted**: the original Sprint 27 design was "client-side trigger from the edit form" and authentication felt heavyweight. Sprint 28's slug fix didn't revisit auth.

**What it blocks**: confidence in production stability under low-effort hostile traffic. Cloudflare WAF would mitigate but isn't currently configured for this path.

**Cost to fix**: 30 minutes. Two options:
- **A) Move trigger backend-side** (recommended): Django serializer's `.save()` calls a backend webhook to `https://tamilschool.org/api/revalidate` with a shared-secret header (`X-Revalidate-Token` env var). Route handler checks the header. Browser-side code stops calling this endpoint.
- **B) Add shared-secret header check** in route.ts, generate the secret via a Next server action that the edit form calls. More plumbing, same security posture.

A) is cleaner and removes the failure mode where a stale browser fails to revalidate.

---

### 🟢 TD-22 — Migrations `0013` + `0014` are a pair; 0014 is now a no-op on fresh installs

**What**: Sprint 28.1 shipped `schools/0013_normalise_leader_phones.py`, which ran with a broken `format_phone()` (missing mobile prefixes 010-019). After fixing `format_phone()`, Sprint 28.1 shipped `schools/0014_normalise_leader_phones_with_mobile.py` to re-run.

On a fresh install today: utils.py is correct, 0013 runs first and normalises everything correctly, 0014 then runs and finds nothing left to do.

**Why this is debt**: someone reading the migration tree in 6 months won't know why two near-identical migrations exist back-to-back. The README of 0014 would explain it, but the operational reality has changed.

**Cost to fix**: 5 minutes. Either: (a) add a single-line comment to 0013 ("ran in prod with broken format_phone; 0014 re-runs after fix"); (b) collapse to a single migration before v2.0 tag (only safe because the migration is idempotent and reversible). (a) is the safer pick.

---

### 🟢 TD-23 — Stale one-off management commands not deleted

**What**: 
- `[backend/newswatch/management/commands/relabel_labu_mistags.py](../backend/newswatch/management/commands/relabel_labu_mistags.py)` — added Sprint 28.1 as a targeted one-off cleanup (7 articles). Ran on prod 2026-06-26. Per workspace cleanup rule ("delete one-off helpers after they run") it should now be removed.
- `[backend/outreach/management/commands/migrate_images_to_storage.py](../backend/outreach/management/commands/migrate_images_to_storage.py)` — Sprint 13 one-off (2026-04-26). 1534/1534 images migrated. Still present 2 months later with its test file (`test_migrate_command.py`).

**Why this is debt**: code clutter that makes future audits longer; future readers ask "do I need to run this?" The answer is no, but the artifact stays.

**Cost to fix**: 10 minutes. Delete the two .py files + the test file. Reference the historical retrospective for context.

---

### 🟢 TD-24 — TD-06 egress checkpoint was scheduled for 2026-05-08; never recorded

**What**: TD-06 in [docs/tech-debt.md:34-37](tech-debt.md#L34-L37) says: *"single dated checkpoint on 2026-05-08 — review the preceding 7 days on Cloud Monitoring dashboard... If <150 MB/day for 7 consecutive days, flip to ✅ RESOLVED."*

That date is 7 weeks past. There is no entry in `docs/lessons.md`, no CHANGELOG line, no retrospective marking the checkpoint as performed. The TD register still says "PROVISIONALLY RESOLVED."

**Why this is debt**: governance smell. Either the egress is fine (good — flip to ✅ RESOLVED) or it isn't (bad — pull Task #43 into a sprint). The current "we forgot to check" state hides which.

**Cost to fix**: 30 minutes. Pull Cloud Monitoring dashboard `f1722366-2df9-4446-9941-7cda5c019615` for the last 7 days. Update TD-06 entry with the actual numbers + outcome.

---

### 🟢 TD-25 — `broadcast_hero_image_view` returns DB bytes with no auth + sequential pk enumeration

**What**: [backend/broadcasts/urls.py:16-24](../backend/broadcasts/urls.py#L16-L24) — function-based view at `/api/v1/broadcasts/<int:pk>/hero-image/` returns `bytes(broadcast.hero_image)` with `content_type="image/png"`. No auth, sequential integer pk.

**Why this is low**: hero images are intentionally public-facing (embedded in marketing emails). The content is non-sensitive. The pk enumeration leaks the COUNT of broadcasts and lets you GET each image, but not the broadcast metadata (subject, recipient list, etc.).

**Why it's still debt**: pattern violation. Other "return DB bytes by sequential pk" endpoints would not be acceptable; this one is by virtue of content type. Worth a comment in the code, or wrap behind a hash-based URL like the Supabase Storage URLs.

**Cost to fix**: 1 hour if you want to migrate to Supabase Storage (consistent with how community/school images already work). 5 minutes for a code comment explaining the deliberate exposure.

---

## Verification of prior TD items (TD-01 → TD-18)

Spot-checked, no regressions surfaced.

| Item | Claim | Verified? | Notes |
|---|---|---|---|
| TD-01 — OAuth checks restored | ✅ Resolved Sprint 16 | ✅ `frontend/lib/auth.ts` still has `__Secure-` prefix + `checks: ["pkce", "state"]` | No regression. |
| TD-02 — Magic-link removed | ✅ Resolved 2026-04-24 | ✅ `grep MagicLinkToken backend/` returns nothing | No regression. |
| TD-03 — DATABASE_URL guard | ✅ Resolved 2026-04-23 | Owner-confirmed pattern still in place (used during Sprint 24 prod migrations) | No regression. |
| TD-04 — SameSite=None workaround | ✅ Resolved Sprint 11 | Cookies work cross-subdomain; verified Sprint 28.1 sign-in cycle | No regression. |
| TD-05 — School images on Supabase Storage | ✅ Resolved Sprint 13 | 1534/1534 reported migrated | No regression. |
| TD-06 — Egress regression | ⏳ "Provisionally resolved", checkpoint 2026-05-08 | **❓ Checkpoint not recorded** — see TD-24 above. | Surfaced as new item. |
| TD-07/09 — Suggestion BinaryField + endpoint | ✅ Resolved Sprint 14 | No `BinaryField` in `community/models.py`; endpoint absent. | No regression. |
| TD-08 — DRF auth classes pinned | ✅ Resolved 2026-04-23 | `backend/sjktconnect/settings/base.py` still has `DEFAULT_AUTHENTICATION_CLASSES` pin | No regression. |
| TD-10 — Next.js upgrade | ✅ Resolved Sprint 16 | Still on Next 16.x — but the `next-intl ≤ 4.9.1` vuln (TD-19) is new since then. | No regression in upgrade; new transitive CVE. |
| TD-11 — google.py coverage | ✅ Resolved Sprint 18 | Tests present and passing per Sprint 28.1 close (1424 passing) | No regression. |
| 🟢 **TD-12 — hansard extractor 26% coverage** | Still open, deferred | Confirmed open. No new test coverage added in Sprints 19–28.1. | **Still 🟢 low** — but moved up in priority because pypdf upgrade (TD-19) will exercise this code path. |
| TD-13 — `uploaded_by` nullable on SchoolImage | ✅ Resolved (no-op) Sprint 13 | n/a | No regression. |
| TD-14 — Role checks consolidated | ✅ Resolved Sprint 16 | Helper present | No regression. |
| TD-15 — FE test flakes | ✅ Resolved Sprint 16 | 367/367 passing per Sprint 28.1 close | No regression. |
| TD-16 — Dashboard chrome leak | ✅ Resolved Sprint 16 | Catch handler present | No regression. |
| TD-17 — Brief-generator flake | ✅ Resolved Sprint 16 | Tests still deterministic | No regression. |
| TD-18 — Sign-in CTA race | ✅ Resolved Sprint 16 | Auth events module present | No regression. |

---

## Pre-release recommendations

Three priorities the user named: SEO, TD audit, release+production move. Updated ordering:

1. **Sprint 29 — Security & Dependency Refresh** (~1-2 days). Closes TD-19, TD-20, TD-21. Folds in TD-22, TD-23, TD-24, TD-25 as ~1-hour each cleanup tasks. Re-runs `pip-audit` + `npm audit` to confirm 0 high / minimal moderate. Outcome: a clean security posture to take into Production.
2. **Sprint 30 — SEO Polish** (~1-2 days). Executes `docs/seo-investigation-sprint28.md` Part 2 (157 GSC 404s, 53 missing canonicals, 380 crawled-not-indexed). Body-content beef-up on school pages.
3. **Sprint 31 — Release v2.0 + Folder Move** (~1 day). Tag `v2.0` (release notes already drafted at [docs/release-notes-v2.0.md](release-notes-v2.0.md)). Move `Development/SJKTConnect/` → `Production/SJKTConnect/`. Run `wat_lint`. Update workspace `MEMORY.md`.

**Optional Sprint 32** — close TD-12 (hansard extractor coverage) if the pypdf 5→6 upgrade in TD-19 surfaces any regression that better tests would have caught. Defer if pypdf upgrade is clean.

---

## Updates to `docs/tech-debt.md`

Append 7 new entries (TD-19 through TD-25). Update TD-06 to flag the missed checkpoint. Update TD-12 to note the prioritisation change driven by pypdf upgrade. Diff captured in the next commit.
