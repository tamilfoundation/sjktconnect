# Retrospective — User Management Sprint 11a

**Dates**: 2026-04-23 → 2026-04-24
**Goal**: Adopt Cloudflare proxy + restore OAuth security + replace magic-link with auto-claim + Next.js major upgrade. Phase 5 (`/dashboard/users` SUPERADMIN UI) deferred to Sprint 11b.

---

## What Was Built

### Phase 1 — Cloudflare reverse proxy
1. Cloudflare account created, `tamilschool.org` added.
2. Nameservers switched at Exabytes registrar from `ns1.awedns.com` / `ns2.awedns.com` to `cody.ns.cloudflare.com` / `oaklyn.ns.cloudflare.com`.
3. SSL/TLS mode = Full (strict). DKIM CNAMEs (`brevo*._domainkey`) explicitly set to **DNS only** to preserve Brevo email auth (DKIM is not HTTP-proxiable).
4. Domain ownership for `tamilschool.org` verified in Search Console under `admin@tamilfoundation.org` (had to add this account as Owner because the initial verification went under `tamiliam@gmail.com`).
5. Cloud Run domain mapping created: `api.tamilschool.org` → `sjktconnect-api`. Google issued managed SSL cert (~10 min wait via Let's Encrypt).
6. CNAME `api → ghs.googlehosted.com` set DNS-only initially for cert provisioning, then flipped to Proxied.
7. Backend env vars updated: `ALLOWED_HOSTS` + `CSRF_TRUSTED_ORIGINS` add `api.tamilschool.org`.
8. Frontend Dockerfile rebuilt with `NEXT_PUBLIC_API_URL=https://api.tamilschool.org` baked in (Next.js NEXT_PUBLIC_* are compile-time, not runtime).

### Phase 2 — Restore OAuth security
9. Removed `SESSION_COOKIE_SAMESITE = "None"` + `CSRF_COOKIE_SAMESITE = "None"` from `production.py`. Default `SameSite=Lax` is correct for same-site subdomains.
10. Restored `checks: ["pkce", "state"]` in `frontend/lib/auth.ts`. The `checks: []` workaround that had been live since 2026-03-11 is gone.

### Phase 3 — Delete magic-link, add auto-claim, redesign claim UX
11. Migration `accounts/0003`: drop `MagicLinkToken` + `SchoolContact` tables. Migration `schools/0009`: add `school.claimed_at`.
12. New `_maybe_auto_claim()` helper in `GoogleAuthView`: extract moe_code from `@moe.edu.my` email, bind `profile.admin_school`, set `school.claimed_at`. Idempotent. Won't overwrite existing claims.
13. `SchoolEditView` + `SchoolConfirmView` migrated from `IsMagicLinkAuthenticated` to `IsProfileAuthenticated` + `admin_school` check (SUPERADMIN bypass).
14. Deleted ~400 LOC across services, views, URLs, serializers, tests, claim pages, ClaimButton/ClaimForm components, magic-link i18n keys.
15. New `EmailClaimIndicator` component renders inline next to email — Google-style three states: Claimed (small green ✓ Verified pill with claim/verify-date tooltip), Unclaimed signed-out ("Claim this page" link → modal with sign-in CTA), Unclaimed signed-in-as-wrong-account (modal explains, sign-out button + copy-link-to-share).
16. `EditSchoolLink` migrated from `user.school_moe_code` to `user.admin_school?.moe_code` + SUPERADMIN bypass.
17. Initial UX (big blue "This page is unclaimed" banner) was rejected as too intrusive after first prod test; redesigned to inline indicator matching Google Business "Own this business?" pattern.

### Phase 4 — Next 14 → 16 upgrade
18. `next` 14.2.x → 16.2.4 (skipped 15 entirely since `@latest` resolved to 16).
19. Migrated 5 app-router files to async `params` API: `layout.tsx`, `school/[moe_code]/page.tsx`, `constituency/[code]/page.tsx`, `dun/[id]/page.tsx`, plus their `generateMetadata` functions. (4 other files were already on Promise<…> syntax.)
20. Added `frontend/global.d.ts` shim: Next 16's auto-generated `.next/types/validator.ts` references `React.ComponentType` unqualified but `jsx: "react-jsx"` doesn't expose React in global scope.
21. Cleaned up stale `user.school_moe_code` reference in `school/[moe_code]/edit/page.tsx`.
22. Explicit `Response` typing in `app/sitemap.ts` to satisfy Next 16's stricter inference.
23. Kept `ignoreBuildErrors: true` in `next.config.js` (with clearer comment) — pre-existing implicit-any issues out of scope.

### Tech debt resolved
- TD-01 OAuth security restored
- TD-02 Magic-link deleted
- TD-04 SameSite=None workaround removed
- TD-10 Next 14→16 (2 transitive residuals)

### Branches merged to main
- `feat/user-management` (Sprint 11a Phases 1+2) — merged in interim ship cycle
- `feat/user-management-b` (Phases 3+4) — merged at sprint close

---

## What Went Well

- **Phase boundaries held.** Splitting Sprint 11 into 11a (Phases 1-2 ship-and-stabilise) and 11b later was the right call. Each phase had a clean smoke test before the next started.
- **The Cloudflare proposal from 2026-03-11 paid for itself.** Nothing in Phase 1 surprised me — I was reading from the proposal. Saved hours of architectural debate at the moment.
- **MX lookup decision-driver.** Verifying `dig MX moe.edu.my` → Google Workspace took 30 seconds and turned a "rewrite magic-link" task into a "delete magic-link entirely" task. That single check changed the scope of Phase 3 from ~1 day to ~half a day and dropped 400 LOC instead of moving them around.
- **User-led course correction was fast.** First Phase 3 UI (big blue callout) was deployed and rejected within 15 minutes; redesigned + redeployed within an hour. Inline indicator is a clearly better design and was discoverable only by shipping the wrong one first.
- **Migration ran on prod cleanly.** Cloud Run executes `manage.py migrate` on container startup; the schema drop ran without incident. Verified via shell after deploy.

---

## What Went Wrong

### 1. First Phase 3 UI dropped a giant blue callout into the page

**What happened**: Built `ClaimCallout` as a multi-line blue alert box at the top of the school page. User immediately said "this is ugly" and pointed to Google Business profile as the right reference. Had to delete the component and rewrite as `EmailClaimIndicator` (inline next to the email field).

**Why it happened**: I designed the callout based on what was *most discoverable* (big, top-of-page, hard to miss) without considering the visual cost. I also didn't ask for a reference design before building. The "small unobtrusive link" pattern (Google's "Own this business?") is the established convention for this exact use case, but I built the heavy version first.

