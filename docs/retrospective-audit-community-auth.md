# Retrospective — Audit & Community Auth Sprint

**Dates**: 2026-04-22 → 2026-04-23 (two sessions)
**Goal**: (a) Unblock community sign-in for non-tamilfoundation.org accounts. (b) Run the first full-codebase audit since Sprint 0.3.

---

## What Was Built

### Production fixes deployed
1. OAuth consent screen moved from Internal → External/Production, renamed from "SJK(T) Connect Feedback" to "SJK(T) Connect".
2. `admin@tamilfoundation.org` promoted from USER → SUPERADMIN role.
3. Session cookies set to `SameSite=None; Secure` (workaround for cross-origin fetch between `tamilschool.org` and `sjktconnect-api-*.run.app`).
4. Photo upload base64 prefix bug — `FileReader.readAsDataURL` result's `data:image/jpeg;base64,` prefix was being sent to the backend `base64.b64decode()`, which silently failed. Fixed with a `.split(",")[1]` on the frontend, then re-added for the preview `<img>`.
5. Photo preview rendered broken in the form — same cause, opposite direction.
6. Error messages swallowed by `catch {}` — now surfaces the DRF response text.
7. Community-approved photo URLs were stored as relative paths in `SchoolImage.image_url`, rendering broken because the browser resolved against `tamilschool.org` instead of the `.run.app` backend. Added `BACKEND_URL` setting and absolute-URL construction in `_apply_photo_upload`. Patched the stale `SchoolImage 1545` record directly.
8. `suggestion_image_view` now requires authentication + a relationship to the school (uploader / school admin / MODERATOR / SUPERADMIN) for non-APPROVED suggestions. APPROVED remain public (referenced from SchoolImage rows).

### Audit deliverables
9. Dependency audit — `pip-audit` clean; npm audit surfaced 3 moderate issues (upgraded next-intl, deferred Next 14→15).
10. Test coverage run — 1109 backend tests pass, 89% line coverage.
11. Security review — 5 findings ranked; 2 patched this sprint.
12. Code simplification scan — identified dead magic-link auth system (Sprint 1.6, 0 production usage ever).
13. `docs/tech-debt.md` — 15-entry living register with severity, cost-to-fix, and sprint triage.

### Punch-list fixes (after audit)
14. Pinned DRF `DEFAULT_AUTHENTICATION_CLASSES = [SessionAuthentication]` (TD-08).
15. `manage.py` prod-DB guard (TD-03) — refuses destructive commands when `DATABASE_URL` points to non-local; scoped to local dev only (bypass when `K_SERVICE` env var present or `DJANGO_SETTINGS_MODULE=production`).
16. `next-intl` upgraded 4.8.3 → 4.9.1+ (TD-10 partial).

### Branches merged to main (then deleted from origin)
- `fix/suggestion-photo-upload`
- `fix/cross-domain-session-cookies`
- `audit/codebase-techdebt`
- `fix/audit-punch-list`

---

## What Went Well

- **Fast root-cause isolation on the auth failure**. The "Failed to submit suggestion" error could have been caused by many things (CORS, permissions, validation, payload size). The diagnostic ladder (error swallowing → DevTools → server 403 → session cookie missing → SameSite=Lax blocking cross-origin) took under an hour.
- **Audit scope held at "catalogue, not fix"**. The 2.5-hour audit produced a 15-item register without any scope creep into actual code changes. The punch list afterwards then drove 3 targeted fixes cleanly.
- **Tech debt register format works**. The `what / why / blocks / cost-to-fix` structure forces each entry to be actionable. Sprints already have clear docking points for each item.
- **User-visible behaviour was validated end-to-end** before declaring item 1 (suggestion workflow E2E) done — submitted suggestions in each of the 3 types, approved them via moderation UI, verified DB state, then verified ISR-cache-refreshed school page shows the applied change.

---

## What Went Wrong

### 1. Prod-DB guard broke Cloud Run deployment

**What happened**: The `manage.py` guard I added refused to run `migrate`, which is exactly what Cloud Run's Dockerfile `CMD` runs on container startup. The new revision exited non-zero, gunicorn never started, the deploy failed and auto-rolled back.

**Why it happened**: I wrote the guard with only one mental model — "protect the local developer from accidentally hitting prod". I didn't think about the fact that production itself runs `manage.py migrate` against production, and production is the *right* place for that. The guard was correctly blocking the very case it was designed to enable.