**System change to prevent recurrence**: Added to `docs/lessons.md`: "When designing UX for a feature whose pattern is well-established in the wider web (sign-in, claim, share, edit, comment, etc.), reference an actual implementation before coding the first version. 'Look at how Google does it' is a five-minute search and prevents the build-then-redesign cycle."

### 2. Initial Search Console domain verification went under the wrong Google account

**What happened**: gcloud opened the Search Console verification URL with `authuser=0`, which on the user's machine resolved to `tamiliam@gmail.com` (browser default). Verification succeeded — but Cloud Run wouldn't accept the verified domain because the verifying account didn't match `admin@tamilfoundation.org` (the project owner). Resulted in 5 min of "why isn't this working" before realising the account mismatch.

**Why it happened**: The `gcloud domains verify` command opens a URL but doesn't inject the right Google account. Browser defaults are unrelated to gcloud's active account.

**System change to prevent recurrence**: Added to `docs/lessons.md`: "When `gcloud domains verify` (or any gcloud command that opens a browser) opens Search Console / Console.cloud.google.com, immediately check which Google account is signed in there. If it's not the same as gcloud's active account, sign out of all and back in with the gcloud account first. The fix path (add second account as Owner under Settings > Users and permissions) takes 2 minutes if you spot it; it's confusing if you don't."

### 3. `manage.py` prod-DB guard fired during Cloud Run container startup

**What happened**: Already covered in Audit & Community Auth retrospective (2026-04-23). Did not recur in this sprint because the guard now correctly checks `K_SERVICE` env var. Note: the `claimed_at` migration ran fine on Cloud Run startup.

### 4. Frontend `NEXT_PUBLIC_API_URL` env var alone didn't switch the API URL

**What happened**: After Phase 1 setup, ran `gcloud run services update sjktconnect-web --update-env-vars=NEXT_PUBLIC_API_URL=https://api.tamilschool.org` expecting the frontend to start calling the new URL. It didn't — the JS bundle still contained the old `.run.app` URL. Took a minute to remember NEXT_PUBLIC_* are compile-time, not runtime, in Next.js.

**Why it happened**: Brain reflex — every other env var in our stack is runtime. Next.js's NEXT_PUBLIC_ convention is the exception.

**System change**: Already addressed by the architecture map note that Dockerfile bakes NEXT_PUBLIC_API_URL at build time. New lesson added: "Next.js `NEXT_PUBLIC_*` env vars are baked into the JS bundle at `npm run build` — Cloud Run runtime env var changes have no effect. To change them, rebuild the container (e.g., `gcloud run deploy --source .`) and patch the Dockerfile if the value is hardcoded there."

### 5. Next 16 build-time TypeScript checking surfaced a chain of pre-existing issues

**What happened**: Removed `ignoreBuildErrors: true` thinking the Next 14 → 16 upgrade would clear the stale issues. It didn't — the pre-existing issues (implicit-any in BoundaryMap, stale AuthUser fields, untyped fetch responses in sitemap) had been hidden for months. After 4 consecutive build failures all from real but trivial type issues, I re-enabled `ignoreBuildErrors: true` with a better comment.

**Why it happened**: Misjudgment. Assumed the type-check failures during the upgrade would be caused by the Next 16 changes themselves. Most were pre-existing.

**System change**: Don't tackle type hygiene during a framework upgrade — they're separate concerns. The arch map already notes the deferred type-hygiene as a future cleanup.

---

## Design Decisions (logged in `docs/decisions.md`)

1. **Subdomain over path-based routing for the API** — `api.tamilschool.org` instead of `tamilschool.org/api/*` via Cloudflare Worker. Simpler, no Worker code; subdomains share registrable domain so cookies are still same-site.
2. **`@moe.edu.my` Google Workspace as the auto-claim signal** — vs. magic-link email round-trip. Verified via `dig MX` once; same security guarantee, one less click.
3. **Inline `EmailClaimIndicator` over banner callout** — small text/pill next to the email field instead of a top-of-page alert. Matches Google Business profile pattern. User-led course correction.
4. **Skip Next 15, jump to 16** — `@latest` resolved to 16; 15 is already a back number. One upgrade cycle instead of two.
5. **Defer Phase 5 (`/dashboard/users` UI)** — currently solvable via Django admin (`/admin/accounts/userprofile/`); not blocking; sprint had hit a natural integration point after Phase 4.

---

## Numbers

| Metric | Sprint Start | Sprint Close |
|---|---|---|
| Backend tests | 1109 | 1076 (net −33: removed magic-link, added auto-claim) |
| Backend coverage | 89% | ~89% |
| Frontend tests | 271 | 258 (net −13: removed claim component tests) |
| Tech debt items open | 11 | 7 |
| Tech debt items resolved this sprint | — | 4 (TD-01, TD-02, TD-04, TD-10 mostly) |
| Cloud Run revisions shipped | api-00094 / web-00081 | api-00097 / web-00088 (Phase 4) |
| Lines of code removed | — | ~400 LOC (magic-link surface) |
| Lines of code added | — | ~200 LOC (auto-claim, EmailClaimIndicator, Next 16 migrations) |
| Branches still open | 0 | 0 |
| OAuth security checks active | 0 | 2 (PKCE + state) |
| Auth identity systems | 2 (magic-link + UserProfile) | 1 (UserProfile only) |
| Cookie SameSite mode | None (workaround) | Lax (proper) |

## Next Sprint

**Sprint 9 — Image Library** is recommended next (over Sprint 11b) because every school page currently shows broken Places photos. Plan ready at `docs/plans/2026-04-22-image-library-sprint-plan.md`. Resolves TD-05, TD-06, TD-07, TD-09.

Sprint 11b (Phase 5: `/dashboard/users` SUPERADMIN UI + profile additions) — pick up after Sprint 9 ships.