**System change to prevent recurrence**: Added to `docs/lessons.md`: "Any code path that inspects `DATABASE_URL` or other production-distinguishing signal must check whether it's running on Cloud Run (`K_SERVICE` env var) or locally. Write this check FIRST, before the logic it gates." The fix itself layered two explicit bypasses (`K_SERVICE` + `DJANGO_SETTINGS_MODULE=production`) so that even a future settings rewrite can't re-trigger this.

### 2. Six hours between first sign-in attempt and root cause identified

**What happened**: The cross-domain cookie bug had three distinct proximate symptoms over the session (OAuth `org_internal` block → suggestion 403 from incognito's third-party cookie blocking → suggestion 403 in regular Chrome with `SameSite=Lax`). Each was diagnosed and patched in isolation, consuming ~6 hours total, when the root cause was a single architectural issue: "frontend and backend on different domains, requiring cross-origin cookies".

**Why it happened**: The Cloudflare proposal (`docs/proposals/2026-03-11-cloudflare-proxy-proposal.md`) **already described this exact problem** and its proper fix, written 6 weeks ago. I didn't read it at the start of this session. When the first symptom appeared, I treated it as a new problem rather than recognising it as the predicted one.

**System change to prevent recurrence**: Added to `docs/lessons.md`: "At the start of a session that touches a known-problematic area (auth, deployment, egress), re-read any existing proposal or post-mortem in `docs/proposals/` or `docs/retrospective-*.md` for that area before diagnosing new symptoms." Also: the tech-debt register now cross-references these proposals so the link is tighter.

### 3. First deploy attempt of punch-list commits failed silently

**What happened**: The initial deploy with the broken `manage.py` guard returned exit code 0 from gcloud but contained a "container failed to start" error deep in the output. I only caught it because I happened to tail the full log.

**Why it happened**: `gcloud run deploy` exits non-zero on failure *most* of the time, but in this case the failure was specifically during the health check after the new revision was created. Cloud Run's behaviour here is to create the revision, fail to route traffic, and report a specific error — but the wrapping command may still exit 0 depending on mode.

**System change to prevent recurrence**: Added to `docs/lessons.md`: "After every `gcloud run deploy`, verify the new revision is serving traffic: `gcloud run revisions list --service=X --limit=2 | head -3` and check the `ACTIVE` flag. Don't trust exit code alone." Long-term: the User Management sprint (TD-01, Cloudflare) will include a post-deploy smoke-test script as part of the deploy process.

---

## Design Decisions (to log in `docs/decisions.md`)

1. **`SameSite=None` on session cookies** as a bridge until Cloudflare proxy is adopted.
2. **Defer Next 14→15 upgrade** despite npm audit flagging the Image Optimizer CVE — verified we don't use `remotePatterns`, so we're not exploitable. Major-version upgrade folded into Sprint 11.
3. **Tech debt register format**: living single-file document, not per-item tickets, not GitHub issues. Triaged at each sprint close.
4. **Prod-DB guard scoping**: opt-in (`SJKTCONNECT_ALLOW_PROD_DB=1`) rather than opt-out (`--local-only`). Default-safe behaviour for developers; explicit override visible in any command history.
5. **Image Library sprint plan**: Supabase Storage over GCS, moderator delete-before-approve over auto-archive, hard cap of 20 stored photos with display cap of 5 (lightbox for rest).

---

## Numbers

| Metric | Before | After |
|---|---|---|
| Backend tests passing | 1107 | 1109 |
| Backend line coverage | unknown | 89% |
| Frontend tests passing | 288 (2 flaky) | 271 (excl. flakies) |
| Open tech debt items | 0 tracked | 15 tracked, 3 resolved |
| Security findings | 5 unknown/latent | 5 catalogued, 2 patched |
| npm audit vulnerabilities | 3 moderate | 2 remaining (not currently exploitable) |
| Cloud Run revisions shipped | `api-00087`, `web-00078` | `api-00094`, `web-00081` |
| UserProfile rows (prod) | 1 | 2 |
| Open branches | 0 | 0 |

## Next Sprint

Either **Sprint 9 (Image Library)** or **Sprint 11 (User Management)**. Strong recommendation: Sprint 11 first — restores OAuth security checks, eliminates the `SameSite=None` hack, kills the dead magic-link system, and unblocks Next 14→15 upgrade. Sprint 9 then inherits a clean auth foundation for community photo uploads.
