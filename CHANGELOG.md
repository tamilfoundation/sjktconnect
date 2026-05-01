# Changelog

## Sprint 22 — SEO Snippet & Canonical Hostname Fix (2026-05-01)

**Trigger**: GSC export `tamilschool.org-Performance-on-Search-2026-05-01` (3-month window 28/02 → ~28/04). Avg position flatlined at 7.4 despite 30× impressions growth from 0 → 33.1k. Top queries are "sjkt {school}" intent searches; SERP shows our top schools winning rich snippets ("Alamat: ..." for `/ms/`) but small schools like Trolak losing to generic English prose ("SJK(T) Trolak is a Tamil primary school..."). Pandai outranks us on text-only listings; AnyFlip and CommChest beat us with image thumbnails. www-root duplicate listings split ranking signal.

### Added
- **`buildSchoolMetadata(school, locale)` in `frontend/lib/seo.ts`** — locale-aware Metadata builder. Title includes town name when town ≠ school name (e.g. "SJK(T) Trolak | 17 Students, Grade C | Pekan Trolak, Perak"). Description renders labelled key/value pairs (Address/Alamat/முகவரி + Email + Phone + Location + Assistance) so Google's snippet picker has consistent structured data on every locale, not just `/ms/`.
- **`buildConstituencyMetadata(c, locale)`** — title format "{Name} — MP, Tamil Schools | {code}, {state}" (e.g. "Indera Mahkota — MP, Tamil Schools | P140, Pahang"). Captures GSC's natural-form queries like "indera mahkota mp" (pos 16) and "yb paya besar" (pos 20).
- **`buildDUNMetadata(dun, locale)`** — title format "{Name} ADUN — Tamil Schools, MP | {code}, {state}".
- **`buildSchoolJsonLd(school)`** — emits `EducationalOrganization` JSON-LD with PostalAddress, GeoCoordinates, telephone, email, image, numberOfStudents. Wrapped in `<script type="application/ld+json">` on every school page; `<` chars escaped to `\u003c` to defang any breakout from school DB fields.
- **`SCHOOL_PLACEHOLDER_URL`** — branded SVG fallback at `/public/school-placeholder.svg` (1200×630 indigo-gradient with "SJK(T) · Tamil Primary School · tamilschool.org"). Used in og:image + ImageObject schema + the SchoolPhotoGallery empty state. Schools without uploaded photos previously rendered text-only "No photo" — now they emit a real `<img>` so Google's SERP thumbnail picker has something to use.
- **Sprint 22 hub-page extension at `/[locale]/about-tamil-schools`** — replaces the "Coming Soon" placeholder with three Q&A blocks ("How many?", "How distributed?", "What is an SJK(T)?") plus a live state-breakdown table sorted by school count. Pulls `fetchNationalStats()` + `fetchAllSchools()` server-side; falls back to last-known stats if API is unavailable during ISR rebuild. Targets long-tail queries "how many tamil school in malaysia" (currently pos 9-23, low volume).
- **`frontend/__tests__/lib/seo.test.ts`** — 23 tests covering buildAlternates, buildSchoolMetadata (locale-aware labels in en/ms/ta, town-distinct logic, og:image fallback), buildConstituencyMetadata (English MP/PH-PKR/mention count + Malay 'mewakili' + locale-correct canonical), buildDUNMetadata, buildSchoolJsonLd (PostalAddress + GeoCoordinates + GPS-missing fallback + image fallback).
- **1 new SchoolImage test** — confirms branded placeholder `<img>` renders with correct src + descriptive alt for SEO.

### Changed
- **`frontend/app/[locale]/school/[moe_code]/page.tsx`** — `generateMetadata` delegates to `buildSchoolMetadata`; page body emits a `<script type="application/ld+json">` JSON-LD payload via the new helper.
- **`frontend/app/[locale]/constituency/[code]/page.tsx`** — delegates to `buildConstituencyMetadata`. Old prose ("MP X represents Y in Z. N Tamil schools.") replaced by data-rich form.
- **`frontend/app/[locale]/dun/[id]/page.tsx`** — delegates to `buildDUNMetadata`.
- **`frontend/components/SchoolImage.tsx`** — empty-state branch renders branded placeholder `<img src="/school-placeholder.svg">` with `alt="{schoolName} — Tamil primary school (SJK(T))"`. The "No photo" text is preserved as an overlay caption.
- **`frontend/messages/{en,ta,ms}.json`** — `aboutTamilSchools` namespace expanded from 5 keys (Coming Soon stub) to 14 keys (full FAQ + state-breakdown table headers + CTA). Page title rewritten to capture "how many tamil schools" intent; intro leads with the 528 number for snippet candidacy.

### Verified pre-deploy
- 320 frontend tests pass (was 297 + 23 new = 320). New: 23 in `__tests__/lib/seo.test.ts`, 1 in `__tests__/components/SchoolImage.test.tsx` (branded placeholder).
- `npx next build` route table: school/constituency/dun pages still show ● (SSG/ISR) markers. `revalidate=86400` preserved; about-tamil-schools added with `revalidate=86400`. Build completes successfully against prod API.
- Pre-rendered `.next/server/app/{en,ta,ms}/about-tamil-schools.html` inspected: titles correct ("Tamil Schools in Malaysia — How Many, Where, Statistics | SJK(T) Connect" / Tamil-script equivalent), state breakdown table populated with live counts (Selangor, Perak, Johor, …).

### Pending post-deploy verification (this sprint)
- Curl `https://tamilschool.org/school/JBD1026` and confirm: new `<title>` with town, data-rich `<meta name="description">`, JSON-LD script tag with EducationalOrganization payload.
- Curl `https://tamilschool.org/ta/school/JBD1026` and confirm Tamil-script title + Tamil-label description (முகவரி / மின்னஞ்சல் / தொலைபேசி).
- Curl `https://tamilschool.org/about-tamil-schools` and confirm state-breakdown table renders.
- Re-pull GSC Pages report 2-3 weeks after deploy; expect "Alternate page with proper canonical tag" count to drop from 2.36k toward zero (Sprint 21 canonical fix landed 29 Apr — 1 day before this GSC export, so it wasn't reflected; Sprint 22 changes should compound).

### Operational followup (manual, user action)
- Configure Cloudflare Page Rule: `www.tamilschool.org/*` → 301 → `https://tamilschool.org/$1`. The Pages report shows the same school listed twice in a single SERP because both hostnames resolve. One canonical hostname consolidates ranking signal. Cloudflare Page Rule (vs Cloud Run domain mapping) is reversible and doesn't require DNS-only flip.

## Sprint 21 — Egress Hardening Round 2 (2026-04-29)

**Deployed**: backend `sjktconnect-api-00112-k7t` (UA block middleware). Frontend `sjktconnect-web-00110-vph` (3 iterative deploys: ISR setup, fetchJSON cache, generateStaticParams). Cloud Monitoring dashboard `f1722366-2df9-4446-9941-7cda5c019615` rewritten with MQL.

User trigger (2026-04-29): the Sprint 17 ISR fix didn't hold — Supabase still showed ~500 MB/day egress with the site barely publicised. Investigation confirmed Sprint 17's `revalidate = 86400` exports were inert because `next-intl/server.getMessages()` reads cookies/headers, which marks every page as dynamic and overrides the page-level revalidate. Real Cache-Control upstream was `no-cache, no-store`. Combined with one bot (AwarioBot) generating ~31 MB/day of backend egress, this sprint hardens both fronts.

### Added
- **`UserAgentBlockMiddleware`** in `core/middleware.py` — case-insensitive substring match against AwarioBot, AwarioRssBot, AwarioSmartBot, SemrushBot, DataForSeoBot, MJ12bot. Wired second in `MIDDLEWARE` (right after `IPBlockMiddleware`) so blocked traffic never reaches routing or DB.
- **`backend/core/tests/test_user_agent_block.py`** — 7 new tests: 6 blocked-UA variants (AwarioBot/SemrushBot/DataForSeoBot + case-insensitive + missing UA + real browser + Googlebot pass-through).
- **`generateStaticParams()` returning `[]`** on 5 dynamic-segment pages (`school/[moe_code]`, `constituency/[code]`, `dun/[id]`, `parliament-watch/[id]`, `parliament-watch/sittings/[id]`). Empty array opts the route into ISR-on-demand caching — nothing is pre-built at deploy time, but each unique URL gets cached on first hit for `revalidate` seconds. Without this, Next 15+ treats undefined `generateStaticParams` as fully-dynamic regardless of `revalidate`.
- **`generateStaticParams()` on `app/[locale]/layout.tsx`** — pre-renders the 3 locale shells (en/ta/ms).
- **`app/[locale]/dashboard/layout.tsx`** — new file with `export const dynamic = "force-dynamic"` so the entire dashboard segment opts out of static prerendering (one file vs editing 4 pages).
- **`backend/docs/metrics/{api-egress,web-egress,dashboard}.{yaml,json}`** — source-of-truth for the Cloud Logging metrics + Cloud Monitoring dashboard. The metrics keep `valueType: DISTRIBUTION` (GCP rejects INT64 + valueExtractor); the dashboard widgets use MQL queries that fold distribution → scalar before rendering top-N.
- **6 explicit Disallow entries in `frontend/app/robots.ts`** — AwarioBot, AwarioRssBot, AwarioSmartBot, SemrushBot, DataForSeoBot, MJ12bot. Polite bots self-throttle before the 403; rude bots get the middleware backstop.

### Changed
- **`app/[locale]/layout.tsx`** — added `setRequestLocale(locale)` call after locale validation. Without it, `getMessages()` reads requestLocale via cookies/headers and marks the layout as dynamic, cascading to every page.
- **10 public pages** (`/[locale]/page.tsx`, `/constituencies/page.tsx`, `/news/page.tsx`, `/parliament-watch/page.tsx`, `/parliament-watch/sittings/page.tsx`, `/constituency/[code]`, `/dun/[id]`, `/parliament-watch/[id]`, `/parliament-watch/sittings/[id]`, `/school/[moe_code]`) — each now imports `setRequestLocale` from `next-intl/server`, accepts `locale` as a Promise param, and calls `setRequestLocale(locale)` at the top of the page component.
- **`lib/api.ts` `fetchJSON()`** — now sets `next: { revalidate: 86400 }`. Next 15+ defaults `fetch()` to uncached, which marked every server-rendered public page as dynamic regardless of the page-level `revalidate` export. Authenticated endpoints use direct `fetch()` with `credentials: "include"` and bypass this helper, so they're unaffected.
- **`MIDDLEWARE` in `sjktconnect/settings/base.py`** — `UserAgentBlockMiddleware` wired second after `IPBlockMiddleware`.
- **Cloud Logging metrics** — `sjktconnect_api_egress_per_route` and `sjktconnect_web_egress_per_route` recreated from YAML configs (kept as DISTRIBUTION; INT64 + valueExtractor combo rejected by GCP).
- **Cloud Monitoring dashboard** — all 4 widgets rewritten as MQL queries (`fetch <resource>::<metric> | align delta(1h) | every 1h | group_by [metric.<label>], sum(value) | top 10`). Replaces the previous GUI-style aggregation that emitted "input cannot be a distribution" on `pickTimeSeriesFilter`.

### Verified live
- `curl -sI https://tamilschool.org/en` → `Cache-Control: s-maxage=86400, stale-while-revalidate=31449600` + `x-nextjs-cache: HIT`. Same for `/news`, `/constituencies`, `/parliament-watch`, `/parliament-watch/sittings`.
- `curl -sI https://tamilschool.org/en/school/BBA8101` → same, `x-nextjs-cache: HIT` on second request. Same for `/constituency/P078`, `/dun/1`, `/parliament-watch/sittings/1`.
- `curl -H "User-Agent: AwarioBot/1.0" https://api.tamilschool.org/api/v1/schools/...` → 403; real browser UA → 200/404 (route works).
- All 4 dashboard MQL queries return `doubleValue` per series with valid top-N — verified via `timeSeries:query` API.

### Deferred to Sprint 22
- **Task #43 (Supabase Storage hot-link protection)** — user-approved deferral. Two viable paths (image-proxy-on-backend vs signed-URL approach) both need a ~2-4h design call. The recommended approach is the image proxy: new `/api/v1/img/<key>` endpoint that streams Supabase bytes after a Referer check, with `Cache-Control: s-maxage=31536000, immutable` so Cloudflare absorbs most repeat hits. Moves egress from Supabase Pro ($0.09/GB) to Cloud Run free tier.

### Tests
- 7 new backend tests in `core/tests/test_user_agent_block.py`. Final tally: **1198 backend (+7) + 297 frontend** pass.

### Operational followup
- **2026-04-30**: Confirm Supabase egress chart shows <150 MB/day. If still elevated, the next-most-likely culprit is Supabase Storage (school-images bucket) being hit directly by image-loading bots — that's Sprint 22 scope.

### Deploys
- Backend: `sjktconnect-api-00111-mrq` → **`sjktconnect-api-00112-k7t`**.
- Frontend: `sjktconnect-web-00107-wd9` → `sjktconnect-web-00108-c56` → `sjktconnect-web-00109-6r4` → **`sjktconnect-web-00110-vph`** (3 iterative deploys to pin down the dynamic-route caching gap; lesson captured in retrospective-sprint21.md).

## Sprint 20 — Leader Inline CRUD (2026-04-28 evening)

**Deployed**: backend `sjktconnect-api-00111-mrq` (3 new endpoints + serializer + permission helper). Frontend `sjktconnect-web-00107-wd9` (LeadersTab rewrite).

User decision (2026-04-28 evening): the Sprint 19 LeadersTab shipped read-only with a "coming soon" notice. School admins know best who their headmaster / board chairman / PTA chairman / alumni chairman is — and these change yearly — so the data needs to be maintained by them, not by a contact-feedback workflow.

### Added
- **`POST /api/v1/schools/<moe_code>/leaders/`** — create. Body: `{role, name, phone?, email?}`. Returns 201 with the new leader's id + role_display. Returns **409 `slot_taken`** if the school already has an active leader for that role (delete the existing first).
- **`PATCH /api/v1/schools/<moe_code>/leaders/<id>/`** — update. Accepts `name`, `phone`, `email`. **Role is immutable on PATCH** — to change a leader's role, delete and recreate.
- **`DELETE /api/v1/schools/<moe_code>/leaders/<id>/`** — soft-delete (sets `is_active=False`). The model's unique constraint is conditional on `is_active=True`, so delete-then-recreate-same-role works correctly.
- **`SchoolLeaderAdminSerializer`** — admin-shape serializer (id + role + role_display + name + phone + email). Used by the new CRUD endpoints AND now by `SchoolEditSerializer.get_leaders()` so the edit page receives the full shape in a single round-trip.
- **`_can_edit_school_leaders` permission helper** — SUPERADMIN OR bound admin of THIS school. Mirrors `community._is_photo_approver`. **MODERATOR is NOT special-cased** — leadership is a school-internal concern, not platform moderation.
- **`backend/schools/tests/test_leader_crud_api.py`** — 17 new tests: 6 permission matrix (anonymous, regular, MODERATOR, admin-of-different, admin-of-this, SUPERADMIN) + 11 behaviour (happy path, 409 slot_taken, 400 invalid role, 400 missing name, 404 unknown school, PATCH name/phone/email, role-immutable-on-PATCH, soft-delete, delete-then-recreate, 404 unknown leader, 404 leader-belongs-to-different-school).

### Changed
- **`frontend/components/edit_tabs/LeadersTab.tsx`** rewritten as inline CRUD. 4 fixed role slots (Board Chairman, Headmaster, PTA Chairman, Alumni Association Chairman). Existing leaders shown as editable rows (name + phone + email + Remove); empty roles shown as "+ Add {role}" buttons. Single "Save changes" button at tab footer (disabled when no pending changes). Sequential flush on save (delete → create → update) so the unique-active-role constraint doesn't trip on a delete-and-recreate-same-role flow. Blanking an existing leader's name = treated as delete (UX shortcut).
- **`SchoolEditSerializer.get_leaders()`** — switched from public `SchoolLeaderSerializer` to admin `SchoolLeaderAdminSerializer`. The endpoint is gated by `IsProfileAuthenticated` AND the page-level role check, so private fields (phone, email) are safe to return here.
- **`frontend/lib/types.ts`** — added `SchoolLeaderAdminData` (extends public `SchoolLeaderData` with id + phone + email). `SchoolEditData.leaders` retyped to use it.
- **`frontend/lib/api.ts`** — `createSchoolLeader`, `updateSchoolLeader`, `deleteSchoolLeader` helpers + `LeaderRole` type + `LeaderUpsertPayload` interface.
- **Translations en/ta/ms** — `leadersIntro` (replaces `leadersComingSoon`), `addLeader` (with `{role}` interpolation), `leaderName/Phone/Email/Remove/RemoveConfirm`, 4 role labels, `leadersSlotTaken`, `leadersSaving/Saved/FailedSave`. The `noLeadersYet` copy updated to point at the + Add buttons.

### Tests
- **8 new LeadersTab tests** in `__tests__/components/LeadersTab.test.tsx` (component-level): renders 4 slots correctly, Save button disabled at rest, edit-existing-name → updateSchoolLeader, click +Add then save → createSchoolLeader, click +Add without name → Save stays disabled, Remove + confirm → deleteSchoolLeader, backend `role_taken` → friendly slot-taken message, blank-name on existing → treated as delete.
- **2 SchoolEditForm tests updated** for the new editable shape (replaces the 1 read-only "coming soon" assertion from Sprint 19).
- Final tally: **1191 backend + 297 frontend tests** pass.

### Deploys
- Backend: `sjktconnect-api-00110-r6l` → **`sjktconnect-api-00111-mrq`**.
- Frontend: `sjktconnect-web-00106-dd6` → **`sjktconnect-web-00107-wd9`**.

## Sprint 19 — Edit Page Tabs (2026-04-28)

**Deployed**: backend `sjktconnect-api-00110-r6l` (migration `0010_drop_last_verified_and_verified_by` applied on prod Supabase + serializer extension). Frontend `sjktconnect-web-00106-dd6` (5-tab edit page).

User decision (2026-04-28): the existing `/school/[moe_code]/edit` page was a long single-form layout with a prominent "Confirm Data" button + green card. The button was redundant — MOE data is the source of truth, nothing for school admins to confirm. The form was also hard to scan with 20+ fields in one column. Sprint 19 redesigns the page as a 5-tab layout (Core / Contact / Leaders / Support / Images) and removes the Confirm Data flow entirely.

### Removed
- **`Confirm Data` button + card** on the edit page.
- **`POST /api/v1/schools/<moe_code>/confirm/`** endpoint (`SchoolConfirmView`).
- **`School.last_verified` + `School.verified_by`** model fields (migration `schools/0010_drop_last_verified_and_verified_by.py`).
- **`SchoolEditView.put()`** no longer sets a verification timestamp on save.
- **Sprint 1.7 admin Verification Dashboard** at `/dashboard/verification/` (entire page + view + template + URL include + nav link). The metric it surfaced — "% of schools whose admins have explicitly confirmed their data" — is no longer meaningful.
- **`confirmSchool()` API helper** + `SchoolConfirmResponse` type from frontend.
- **6 SchoolConfirmViewTest cases** + 4 verification-dashboard tests + 1 verification-timestamp test on `SchoolEditView`.
- 1 stale row in the tech-debt triage table.

### Added
- **5-tab edit page** at `/school/[moe_code]/edit`:
  - **Core** — identity (read-only MOE) + editable details (Tamil name, enrolment counts, sessions). Read-only fields visually distinct: muted background, lock icon, smaller padding. Editable fields: clean white inputs, blue focus ring.
  - **Contact** — address + phones + email. GPS coordinates **gated to SUPERADMIN** — school admins see them read-only with a "verified via Google Places" badge so they can't accidentally override the Sprint 5.4 batch verification.
  - **Leaders** — read-only listing of the 4 SchoolLeader rows. "Editing leaders coming soon" notice. Inline CRUD on Leaders is a future-work item; needs new permission-scoped backend endpoints.
  - **Support** — bank details that power the SupportSchoolCard + DuitNow QR.
  - **Images** — launchpad linking to the existing `/dashboard/images` manager (Sprint 14).
- **New shared frontend primitives** in `frontend/components/edit_tabs/`:
  - `TabBar.tsx` — pill-button nav with `aria-selected` + URL-hash persistence (deep-link + browser back).
  - `FieldRow.tsx` — `ReadOnlyField` + `EditableField` shared between all tabs.
  - `CoreTab.tsx`, `ContactTab.tsx`, `LeadersTab.tsx`, `SupportTab.tsx`, `ImagesTab.tsx`.
- **"Claimed by HM since {date}" badge** in the page header when `claimed_at` is set — surfaces the auto-claim trust signal Sprint 11a Phase 3 added but never displayed anywhere.
- **`SchoolEditSerializer` extended** with read-only MOE metadata (`ppd`, `grade`, `assistance_type`, `skm_eligible`, `location_type`, `gps_lat`, `gps_lng`, `gps_verified`, `claimed_at`) and a nested `leaders` array. Single endpoint serves the entire tabbed page; no second API call.
- **10 new frontend tests** in `__tests__/components/SchoolEditForm.test.tsx` covering tab navigation, default tab, no-Confirm regression, leaders/images launchpad, GPS gating both ways, save-payload filter excludes GPS for non-admins.

### Translations
- `en/ta/ms` updated with tab labels, section captions ("Identity (from MOE — read-only)", "Editable details"), GPS notice, "Claimed by HM since {date}" badge, "Editing leaders coming soon", and the field labels for the newly-surfaced read-only MOE fields.

### Tests
- Backend: **1174 passed** (was 1184 before this sprint; -10 = removed dashboard + confirm tests).
- Frontend: **288 passed** (was 289; -1 = removed `confirmSchool` test block; SchoolEditForm test rewritten with 10 new tests replacing 11 old ones).

### Process
- **Stitch prototype mandatory** per CLAUDE.md "prototype UI in Stitch first" rule. Project `10588652759232271161`, screen `9d4cd7350e2648f9a0be8321f295df11`. User-approved before any code was written.
- **Two deploys** for the sprint (backend + frontend, in parallel) — within budget.

## Sprint 18 — Monthly Digest Coverage (2026-04-27 evening)

**Deployed**: backend `sjktconnect-api-00107-dxh` (aggregator extension + command flag). Frontend unchanged.

User noticed the 1 April 2026 monthly digest reported "0 Parliament Mentions" for March even though three mentions were live on the public site under a published Sitting Brief, AND the 1st Meeting 2026 Report (covers 19 Jan → 03 Mar) had been generated on 4 Mar. Investigation found four gaps in the aggregator + two more during prod dry-run.

### Added
- **`backend/broadcasts/services/blast_aggregator.py`** — `aggregate_month()` now returns 5 keys (was 3): `parliament`, `news`, `briefs` (NEW — sitting briefs), `meeting_reports` (NEW — meeting-level reports), `scorecards`, plus `scorecards_are_lifetime_fallback` (NEW — bool). Added optional `backfill_since: date` parameter that widens the briefs + meeting_reports lookback for one-time fill scenarios.
- **`compose_monthly_blast --backfill-since YYYY-MM-DD`** flag — date-validated. Forwards through to aggregator + analyst. Dry-run output now lists each picked-up meeting + brief by name so the operator can verify before sending.
- **DATE-SEMANTICS POLICY** docstring at the top of `blast_aggregator.py` documenting per-source filter field + approval gate. Future contributors don't have to re-derive.
- New "Parliament Meeting Reports" + "Sitting Summaries" sections in both v1 and v2 templates.

### Changed
- **HansardMention filter**: `review_status="APPROVED"` → `exclude(review_status="REJECTED")`. Mentions default to PENDING; the public site shows them; the digest now does too. **This was the root cause of the 1 April digest's "0 mentions" lie** — three mentions on 2 March were PENDING.
- **MPScorecard filter**: now date-filtered by `last_mention_date` in target month. Falls back to lifetime top-3 only when no MP was active that month, with a `scorecards_are_lifetime_fallback` bool so the template can label the section appropriately. Stops the "same top-3 every month forever" pattern.
- **`is_published` filter on briefs + meeting reports**: REMOVED (was added in a first pass, then removed when the dry-run revealed prod data routinely has `is_published=False` even on artifacts shown publicly). Aggregator now mirrors public-site visibility — see lessons.md entry.
- **Backfill window for meetings**: switched from `published_at` to `end_date` because most prod rows have `published_at=None`. Captures natural intent ("any meeting that ended after backfill_since but before the target month").
- **`monthly_analyst.py` ANALYST_PROMPT**: now includes sitting briefs + meeting reports in the input data, plus a `scorecard_qualifier` note when the lifetime fallback is in use so Gemini can avoid claiming "most active this month" when it isn't.

### Tests
- 22 new tests in `test_blast_aggregator.py` covering the new keys, APPROVED→exclude(REJECTED) regression-fix, brief + meeting filters, backfill semantics, lifetime-fallback scorecards.
- 2 new tests in `test_compose_command.py` for `--backfill-since` (invalid date + happy-path dry-run).
- `test_monthly_analyst.py` mocks updated for the new aggregator return shape.
- Final tally: **179 broadcasts tests pass** (was 174).

### Verified end-to-end (read-only against prod)
```
PYTHONIOENCODING=utf-8 python manage.py compose_monthly_blast \
    --month 2026-04 --backfill-since 2026-02-01 --dry-run
→ 0 parliament, 5 news, 1 sitting briefs, 1 meeting reports,
  3 scorecard items (lifetime fallback)
→ meeting: 1st Meeting 2026 (2026-01-19 → 2026-03-03)
→ brief: 2026-03-02 — Parliament Addresses SJK(T) Special
  Education Disparity, Mother Tongue Learning
```

Both pieces of missing content from the original investigation surface.

### Operational follow-up (one-time fill)
The Cloud Scheduler `sjktconnect-monthly-blast` job fires at 09:00 MYT on 1 May 2026 with the default args (no `--backfill-since`). To get the meeting report into the April digest, one of:
- **Manual trigger** before 1 May: `gcloud run jobs execute sjktconnect-monthly-blast --args="--month=2026-04,--backfill-since=2026-02-01" --region asia-southeast1`. Then disable the scheduled fire OR let it run as a no-op duplicate.
- **Edit Cloud Scheduler args** temporarily to add `--backfill-since 2026-02-01`. Revert after the 1 May fire so future months don't repeat the backfill.

Recommended: manual trigger so the scheduler config stays clean.

## Sprint 17 — Egress Hardening (2026-04-27)

**Deployed**: backend `sjktconnect-api-00106-rxf` (IPBlockMiddleware), frontend `sjktconnect-web-00105-vhx` (ISR + sitemap + news pageSize fixes).

Hotfix-style sprint triggered by user noticing 500 MB/day Supabase egress with the site not yet publicised. Investigation found four leaks; fixed all four. Also added per-route egress observability so the next anomaly is visible by route + user-agent before it hits the billing chart. Expected impact: 500 MB/day → ~100-150 MB/day within 24h.

### Added
- **`backend/core/middleware.py` — `IPBlockMiddleware`**: returns 403 immediately for IPs on a `BLOCKED_IPS` set. Reads real client IP from Cloudflare's `CF-Connecting-IP` header (priority), `X-Forwarded-For` first hop, or `REMOTE_ADDR` (fallback for direct Cloud Run service URL). Wired FIRST in the MIDDLEWARE chain so blocked requests never touch routing/DB/serializers — cheapest possible abort. Initial blocklist: `88.216.210.27` (the Chrome/91 fake-UA scraper that's been generating ~1,400 req/day).
- **`backend/core/tests/test_ip_block.py`**: 6 unit tests covering CF-Connecting-IP priority, X-Forwarded-For first-hop parsing, multi-hop XFF, clean IPs, no-headers fallback, header precedence.
- **`backend/scripts/egress_metric_config.yaml`** + **`egress_metric_web_config.yaml`**: Cloud Logging metric configs for per-route egress on `sjktconnect-api` and `sjktconnect-web`. Distribution metrics over `httpRequest.responseSize`, labelled by `route` + `user_agent` + `status`.
- **`backend/scripts/egress_dashboard.json`**: Cloud Monitoring dashboard config — 4 charts (API + web egress by route, API + web egress by user_agent for bot detection). Applied as dashboard `f1722366-2df9-4446-9941-7cda5c019615` in `sjktconnect` GCP project.
- **`frontend/app/sitemap.ts`** — `export const revalidate = 86400`. Sitemap now regenerates once per day instead of per-request (was being fetched ~6×/day by ClaudeBot et al, each fetch pulling all 528 schools + 222 constituencies fresh from the backend).

### Changed
- **10 frontend pages** flipped from `export const revalidate = false` to `export const revalidate = 86400` (24h ISR). The `false` value disables Next.js caching entirely — every request, including bot crawls, forces a fresh server-side render. Pages: `/`, `constituencies`, `constituency/[code]`, `dun/[id]`, `news`, `parliament-watch`, `parliament-watch/[id]`, `parliament-watch/sittings`, `parliament-watch/sittings/[id]`, `school/[moe_code]`. Verified each page has no cookies/headers/dynamic markers — all serve fully public data, safe to cache. Sprint 8.3 retrospective claimed "ISR with 24h revalidate" was set; reality was the opposite. **This is the single biggest egress fix.**
- **`backend/sjktconnect/settings/base.py`** — `IPBlockMiddleware` added to `MIDDLEWARE` list as the first entry.
- **`frontend/app/[locale]/news/page.tsx`** — `fetchNews({ pageSize: 50 })` (was `500`). NewsList already supports pagination via `totalCount`. Saves ~125 KB per news page render.

### Tests
- 6 new backend tests (`core/tests/test_ip_block.py`).
- Final tally: **1161 backend** + 289 frontend tests.

### Verified (no change needed)
- `sjktconnect-web` Cloud Run service has `autoscaling.knative.dev/minScale: '1'` — Egress Fix sprint did land this; Next.js ISR cache stays warm 24/7. (CLAUDE.md memory was wrong about middleware — that didn't land — but right about minScale.)
- `.defer("boundary_wkt")` on the 6 schools/constituency views from Egress Fix sprint is in place; saving ~2 GB/day vs without it.

### Observability now available
- Cloud Monitoring → Dashboards → "SJK(T) Connect — Egress by Route/UA": real-time per-route bytes-per-hour, broken down by route AND user-agent. The next "egress is too high" question can be answered by clicking instead of hypothesising.
- Cloud Logging metrics `sjktconnect_api_egress_per_route` + `sjktconnect_web_egress_per_route` are queryable via Metrics Explorer for ad-hoc analysis.

### Monitor
- **2026-04-29 (48h post-deploy)**: check Supabase Reports → SJK(T) Connect → Egress chart. Target: <150 MB/day daily bars. If still ~500 MB/day, the new dashboard will show which route is leaking and we attack that next.

## Sprint 16 — Code-Quality Pass (2026-04-27)

**Deployed**: backend `sjktconnect-api-00105-wwd` (TD-14 refactor), frontend `sjktconnect-web-00103-phl` (TD-01) → `00104-d4n` (TD-18). Both auth fixes user-verified on prod.

Final sprint of the 5-sprint roadmap (12 → 13 → 14 → 15 → 16). Closed all open tech debt that was triaged into this sprint except TD-11 + TD-12 (test-coverage padding, deferred). Both auth bugs that have shadowed Sprint 12 onwards (TD-01 and TD-18) are resolved; SuperAdmin and regular users can now sign in with full PKCE+state CSRF protection AND see role-correct CTAs without a manual page refresh.

### Added
- **`frontend/lib/auth-events.ts`** — module-scoped pub/sub emitter (`emitProfileReady` / `onProfileReady`). Tiny (~30 lines, no deps). Used by `UserMenu` to broadcast "Django session is ready" after `syncGoogleAuth()` resolves; consumed by `EditSchoolLink` and `SuggestButton` to re-fetch `/me` on the explicit signal instead of racing the cookie write.

### Changed
- **`frontend/lib/auth.ts`** — bumped `next-auth` 5.0.0-beta.30 → beta.31 (pulls `@auth/core` 0.41.0 → 0.41.2). Restored `checks: ["pkce", "state"]` on the Google provider — back to full OAuth CSRF protection after the Sprint 12 regression. Overrode `@auth/core`'s default `csrfToken` cookie name to use `__Secure-` prefix instead of the stricter `__Host-` (root cause of TD-01: Cloudflare's proxy / Cloud Run header pipeline modifies `Set-Cookie` in ways that violate `__Host-` semantics, silently dropping the cookie at the browser).
- **`frontend/components/UserMenu.tsx`** — fires `emitProfileReady()` after `syncGoogleAuth()` resolves (closes the TD-18 race for downstream auth-aware components).
- **`frontend/components/EditSchoolLink.tsx`** + **`SuggestButton.tsx`** — subscribe to `onProfileReady`; first fetch attempts immediately on `status === "authenticated"` (cheap, often races the cookie write), then re-fetches when the explicit signal fires. No polling, no setTimeout. Same pattern is now established for any future role-aware UI element.
- **`frontend/app/[locale]/dashboard/users/page.tsx`** — added `.catch(() => router.push("/"))` to the `fetchMe()` SUPERADMIN gate (TD-16 residual). On a 401 from the backend (signed-out user, network error), the redirect now fires instead of falling through to render the user table chrome. Backend remained correctly gated by `IsSuperAdmin` so no data ever leaked, but the bug was a trust signal.
- **`backend/community/api/views.py`** — extracted `_can_moderate_or_owns_school(profile, school_id)` helper. Replaces 4 inline duplications of the "MODERATOR/SUPERADMIN OR bound school admin" check across `pending_suggestions_view` (gate + filter), `approve_suggestion_view`, and `reject_suggestion_view`. Pure refactor. (TD-14)

### Tests
- 4 fixed pre-existing test failures inherited from Sprint 15 (`EditSchoolLink.test.tsx` + `SuggestButton.test.tsx` didn't mock the new `useSession` dependency added by Sprint 15's hotfix; `SubscribeForm.test.tsx` was missing the `website: ""` honeypot field added in Sprint 8.6). Sprint 15's "285 frontend tests passing" claim was actually 282 pass + 3 fail — discovered when running the suite at the top of Sprint 16. (TD-15)
- `parliament/tests/test_brief_generator.py` now `@patch.dict(os.environ, {"GEMINI_API_KEY": ""}, clear=False)` at the class level — forces brief generation down the template-fallback path, removing the non-deterministic LLM dependency that's been flaking the literal-substring assertions since Sprint 0.4. The tests verify generate_brief wiring (title, mention count, HTML containing fixture summaries, social post length); prose-quality tests live elsewhere and mock genai directly. (TD-17)
- Final tally: **1155 backend + 289 frontend tests** (no flakes; TD-15 + TD-17 cleared).

### Resolved tech debt
- **TD-01** — OAuth checks restored to `["pkce", "state"]` after `__Secure-`-prefix override on csrfToken cookie + `next-auth` bump. User-verified on prod 2026-04-27 (`web-00103-phl`).
- **TD-10** — Last residual was `brace-expansion` + `picomatch` transitive deps; both bumped via `npm audit fix` (no `--force`).
- **TD-14** — Role checks consolidated.
- **TD-15** — Frontend test flakes deflaked.
- **TD-16** — `/dashboard/users` chrome leak closed; other dashboard pages already had acceptable fallback UX.
- **TD-17** — Brief generator LLM flake pinned to template fallback.
- **TD-18** — Sign-in CTA race fixed via `auth-events` emitter. User-verified on prod 2026-04-27 (`web-00104-d4n`) — both `tamiliam` (USER) and `admin` (SUPERADMIN) accounts confirmed.

### Deferred (out of scope for this sprint)
- **TD-11** — `accounts/services/google.py` at 25% coverage. Test-coverage padding; not blocking anything.
- **TD-12** — `hansard/pipeline/extractor.py` at 26% coverage. Same.

### Deploys
- frontend: `web-00102-v4f` → `web-00103-phl` (TD-01) → `web-00104-d4n` (TD-18). Two deploys, within the per-feature budget.
- backend: `api-00104-qm7` → `api-00105-wwd` (TD-14 refactor; backend has no behavioural change so this could have been deferred but shipped to keep main and prod in sync at sprint close).

### Roadmap status
**The 5-sprint roadmap is complete.** Sprint 12 (User Management UI) → Sprint 13 (Image Storage Migration) → Sprint 14 (Community Photo Uploads) → Sprint 15 (Image Display Polish) → **Sprint 16 (Code-Quality Pass)** all delivered between 2026-04-24 and 2026-04-27.

## Sprint 15 — Image Display Polish (2026-04-26)

**Deployed**: backend `sjktconnect-api-00104-qm7`, frontend `sjktconnect-web-00102-v4f`. Migration `outreach.0005_add_caption` applied on prod Supabase.

Fourth sprint of the 5-sprint roadmap. Adds a per-image caption that surfaces in a full-screen lightbox on public school pages and an inline editor in the admin Image Manager. Hotfixes during the sprint addressed (a) the public hero showing the placeholder house emoji even for schools with valid photos, (b) the Edit School Data button persisting after sign-out, and (c) the Edit + Suggest CTAs both rendering for users who can already edit directly.

### Added
- **`SchoolImage.caption`** — `CharField(max_length=200, blank=True)`. Migration `outreach/0005_add_caption.py`. Surfaced in `SchoolImageSerializer` + `school_images_view` alongside existing `id`.
- **`PATCH /api/v1/schools/<moe_code>/images/<id>/caption/`** — caption editor endpoint. Permission: `IsPhotoApprover` (SUPERADMIN OR bound school admin — same matrix as Sprint 14 hero-pin). 200-char hard cap, type-checked, empty string clears.
- **`POST /api/v1/auth/logout/`** — flushes the Django session. AllowAny + idempotent so a stale session can self-clear without authenticating. Called by `UserMenu` before `next-auth signOut()` to fix the frontend/Django session divergence that left the Edit button visible after sign-out.
- **Frontend `PhotoLightbox`** component — wraps `yet-another-react-lightbox` (~15 KB gzipped) with the Captions plugin. Lazy-imported via `next/dynamic` in `SchoolImage.tsx` so the lib loads on first click and stays out of SSR.
- **`SchoolImage` gallery interactions**: hero click opens lightbox; thumbnails switch hero on single click and open the lightbox on double-click; "View all N photos" overlay button appears top-right when total > 5.
- **`ImageManager` inline caption editor**: per-image textarea + char counter + Save/Cancel + optimistic update via `updateImageCaption()`.
- **`scripts/audit_image_counts.py`** — promoted from a throwaway helper. Walks the public API to find schools with >N images. Useful for validating the "View all N photos" overlay and harvester coverage spot-checks.

### Changed
- **`SchoolListSerializer.get_image_url`**: returns `primary.display_url` instead of `primary.image_url`. The legacy raw field is empty for Sprint-13-migrated rows, so search results were carrying `image_url=""`. Combined with a too-loose `!== undefined` guard in `SchoolMarkers` this caused the map InfoWindow to skip the lazy detail-fetch and render the placeholder forever. Guard tightened to a truthy check (defence in depth).
- **`EditSchoolLink`** + **`SuggestButton`** — both now subscribe to `useSession()` status and re-fetch `/me` on every transition. Fixes two visibility bugs:
  - *Sign-out:* Edit button hides immediately without a hard refresh.
  - *Sign-in:* Edit button appears as soon as the JWT lands, not only after the next page load.
  - *Role overlap:* `SuggestButton` now hides for SUPERADMIN and for the bound admin of the school being viewed, so the two CTAs become mutually exclusive: SUPERADMIN sees Edit only; a bound admin sees Edit on their school + Suggest on others; MODERATORs and regular users see Suggest only; signed-out users see neither.
- **`PhotoLightbox`** slide rendering: passes only `description` (not both `title` and `description`), so the Captions plugin no longer renders the caption twice.
- **Public hero**: caption overlay removed. It collided with the bottom thumbnail strip on schools with 6+ photos (e.g. SJK(T) Vivekananda). Caption is preserved in the lightbox and the admin editor — matching Google Photos / Flickr index-vs-detail UX convention.

### Tests
- 8 new backend tests in `community/tests/test_image_caption.py` (happy path, 5-role permission matrix, 200-char reject, type-check, clear via empty string).
- 2 new backend tests for the logout flush endpoint (clears session + idempotent on already-empty session).
- 5 net new frontend tests across `ImageManager.test.tsx` (caption editor) and `SchoolImage.test.tsx` (lightbox open paths). One unit test removed (`PhotoLightbox.test.tsx` — `yet-another-react-lightbox` is ESM-only and Jest doesn't transform `node_modules` by default; the wrapper is exercised via `SchoolImage` integration tests).
- Final tally: **1155 backend + 285 frontend tests**. SubscribeForm flake remains (TD-15).

### Migrations
- `outreach/0005_add_caption.py` — Add `SchoolImage.caption` (CharField max_length=200, blank=True).

### Known issues
- **TD-18** — After sign-in on a school page, the Edit / Suggest CTA only appears after a manual page refresh. Sign-out reactivity works (this sprint's hotfix). Suspected to share root cause with TD-01 (Auth.js v5 + Next 16 cookie round-trip). Deferred to Sprint 16.

## Sprint 14 — Community Photo Uploads (2026-04-26)

**Deployed**: backend `sjktconnect-api-00101-klw`, frontend `sjktconnect-web-00094-gqx`. Migration `community.0002_drop_image_add_pending` applied on prod Supabase.

Third sprint of the 5-sprint roadmap. Replaces the Sprint 8.2 base64-into-BinaryField photo flow with multipart uploads → Supabase Storage. Adds Pillow validation, perceptual-hash dedup, daily throttling, a 20-photo cap on approve, a hero-pin endpoint, and a `IsPhotoApprover` permission that excludes MODERATORs from photo decisions. Resolves TD-07 + TD-09 + TD-16 (suggestions-page portion).

### Added
- **`backend/outreach/services/image_processor.py`**: Pillow-backed validate → strip EXIF → resize to 1600px → compute pHash. Stable error codes (`too_large`, `too_small`, `unsupported_format`, `invalid_image`, `empty`).
- **`POST /api/v1/schools/<moe_code>/suggestions/photo/`**: multipart upload endpoint. Validation (≤5 MB, JPEG/PNG/WebP, ≥640×400), pHash dedup against `(school + user)` PENDING/APPROVED uploads, scoped throttling. Creates `Suggestion(type=PHOTO_UPLOAD, status=PENDING)` with bytes in `Suggestion.pending_image` (Supabase Storage, UUID path).
- **`POST /api/v1/schools/<moe_code>/images/<id>/pin/`**: makes a photo the school's hero (`is_primary=True`). Atomically clears `is_primary` on siblings. Permission: `IsPhotoApprover`.
- **`backend/community/api/permissions.py` — `IsPhotoApprover`**: SUPERADMIN OR `admin_school_id == school_id`. MODERATOR explicitly NOT a photo approver (Image Library plan Decision #5).
- **`backend/community/api/throttles.py`**: `PhotoUploadUserThrottle` (5/day) + `PhotoUploadSchoolThrottle` (20/day). Configured via `REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]`.
- **`Suggestion.pending_image` ImageField** + **`Suggestion.phash` indexed CharField**: replaces the dropped `image` BinaryField. Migration `community/0002_drop_image_add_pending.py`.
- **`SuggestionListSerializer.pending_image_url`**: surfaces the staged Storage URL to authorised viewers via the moderation queue API.
- **Frontend `SuggestForm`**: file picker + preview + client-side size/format/dimensions check + multipart `FormData` POST to `uploadSchoolPhoto()`. Typed error surfacing for `duplicate`, `too_large`, `too_small`, `unsupported_format`, `throttled`.
- **Frontend `ImageManager`**: ⭐ Make hero button per image; current hero shows ★ Hero badge + disabled.
- **Frontend `ModerationQueue`**: photo preview rendered inline from `pending_image_url`; school name as link to `/school/<moe_code>` (target=_blank); 20-photo `slot_full` 409 surfaces as an inline amber banner; reject reason now multi-line textarea.
- **`PhotoUploadError` typed Error class** in `lib/api.ts` with `setPrototypeOf` fix for ES5-target instanceof checks.

### Changed
- **`approve_suggestion` service**: PHOTO_UPLOAD path now reads bytes from `Suggestion.pending_image`, copies them into a fresh `SchoolImage.image_file` under `schools/<moe>/`, then clears the pending file. Cap enforcement remains in the API view (`PHOTO_CAP_PER_SCHOOL = 20`); service is the defence in depth.
- **`reject_suggestion` service**: PHOTO_UPLOAD now deletes the staged file from Supabase Storage best-effort.
- **`approveSuggestion` (frontend)**: split into `approvePhotoSuggestion()` which surfaces 409 `slot_full` as a typed result.
- **`createSuggestion` signature** narrowed to `DATA_CORRECTION | NOTE` — photos use `uploadSchoolPhoto()`.
- **`SchoolImage.image_url`** in the school-images list endpoint now returns `display_url` (Sprint 13 backwards-compat property), so the frontend doesn't need to know about the dual-field model.

### Removed
- **`Suggestion.image` BinaryField** (migration 0002 `drop_image_add_pending`). Sprint 13's COMMUNITY pass already migrated existing bytes to SchoolImage.
- **`/api/v1/suggestions/<id>/image/` endpoint** + `suggestion_image_view`. Bytes are now served by Supabase Storage directly via `display_url` / `pending_image_url`.

### Tests
- 28 new backend tests across `community/tests/test_photo_upload.py` (validation matrix, pHash dedup, throttle, owner-school rejected), `test_photo_approve_cap.py` (20-cap 409, reject deletes file), `test_photo_approver_perm.py` (5-role matrix incl. MODERATOR-rejected case), `test_pin_image.py` (atomic primary swap, permission, foreign-image 404). Existing `test_approval.py` rewritten for the new flow.
- 5 new frontend tests across `__tests__/components/SuggestForm.test.tsx` (client-side type/size rejection, backend duplicate error message), `ImageManager.test.tsx` (hero badge state, pin button click + optimistic update), `ModerationQueue.test.tsx` (photo preview, school link, slot-full banner).
- Final tally: 1145 backend + 286 frontend tests (`SubscribeForm` flake remains, TD-15).

### Migrations
- `community/0002_drop_image_add_pending.py` — Remove `image` BinaryField; add `pending_image` ImageField + `phash` CharField (indexed).

## Sprint 13 — Image Storage Migration (2026-04-25 → 2026-04-26)

Second sprint of the 5-sprint roadmap. Replaces volatile Google Places URLs with persistent bytes in Supabase Storage. Single coherent deliverable, shipped across two sessions because the harvest + migration steps took ~30 min wall time.

### Added
- **Supabase Storage bucket `school-images`** (public read, authenticated write, 5 MB limit, JPEG/PNG/WebP). Created via Supabase dashboard.
- **`django-storages[boto3]>=1.14`** + **`Pillow>=10.0`** in `requirements.txt`.
- **`STORAGES["default"]`** in `backend/sjktconnect/settings/base.py` configured to `storages.backends.s3.S3Storage` when `SUPABASE_STORAGE_*` env vars are present (5 vars: `ENDPOINT`, `REGION`, `BUCKET`, `ACCESS_KEY`, `SECRET_KEY`). Falls back to `FileSystemStorage` for local dev / tests.
- **`SchoolImage.image_file = ImageField(upload_to="schools/<moe_code>/")`** alongside the legacy `image_url` field. Migration `outreach/0004_add_image_file_field.py` adds the column. Existing `image_url` field made `blank=True`.
- **`SchoolImage.display_url` property**: returns `image_file.url` if set, falls back to `image_url`. Centralises the URL-resolution logic so serializers don't need to branch.
- **`migrate_images_to_storage` management command**: idempotent, resumable, source-filterable. Downloads each unmigrated SchoolImage's `image_url` and uploads bytes to Supabase. Batched commits + `connection.close()` every 50 to avoid Supabase pooler write drops.
- **`MEDIA_ROOT = BASE_DIR / "media"`** in base.py + `backend/media/` in `.gitignore` — so local FileSystemStorage fallback writes don't leak into the repo.
- **Lazy-fetch on `SchoolMarkers` InfoWindow**: when a marker is clicked, fetch `/api/v1/schools/<moe_code>/` to populate `image_url` + `teacher_count` (fields trimmed from the `/schools/map/` endpoint by Sprint 8.3 egress fix). InfoWindow now shows the real hero photo + ratio after a ~200ms detail-fetch delay.
- **11 new backend tests**: `test_models.SchoolImageDisplayUrlTest` (3 — display_url fallback logic), `test_migrate_command` (6 — dry-run, success, idempotent, dead URL, source filter, empty-set), additional `test_image_harvester` cases for byte-based flow + skipped-failed-download scenario.

### Changed
- **`harvest_satellite_image`** + **`harvest_places_images`** in `outreach/services/image_harvester.py`: download bytes from Google APIs and write via `image_file.save()` instead of storing the API-key-bearing URL. New helper `_download_bytes()` with 5 MB cap. Per-school upload path: `schools/<moe_code>/<source>-<uuid>.<ext>`. Existing `image_url` field no longer populated by harvests.
- **`SchoolDetailSerializer.get_image_url`** + **`SchoolImageSerializer.image_url`**: both use `obj.display_url` so frontend gets Supabase URLs after migration without code changes.
- **`production.py`**: STORAGES uses `STORAGES["staticfiles"] = {...}` augmentation (don't replace the dict) so base.py's Supabase media config survives.
- All existing `test_image_harvester` tests rewritten for byte-based flow (`mock requests.get` + `iter_content`).

### Fixed
- **TD-05** (broken Places URLs on every school page): all 1009 prior PLACES rows replaced with re-harvested bytes uploaded to Supabase. Verified `curl -sI https://kafuxsinrbqafvarckxu.storage.supabase.co/storage/v1/object/public/school-images/...` returns 200 + image/jpeg.
- **TD-06** (Supabase egress regression): no more browser retries to dead `places.googleapis.com/.../media` URLs. The 5–10× egress baseline should drop to <100 MB/day target as cached responses expire.
- **TD-13** (`uploaded_by` NULL on harvester images): no actionable code change — confirmed semantic intent (NULL = harvester-sourced, set = community-uploaded). Closed with documentation in code.

### Production migration ops (executed during sprint)
- `harvest_school_images` (full, 528 schools) on 2026-04-25 → 1005 PLACES rows created. Cost: ~US$14 in Places API search + photo-fetch calls (within RM10/month budget; spread across cycle).
- `harvest_school_images --source satellite` on 2026-04-25 → 528 SATELLITE rows created. Cost: ~US$1 in Static Maps calls. Required the *frontend* `AIzaSyAx...` API key (the Places-only `AIzaSyCk...` key returned 403 for Static Maps).
- `migrate_images_to_storage` on 2026-04-26 → 1 COMMUNITY row migrated.
- Manual cleanup: 5 stuck rows deleted (4 PLACES with no current Google photos, 1 COMMUNITY with broken pre-`BACKEND_URL` relative URL).
- **Final state: 1534 SchoolImage rows, 1534 with `image_file` (100%)**.

### Tests
- Backend: 1106 → 1117 (+11). Frontend: 258 (unchanged — no new component tests for SchoolMarkers, that pre-existed without coverage).

### Deployed revisions
- Backend: `sjktconnect-api-00098-hsr` → `sjktconnect-api-00100-7x2` (Sprint 13 backend, then env-var update revision `00099-jtr`).
- Frontend: `sjktconnect-web-00092-7ts` → `sjktconnect-web-00093-p8c` (lazy-fetch InfoWindow fix).

## Sprint 12 — User Management UI (2026-04-24)

First sprint of the 5-sprint roadmap agreed via `implementation-planning.md`. Single coherent deliverable, shipped in one session.

### Added
- **Backend `GET /api/v1/auth/admin/users/`** — SUPERADMIN-only paginated list. Filters: `role`, `has_admin_school`, `is_active`, `search` (matches display_name, email, moe_code, school short_name).
- **Backend `PATCH /api/v1/auth/admin/users/<id>/`** — SUPERADMIN-only. Updates `role`, `admin_school` (by moe_code string or null), `is_active`. Assigning a school swaps the existing admin off (one school, one admin).
- **Backend `DELETE /api/v1/auth/admin/users/<id>/`** — soft delete via `is_active=False`.
- **Self-demotion safety checks** on PATCH + DELETE: SUPERADMIN cannot change own role away from SUPERADMIN, cannot deactivate own account.
- **Backend `PATCH /api/v1/auth/me/`** (self-service) — accepts `display_name` update only; other fields ignored at serializer level.
- **New serializers** in `accounts/api/serializers.py`: `UserProfileUpdateSerializer`, `UserProfileAdminListSerializer`, `UserProfileAdminUpdateSerializer`.
- **Frontend `/dashboard/users` page** — SUPERADMIN-gated list UI with filter controls (role, school-admin, status, search).
- **New components**: `UserManagementTable`, `RoleChangeModal`, `SchoolAssignModal` (searchable school picker via existing `searchEntities()`).
- **`UserMenu` dropdown** — new "User Management" link visible only for SUPERADMIN role.
- **Profile page `/profile`** — editable display name (inline edit + save/cancel + error surfacing).
- **30 new backend tests** in `accounts/tests/test_admin_users.py` covering permission matrix, self-demotion, filters, validation.
- **i18n**: en/ta/ms `userManagement.*` + `auth.*` additions (edit, save, saving, cancel, userManagement, noSchoolHint, etc.).

### Changed
- `MeView` extended to accept PATCH (display_name update) alongside existing GET.
- Removed broken "Claim your school" CTA on profile page (pointed to deleted `/claim`); replaced with `noSchoolHint` text explaining auto-claim via `@moe.edu.my` sign-in.

### Fixed
- **Sign-in broken after deploy (Sprint 12 deploy side-effect)**: Auth.js v5 beta + Next 16 state/PKCE cookie round-trip regressed. Removed duplicate `NEXTAUTH_SECRET`/`NEXTAUTH_URL` env vars in favour of Auth.js v5 `AUTH_SECRET` + `AUTH_URL` conventions. Still broken → reverted `checks: ["pkce", "state"]` to `checks: []` as pragmatic unblock (same workaround as pre-Sprint-11a Phase 2). **TD-01 re-opened** with detailed root cause + Sprint 16 follow-up note in the code.

### Security
- **TD-01 re-opened** (regression): Auth.js v5 beta.30 + Next 16 state/PKCE cookie round-trip broken. `checks: []` workaround reinstated. Root cause investigation scheduled for Sprint 16.

### Deployed revisions
- Backend: `sjktconnect-api-00097-5k7` → `sjktconnect-api-00098-hsr`
- Frontend: `sjktconnect-web-00088-kz2` → `sjktconnect-web-00092-7ts` (4 revisions during the sign-in debug loop)

### Tests
- Backend: 1076 → 1106 (+30). Frontend: 258 (unchanged).

### Prod community growth since Sprint 11a close
- UserProfile count: 2 → 5 (3 community sign-ins without any promotion): khathijah123mohamedrasul@gmail.com, deneshkumaar@mitra.gov.my, rinishhaa@tamilfoundation.org. tamiliam@gmail.com now has 11 points from earlier test suggestions.

## User Management Sprint — Part A (Sprint 11a, 2026-04-23 → 2026-04-24)

Four-phase sprint covering auth foundation + magic-link removal + Next.js major upgrade. Phase 5 (`/dashboard/users` SUPERADMIN UI + profile page additions) deferred to Sprint 11b.

### Phase 1 — Cloudflare reverse proxy adoption
- Cloudflare set up as DNS + proxy for `tamilschool.org`. Nameservers switched at Exabytes registrar to `cody.ns.cloudflare.com` + `oaklyn.ns.cloudflare.com`. Cloud Run domain mapping kept active for rollback.
- New subdomain `api.tamilschool.org` mapped to Cloud Run `sjktconnect-api` via Google-managed SSL (verified domain ownership in Search Console; cert issued in ~10 min).
- DNS table cleaned: DKIM CNAMEs (`brevo1._domainkey`, `brevo2._domainkey`) set to **DNS only** (NOT proxied) so Brevo email auth keeps working. MX records DNS only. A records + `www` + `api` proxied through Cloudflare.
- SSL/TLS mode: Full (strict).
- Backend env vars updated: `ALLOWED_HOSTS` + `CSRF_TRUSTED_ORIGINS` add `api.tamilschool.org`.
- Frontend Dockerfile rebuilt with `NEXT_PUBLIC_API_URL=https://api.tamilschool.org` baked in (Next.js NEXT_PUBLIC_* are compile-time, not runtime).

### Phase 2 — Restore OAuth security + remove cross-domain workarounds
- Removed `SESSION_COOKIE_SAMESITE = "None"` + `CSRF_COOKIE_SAMESITE = "None"` from `production.py`. Default `SameSite=Lax` is correct now that frontend + backend are same-site (both subdomains of `tamilschool.org`).
- Restored `checks: ["pkce", "state"]` in `frontend/lib/auth.ts` (NextAuth Google provider). The `checks: []` workaround that had been live since 2026-03-11 is gone.

### Phase 3 — Delete magic-link, add auto-claim, redesign claim UX
- Migration `accounts/0003`: drop `MagicLinkToken` + `SchoolContact` tables.
- Migration `schools/0009`: add `school.claimed_at` field.
- New auto-claim logic in `GoogleAuthView`: if Google email ends with `@moe.edu.my`, extract the moe_code part and bind `profile.admin_school` automatically. Sets `school.claimed_at`. Idempotent. Skipped if school already claimed by another profile or if profile already has a school.
- `SchoolEditView` + `SchoolConfirmView` migrated from `IsMagicLinkAuthenticated` to `IsProfileAuthenticated` + `admin_school` check (SUPERADMIN bypass). The Edit School Data button on every school page is now usable.
- Deleted: `accounts/services/token.py`, `accounts/services/email.py`, `IsMagicLinkAuthenticated`, `RequestMagicLinkView`, `VerifyTokenView`, `LinkSchoolView`, all magic-link tests.
- Frontend deletions: `/claim/page.tsx`, `/claim/verify/[token]/page.tsx`, `ClaimButton.tsx`, `ClaimForm.tsx`, `requestMagicLink`/`verifyMagicLink` from `lib/api.ts`, `MagicLinkResponse` type.
- New `EmailClaimIndicator` component renders inline next to the email in the School Details card — Google-style. Three states:
  - **Claimed**: small green ✓ Verified pill (click expands tooltip with claim + verify dates).
  - **Unclaimed, signed-out**: small "Claim this page" text link → opens modal with "Sign in with Google to claim" CTA.
  - **Unclaimed, signed in as wrong account**: same link → modal explains "Signed in as X, only the school's MOE email can claim" + sign-out button.
  - Modal has "Copy link to share" secondary action for visitors who aren't the HM.
- Removed `ClaimCallout` (the original big blue banner) and `VerifiedBadge` (next to school name) — replaced by inline indicator. School page is clean by default.
- Verified mechanism: `dig MX moe.edu.my` → all 5 records resolve to `*.ASPMX.L.GOOGLE.COM`. Every `<moe_code>@moe.edu.my` IS a Google Workspace account; sign-in proves access to the same inbox the magic-link mechanism would have emailed.

### Phase 4 — Next 14 → 16 upgrade
- `next` 14.2.x → 16.2.4 (skipped 15 entirely; @latest is 16).
- Migrated 5 app-router files to new async `params` API: `layout.tsx` (locale), `school/[moe_code]/page.tsx`, `constituency/[code]/page.tsx`, `dun/[id]/page.tsx`, plus their `generateMetadata` functions.
- Added `frontend/global.d.ts` shim: Next 16's auto-generated `.next/types/validator.ts` references `React.ComponentType` unqualified, but `jsx: "react-jsx"` doesn't expose React in global scope. Shim re-exports the namespace.
- Cleaned up stale `user.school_moe_code` usage in `school/[moe_code]/edit/page.tsx` (exposed by type-check; replaced with `user.admin_school?.moe_code` + SUPERADMIN bypass).
- Explicit `Response` type on `app/sitemap.ts` `fetch()` to satisfy Next 16's stricter inference.
- Kept `ignoreBuildErrors: true` in `next.config.js` with clearer comment — pre-existing implicit-any issues in `BoundaryMap` etc. are out of scope for an upgrade sprint.
- npm audit: Next CVE (GHSA-9g9p-9gw9-jx7f) cleared. 2 transitive issues remain (`brace-expansion` moderate, `picomatch` high).

### Tests
- Backend: 1076 (was 1109). Net change: -33 (deleted magic-link tests across `test_api.py`, `test_models.py`, `test_link_school.py`, `test_me_endpoint.py`, `test_edit_api.py`, `test_dashboard.py`) + 7 (new `test_auto_claim.py` covering the auto-claim matrix) + 5 (rewritten `test_edit_api.py` for UserProfile-based auth) + 1 (new `test_me_endpoint.py` inactive-profile test) − tests that were collapsed.
- Frontend: 258 (was 271). Net change: -8 (deleted `ClaimButton.test.tsx`, `ClaimForm.test.tsx`) - 5 (rewritten api-auth + EditSchoolLink tests under new shape).

### Resolved tech debt
- TD-01 OAuth checks restored
- TD-02 Magic-link deleted; auto-claim live
- TD-04 SameSite=None workaround removed
- TD-10 partially closed (Next upgraded; 2 transitive deps remain)

### Deferred to Sprint 11b
- Phase 5: `/dashboard/users` SUPERADMIN UI + profile page additions. Not blocking — SUPERADMIN can manage roles via Django admin (`/admin/accounts/userprofile/`) for now.

### Deployed revisions
- Backend: `sjktconnect-api-00094-rvm` → `sjktconnect-api-00097-5k7`
- Frontend: `sjktconnect-web-00081-jzn` → `sjktconnect-web-00088-XXX` (Phase 4)

## Audit & Community Auth Sprint (2026-04-22 → 2026-04-23)

Two-session sprint: unblocked Google OAuth for non-tamilfoundation.org accounts, fixed three pre-existing bugs in the Sprint 8.2 suggestion workflow end-to-end, ran the project's first full-codebase audit since Sprint 0.3, and paid down three tech debt items surfaced by the audit.

### Added
- **`docs/tech-debt.md`** — tech debt register with 15 entries (what / why / blocks / cost-to-fix format). Living document, triaged each sprint close.
- **`docs/plans/2026-04-22-image-library-sprint-plan.md`** — Sprint 9 plan: replace volatile Google Places photo URLs with Supabase Storage, add community upload flow with SUPERADMIN/school-admin approval, 20-photo hard cap, lightbox modal, moderation queue UX improvements.
- **`BACKEND_URL` setting** (`backend/sjktconnect/settings/base.py`) — absolute URL used when building image references that must resolve from the frontend domain. Set on Cloud Run backend via `--update-env-vars`.
- **Prod-DB guard** in `backend/manage.py` — refuses destructive commands (`migrate`, `flush`, `import_*`, `harvest_*`, etc.) when `DATABASE_URL` points to a non-local host, unless `SJKTCONNECT_ALLOW_PROD_DB=1` or running on Cloud Run (`K_SERVICE` set). Read-only commands unchanged.
- **Explicit DRF `DEFAULT_AUTHENTICATION_CLASSES = [SessionAuthentication]`** pin — prevents silent CSRF regression if `TokenAuthentication` is added later, which would bypass `SameSite=None`'s compensating control.
- **3 new backend tests** in `community/tests/test_approval.py` — cover approved-image public access, pending-image anonymous block, pending-image uploader access.

### Changed
- **OAuth consent screen** → External + In Production. `tamiliam@gmail.com` (and any Google account) can now sign in. Renamed from "SJK(T) Connect Feedback" to "SJK(T) Connect".
- **`admin@tamilfoundation.org` role** → SUPERADMIN (was USER) — unlocks the Dashboard link + moderation queue in the UserMenu.
- **Session cookies** — `SESSION_COOKIE_SAMESITE = "None"` + `CSRF_COOKIE_SAMESITE = "None"` added to production settings. Required for cross-origin `fetch()` from `tamilschool.org` to `sjktconnect-api-*.run.app` to carry the session cookie. Documented as a temporary workaround pending Cloudflare proxy adoption.
- **`next-intl`** upgraded from 4.8.3 → 4.9.1+ (clears open-redirect advisory).

### Fixed
- **Photo upload silently failed** (Sprint 8.2 bug): `FileReader.readAsDataURL` returns a full `data:image/jpeg;base64,...` string, but backend's `base64.b64decode()` cannot parse the prefix. `frontend/components/SuggestForm.tsx` now strips the prefix before storing, then prepends it for the preview `<img>` tag.
- **Suggestion submit error swallowed**: `catch {}` block replaced the server's real error message with a generic "Failed to submit suggestion". Now logs to console and surfaces the actual DRF detail text.
- **Community-approved photos rendered broken** (Sprint 8.2 bug): `_apply_photo_upload` set `SchoolImage.image_url` to relative path `/api/v1/suggestions/<pk>/image/`, which the browser resolved against `tamilschool.org` (not the `.run.app` backend). Now uses absolute URL via `settings.BACKEND_URL`. Patched stale SchoolImage 1545 record directly in prod DB.
- **Non-approved suggestion images publicly enumerable** (security, audit finding 2+5): `suggestion_image_view` served any `PENDING`/`REJECTED` suggestion's uploaded image to anyone who guessed the pk, leaking photos that were never approved. Now requires viewer to be uploader / school admin / MODERATOR / SUPERADMIN. APPROVED suggestions remain public (SchoolImage rows point here).

### Security
- **Audit finding 2 + 5** patched — see Fixed section above.
- **3 findings deferred** — logged in `docs/tech-debt.md`:
  - TD-01 (OAuth `checks: []` workaround, prerequisite for Sprint 11 Cloudflare)
  - TD-04 (`SameSite=None` workaround, resolves with same Cloudflare migration)
  - TD-09 (hardcoded `image/png` Content-Type, resolves with Sprint 9)

### Audit Summary (item 12 from CLAUDE.md Next Sprint list)
- **Dependency audit**: backend pip-audit clean; frontend npm audit showed 3 moderate issues — `next-intl` upgraded, `next` + `picomatch` deferred (we don't use `remotePatterns`, so not currently exploitable).
- **Test coverage**: 1109 backend tests, 89% line coverage (excluding one-off management commands which are 0% by design). Frontend 271 tests pass (excluding 2 pre-existing flakies).
- **Security review**: 5 findings — 2 patched this sprint, 3 deferred to Sprint 9 / Sprint 11 (all tracked in `docs/tech-debt.md`).
- **Code simplification scan**: magic-link auth system (Sprint 1.6) is fully dormant (0 contacts, 0 tokens ever issued) but still wired into `SchoolEditView` + `SchoolConfirmView`, meaning the edit-school button on every school page is unusable. Resolves with Sprint 11.
- **Tech debt register**: 15 items catalogued, 3 resolved this sprint (TD-03, TD-08, TD-10-partial).

### Deployed revisions
- Backend: `sjktconnect-api-00087` → `sjktconnect-api-00094-rvm`
- Frontend: `sjktconnect-web-00078` → `sjktconnect-web-00081-jzn`

## News Digest & Urgent Alert Fix (2026-04-21)

### Fixed
- **Digest cadence skipped a fortnightly cycle**: `compose_news_digest._should_skip()` and `_get_since_date()` filtered by `audience_filter__category="NEWS_WATCH"`, which matched urgent alerts as well as digests. A Broadcast 68 urgent alert on 7 Apr 2026 caused the 13 Apr digest to be wrongly skipped, and the 20 Apr digest to cover 7–20 Apr instead of 31 Mar – 20 Apr. Root cause: `audience_filter` describes *who* receives a broadcast; *what kind* of broadcast it is was never tracked. Added `Broadcast.kind` field (NEWS_DIGEST / URGENT_ALERT / MONTHLY_BLAST / PARLIAMENT_WATCH / OTHER) + `coverage_start_date` / `coverage_end_date`. All 5 writers now set `kind`. Digest cadence filters by `kind=NEWS_DIGEST` only.
- **Digest coverage off-by-one**: `_get_since_date()` returned the previous broadcast's `created_at`, so each digest re-covered the final day of the previous digest. Now returns `coverage_end_date + 1 day`.
- **Urgency classifier too lenient**: Rewrote the urgency section of `ANALYSIS_PROMPT` in `newswatch/services/news_analyser.py` as a two-step gate (Step 1: three narrow triggers — confirmed closure, active emergency, binding government restriction; Step 2: 7-day action window + primary subject). Added six explicit negative examples including heat-policy announcements and rebuild announcements (the real misclassification from Broadcast 68). Added three positive examples.

### Added
- **Second-pass urgency verification**: When first-pass sets `is_urgent=True`, a narrow verification prompt is called on a fresh Gemini request. If the verifier disagrees, the flag is downgraded and the first-pass reason is logged. Audit trail stored in `ai_raw_response["urgent_verification"]`.
- **Dormant DRAFT-review feature flag**: `URGENT_ALERT_REQUIRE_REVIEW` setting (default `false`). When flipped to `true`, `send_urgent_alerts` creates a DRAFT but does not auto-send — a moderator must approve it from the admin broadcasts queue. Activate with a single `gcloud run jobs update ... --update-env-vars` with no redeploy needed.
- **`clear_stale_urgent_flags` management command**: Clears `is_urgent=True` on articles older than 30 days that never triggered an alert. Preserves articles that did fire an alert (historical record).

### Migration
- **Migration 0006** adds `kind`, `coverage_start_date`, `coverage_end_date` and backfills all existing broadcasts. 12 URGENT_ALERT, 7 NEWS_DIGEST (with coverage dates parsed from subject), 4 MONTHLY_BLAST, 2 OTHER on local DB.

### Investigation
- Full fix plan at `docs/plans/2026-04-21-news-digest-urgent-alert-fix-plan.md`.

## Egress Fix — Supabase Egress Optimisation (2026-03-29)

### Fixed
- **`boundary_wkt` fetched and discarded on every API request**: Django ORM `select_related("constituency", "dun")` was fetching full rows including large WKT polygon data (5-8 KB per row) via PostgreSQL JOINs, then the serializer discarded it. Added `.defer("boundary_wkt")` to 6 non-GeoJSON views: `SchoolListView`, `SchoolDetailView`, `ConstituencyListView`, `ConstituencyDetailView`, `DUNListView`, `DUNDetailView`. Estimated ~85% reduction in Supabase egress (~1 GB/day eliminated).

### Added
- **Scraper bot IP blocking**: Next.js middleware blocks known scraper IPs (Chrome/91 bot at 88.216.210.27 was generating ~1,413 requests/day).
- **robots.txt bot exclusions**: Blocked AhrefsBot, GPTBot, OAI-SearchBot, Amazonbot, and ClaudeBot — these generated ~95% of frontend traffic but provided no value.

### Investigation
- Full egress investigation report at `docs/egress-investigation-report.md`.
- Root cause: 3 compounding factors — (1) ORM fetching unused boundary_wkt, (2) 95% bot traffic, (3) Next.js ISR cache broken on Cloud Run ephemeral containers.

## Sprint 8.6 — Email Quality & Spam Cleanup (2026-03-28)

### Fixed
- **Hero image bytes in email HTML**: `compose_news_digest` and `compose_parliament_watch` passed raw image bytes directly as `hero_image_url` template variable, causing ~2.5 MB of binary data to be HTML-escaped into `<img src="...">`. Now follows the correct two-pass pattern: save bytes to `broadcast.hero_image`, re-render template with API URL.
- **Hard bounce threshold reduced to 1**: Subscribers are now immediately deactivated on first hard bounce (was 3). Dead addresses rarely recover.

### Added
- **Contact form honeypot**: Hidden `website` field on both backend and frontend. Bots that fill it get a silent 200 response; no email is sent.

### Removed
- **37 spam subscribers deleted**: Bot-injected subscribers with random-string names purged from database.
- **44 hard-bounced subscribers deactivated**: Bulk-import contacts with dead email addresses (old Yahoo, Hotmail, corporate) deactivated based on Brevo bounce logs.

## Sprint 8.5 — Brevo Webhook Integration (2026-03-28)

### Added
- **Brevo webhook endpoint**: `POST /api/v1/webhooks/brevo/` receives delivery events (delivered, opened, clicked, hard/soft bounce, spam, unsubscribed) from Brevo transactional API.
- **Engagement tracking fields**: `delivered_at`, `opened_at`, `open_count`, `clicked_at`, `click_count`, `bounce_type` on BroadcastRecipient model.
- **New delivery statuses**: `DELIVERED`, `BOUNCED`, `SPAM` added to BroadcastRecipient.DeliveryStatus.
- **Bounce management**: `bounce_count` on Subscriber model. Auto-deactivation after 1 hard bounce (reduced from 3 in Sprint 8.6).
- **Brevo-side unsubscribe sync**: Unsubscribes triggered in Brevo are mirrored back to the subscriber database.
- **Optional HMAC signature verification**: Set `BREVO_WEBHOOK_SECRET` env var for request authentication.
- 19 new backend tests (webhook service + API endpoint).

## Sprint 8.4 — SEO Improvements (2026-03-28)

### Added
- **Hreflang alternate links**: All 22 pages now include `<link rel="alternate" hreflang="...">` tags for EN/TA/MS locales, fixing 69 "Duplicate without user-selected canonical" errors in Google Search Console.
- **Canonical URLs**: Self-referencing `<link rel="canonical">` on all pages to prevent duplicate content indexing.
- **Dynamic sitemap.xml**: Auto-generated sitemap with locale alternates for all static pages + 528 school pages + constituency pages. Located at `/sitemap.xml`.
- **robots.txt**: Blocks `/api/`, `/dashboard/`, `/claim/verify/` paths from crawlers. Points to sitemap.
- **`lib/seo.ts` helper**: `buildAlternates()` function for consistent hreflang/canonical generation across all pages.

### Changed
- **School page meta titles**: Now follow "SJK(T) Name | 450 Students, Grade A | Selangor" format for richer SERP display.
- **School page meta descriptions**: Now include city/location, preschool/special ed availability, and a call to action.
- **Constituency page meta titles**: Now follow "Name (Code) | 5 Tamil Schools | State" format.

## Sprint 8.3 — Supabase Egress Optimisation (2026-03-28)

### Added
- **School Map API endpoint**: `GET /api/v1/schools/map/` — returns all active schools with 10 minimal fields (~50 KB vs ~550 KB from SchoolListView). Non-paginated, single response.
- **`SchoolMapSerializer`**: Lightweight serializer with moe_code, short_name, gps_lat, gps_lng, enrolment, preschool_enrolment, special_enrolment, assistance_type, location_type, state.
- **`fetchMapSchools()`** in frontend API client — calls the new lightweight endpoint.
- **`subscriber_ids` audience filter** in broadcasts — enables targeting specific subscriber IDs for batch welcome emails.

### Changed
- **Homepage now fetches school data server-side** with ISR (revalidate every 24 hours). Previously every visitor triggered a client-side fetch to Supabase. Now Supabase is hit once per day regardless of visitor count.
- **SchoolMap component** accepts `initialSchools` prop from server instead of fetching client-side. Removed `useEffect` fetch, loading spinner, and error overlay.
- **News page revalidation** changed from 5 minutes to 24 hours (news arrives ~1-2 per week).
- **`send_welcome_email` command** rewritten to track already-sent recipients, enabling batch 2 sends without duplicates.

### Fixed
- **Supabase free tier egress exceeded** (20 GB vs 5 GB quota). Root cause: every page visit fetched all 528 schools client-side. With ISR, egress drops ~1000x.

## Sprint 8.2 — Suggestion Workflow (2026-03-11)

### Added
- **Community app**: New `community` Django app with Suggestion model (DATA_CORRECTION, PHOTO_UPLOAD, NOTE types; PENDING/APPROVED/REJECTED statuses).
- **Suggestion API**: `POST/GET /api/v1/schools/<moe_code>/suggestions/` — create and list suggestions. Validates suggestible fields, snapshots current values, handles base64 image upload. Blocks own-school suggestions.
- **Moderation API**: `GET /api/v1/suggestions/pending/` (queue), `POST /api/v1/suggestions/<id>/approve/` and `/reject/` — moderators and school admins review suggestions. Approval auto-applies data corrections to School model and creates SchoolImage for photo uploads.
- **Points system**: Approved suggestions award points (3 for photos, 2 for data corrections, 1 for notes). No points for own-school suggestions.
- **Image management API**: `GET /api/v1/schools/<moe_code>/images/`, `PUT .../images/reorder/`, `DELETE .../images/<id>/` — school admins and superadmins manage school images (reorder, delete).
- **SchoolImage enhancements**: Added `position` (display order), `uploaded_by` (FK→UserProfile), and `COMMUNITY` source type. Updated ordering to position-first.
- **Suggestion image endpoint**: `GET /api/v1/suggestions/<id>/image/` — serves uploaded PNG from BinaryField.
- **Frontend: Suggest form**: SuggestButton + SuggestForm modal on school pages — type selector, field picker, image upload (base64), note textarea. Auth-gated.
- **Frontend: My Suggestions**: MySuggestions component on profile page — status badges (green/yellow/red), points display, rejection reasons.
- **Frontend: Moderation Queue**: `/dashboard/suggestions` page — pending suggestions table with current-vs-suggested side-by-side, image preview, approve/reject with reason input.
- **Frontend: Image Manager**: `/dashboard/images` page — grid of school images with up/down reorder, delete with confirmation, save order, 10-image cap indicator.
- **Trilingual i18n**: 28 new strings in EN/TA/MS for suggestions namespace.
- **43 new backend tests** (community app: model, API, approval service, image management). **8 new frontend tests** (SuggestButton, MySuggestions, ModerationQueue, ImageManager).

---

## Sprint 8.1 — Community Admin Panel: Auth + Roles Foundation (2026-03-10)

### Added
- **UserProfile model**: Community user profiles with role system (SUPERADMIN/MODERATOR/USER), Google OAuth subject ID, display name, avatar, points, and optional school admin link (OneToOne to School).
- **Google auth endpoint**: `POST /api/v1/auth/google/` — verifies Google ID token, creates/returns UserProfile, sets session. Updates display name and avatar on each login.
- **Updated /me endpoint**: `GET /api/v1/auth/me/` now checks Google auth session first, falls back to magic link session for backward compatibility.
- **Link-school endpoint**: `POST /api/v1/auth/link-school/` — connects a magic-link-verified school to the current Google profile. Validates token, checks school not already claimed (409), creates SchoolContact for backward compatibility.
- **Role-based permission classes**: `IsProfileAuthenticated`, `IsModeratorOrAbove`, `IsSuperAdmin`, `IsSchoolAdminForObject` — alongside existing `IsMagicLinkAuthenticated`.
- **NextAuth.js v5**: Google provider with JWT callback passing ID token to session for backend sync.
- **AuthProvider**: SessionProvider wrapper in layout for client-side auth state.
- **UserMenu component**: Google sign-in/out button in Header, avatar dropdown with role badge, points, profile/dashboard links. Trilingual (EN/TA/MS).
- **Profile page** (`/profile`): Avatar, role badge, points/schools stats, admin school link, claim CTA.
- **Dashboard shell** (`/dashboard`): Role-gated placeholder sections (My School, Moderation Queue, Administration, My Contributions).
- **Settings**: `GOOGLE_OAUTH_CLIENT_ID` env var, `CORS_ALLOW_CREDENTIALS = True`.
- **64 new backend tests** (accounts app: model, auth, /me, link-school, permissions).

---

## Sprint 7.2 — Medium Effort Quality Improvements (2026-03-09)

### Added
- **Fuzzy school matching**: Report linkification now falls back to difflib fuzzy matching (threshold 0.85) for near-miss school names (e.g. "Mentakb" → "Mentakab").
- **MP name normalisation**: `_normalise_mp_name` strips honorific prefixes (YB, Dato', Datuk Seri, Tan Sri, Dr., Puan, etc.) and normalises smart apostrophes for consistent MP matching.
- **Mention-level evaluator**: Deterministic quality check on individual mentions — validates speaker presence in excerpt, flags high significance on short excerpts, checks BUDGET type consistency. No API call. Stores `eval_warnings` and `eval_confidence` on HansardMention.
- **Unified quality loop**: `run_quality_loop()` framework replaces inline while-loops in both brief and report generators. Single reusable function with evaluate/correct/log callbacks.

---

## Sprint 7.1 — Pipeline Quality Quick Wins (2026-03-09)

### Added
- **Speaker verification**: `speaker_verified` boolean on HansardMention validates that Gemini's extracted speaker name appears in the Hansard excerpt (full name or surname fragment matching). Advisory only.
- **Brief correction loop**: Briefs now follow evaluate→correct→re-evaluate pattern (up to 3 attempts). Circuit breaker sets RED flag on exhaustion. Mirrors report quality loop.
- **Evaluator fail-safe**: API errors return AMBER verdict (needs human review) instead of silently passing as GREEN. New `evaluator_error` flag on EvaluationResult.
- **Context staleness warning**: Logs warning when `report-context.json` is >180 days old, prompting update of cabinet/glossary reference data.

### Fixed
- Brief generator tests now properly isolated from environment GEMINI_API_KEY presence.

---

## Bugfix — Electoral Influence & DOSM Links (2026-03-08)

### Fixed
- **DOSM Kawasanku link**: Multi-word state names now title-cased correctly (e.g. `Pulau Pinang` not `Pulau pinang`). Affected Pulau Pinang, Negeri Sembilan, Wilayah Persekutuan Kuala Lumpur.
- **GE15 scraper**: Removed underscore replacement in undi.info API seat names — three-word constituencies (P124 Bandar Tun Razak, P137 Hang Tuah Jaya) were returning empty responses.
- **Electoral influence fallback**: Card now falls back to DOSM census `indian_population` when voter ethnicity data is unavailable (e.g. P018 Kulim-Bandar Baharu).
- **News school matching**: Added fuzzy match (Strategy 6) that collapses doubled consonants to handle Tamil transliteration variants (e.g. Alagar → Allagar). Fixed article 98.
- **Most Mentioned sidebar**: Skip schools with empty `moe_code` to avoid showing unmatched AI guesses.

### Deployed
- Backend revisions 00064–00066, frontend revisions 00054–00055.
- Re-scraped GE15 data for all constituencies — P124 and P137 now populated.
- Ran `rematch_schools` — article 98 now correctly linked to SJK(T) Ladang Allagar (ABD6117).
- Cloud Run job image updated to latest backend.

---

## Sprint 6.3 — Frontend & Polish (2026-03-07)

### Added
- **Brief detail page** (frontend): New Next.js page at `/parliament-watch/sittings/[id]` with breadcrumb navigation, prose-styled body, and back link. `fetchBrief` API function.
- **Brief linking from reports**: `_linkify_briefs` post-processor links sitting dates in report HTML to frontend brief detail pages. Wired into report generation pipeline.
- **BriefsList "Full page" link**: Each sitting brief card now links to its dedicated detail page.
- **i18n**: `backToSittingBriefs` and `viewBriefDetail` keys added in EN/TA/MS.

### Deployed
- Backend and frontend deployed to Cloud Run (sjktconnect-api, sjktconnect-web).

### Tests
- 2 new backend tests (930 total backend, 282 frontend = 1212 total)

---

## Sprint 6.2 — Pipeline Prompts (2026-03-07)

### Changed
- **Mention analysis prompt**: Wired `context_builder` for domain context (cabinet, glossary, taxonomy) injection. Added past tense enforcement for summaries.
- **Brief generator**: Replaced template-based `_build_markdown` with Gemini-powered prose generation (executive summary → details → verbatim quotes, 100-350 words). Falls back to template when `GEMINI_API_KEY` is absent.
- **Report generator prompt**: Restructured with domain context injection (cabinet reference for minister attribution, glossary for acronym expansion, taxonomy definitions for Impact/Stance columns, RPM alignment for Policy Signals). Strengthened minister hallucination guard. Added past tense rule.

### Validated (3rd Meeting 2025 regeneration)
- FLAG-001: No minister hallucination — Zaliha correctly labelled "Minister of Health"
- FLAG-002: Executive responses fully attributed with named ministers and portfolios
- FLAG-003: Past tense used throughout lead and body
- FLAG-004: Acronyms (KPM, MITRA, RPM) expanded on first use
- FLAG-005: Impact categories rebalanced — General Rhetoric reduced from 10/15 to 4/17

### Tests
- 8 new tests (928 total backend): context injection in prompts, past tense enforcement, graceful context failure, Gemini brief prose path, fallback on API error, mention data formatting, report domain context

---

## Sprint 6.1 — Foundation & Data Layer (2026-03-07)

### Added
- **Report context JSON v2.0** (`data/report-context.json`): Curated domain expertise — cabinet ministers, glossary (15 terms), taxonomy definitions (stance/impact/verdict), RPM 2026-2035 commitments, national baseline stats, domain challenges
- **context_builder service** (`parliament/services/context_builder.py`): Loads context JSON + enriches with runtime data (school names, MP portfolios) for Gemini prompt injection
- **MP portfolio field**: CharField on MP model for ministerial portfolio tracking (e.g. "Minister of Education")
- **Portfolio scraper**: Extracts jawatan/portfolio from parlimen.gov.my profile pages
- **executive_response_attribution** criterion added to report quality rubric (Tier 2)
- **"Without Ladang" alias variant**: `seed_aliases` now generates aliases without "Ladang" for 294 estate schools (resolves FLAG-003)
- **WAT workflow**: `context-maintenance.md` — when and how to update the context JSON

### Fixed
- **Mention deduplication**: Changed grouping from (sitting, page) to (sitting, page, speaker) so different speakers on the same page are preserved
- **Donation return URL**: Uses FRONTEND_URL instead of backend URL for Toyyib Pay redirect

### Tests
- 22 new tests (920 total backend)

---

## Full Hansard Rebuild (2026-03-07)

### Changed
- **Complete data wipe and rebuild** of all 15th Parliament Hansard data (Dec 2022 - Mar 2026)
- Wiped all existing mentions, briefs, reports, scorecards, sittings, and meeting records
- Created 13 meeting records covering all 5 terms of the 15th Parliament (was 7 previously)
- Discovered and processed 286 sittings across all meeting periods using `check_new_hansards --start --end`
- 204 mentions extracted with improved pipeline (20-page speaker lookback, tightened Gemini prompt, MP resolver)
- 203 mentions analysed by Gemini (1 unanalysed edge case)
- 67 mentions matched to specific schools
- 53 MP scorecards generated
- 71 sitting briefs generated
- 11 meeting reports with Imagen 4.0 editorial cartoon illustrations

### Fixed
- **2nd Meeting 2025 report bloat** (108KB): Gemini output contained a 109,632-character run of dashes from PDF table separator artefact. Cleared and regenerated (8KB clean report).
- **Git remote URL**: Removed plaintext PAT from remote URL
- **Git author email**: Changed from personal to `admin@tamilfoundation.org` for SJKTConnect repo

### Deployment
- Backend deployed to Cloud Run (revision sjktconnect-api-00058-rvv)
- All rebuilt data live on tamilschool.org

---

## Self-Correcting Report Engine (2026-03-07)

### Added
- **Quality rubric** (`docs/quality/rubric.md`) — permanent 3-tier standard (red lines, quality gates, drift detection)
- **QualityLog model** — records every evaluation cycle with verdict, tier scores, corrections applied
- **quality_flag field** on SittingBrief and ParliamentaryMeeting (GREEN/AMBER/RED)
- **Evaluator service** — separate Gemini API call scoring output against rubric. Fail-open design.
- **Corrector service** — re-prompt with targeted feedback, deterministic code fixes. 3-attempt circuit breaker.
- **School name repairer** — comma removal, filler word removal, fuzzy matching for unlinked names
- **Learner service** — pattern detection across quality logs, quality summary per meeting
- **Brief generator integration** — evaluate/correct loop runs after brief generation
- **Report generator integration** — 3-attempt circuit breaker with quality logging (first tests for report generator)
- **Prompt registry** (`docs/quality/prompt-registry.md`) and **learner patterns** tracking files
- 46 new backend tests (898 total)

---

## Data Quality Fixes (2026-03-06)

### Fixed
- **School name abbreviations**: Data migration normalises inconsistent MOE abbreviations — Ldg→Ladang (95 schools), Sg→Sungai (17), Bkt→Bukit (2), Kg→Kampung (3). 110 schools updated. Aliases re-seeded (2,106 total).
- **Matcher punctuation handling**: Candidate extractor now strips trailing punctuation (commas, semicolons) from school name boundaries. Fixes "SJK(T) Ladang Jeram," failing to match.
- **Matching improvement**: 62/134 mentions now matched (was 38/134 before normalisation). Remaining 72 are generic "SJK(T)" category references without specific school names.

### Deployment
- Backend deployed with migration + matcher fix
- Re-matching run on production (Cloud Run job, 6m33s)
- One-off `sjktconnect-rematch` job cleaned up

---

## Email Infra Follow-up (2026-03-06)

### Added
- **Gmail OAuth for feedback@tamilschool.org** — OAuth2 consent screen (Internal), client credentials, refresh token via OAuth Playground. Env vars set on Cloud Run API + feedback job.
- **`google-api-python-client` + `google-auth`** added to requirements.txt (Gmail API dependencies)
- **Cloud Run job: `sjktconnect-process-feedback`** — fetches Gmail inbox, classifies with Gemini, auto-responds
- **Cloud Scheduler: `sjktconnect-process-feedback`** — 4x daily (8AM/12PM/4PM/8PM MYT)

### Fixed
- **11 failing tests** in broadcasts/feedback modules — tests mocked `genai` but services had early-return guard on `GEMINI_API_KEY` env var. Added `@patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"})` to 4 test classes.

### Deployment
- Backend redeployed with Gmail API dependencies
- Feedback job tested end-to-end: 2 emails fetched, classified (IRRELEVANT), auto-responded

---

## Sprint 5.6: Report Quality Fixes (2026-03-06)

### Fixed
- **PDF text artefacts**: Added `clean_extracted_text()` to normalizer — strips garbled fragments ("ohoh"), double periods (". ."), orphaned punctuation from pdfplumber output. Applied to all stored verbatim quotes and context.
- **Double brackets**: Added post-processing regex `(SJK(T))` → `SJK(T)` in both brief and report generators
- **Blurb extraction**: `BriefsList.tsx` `extractSummary()` now extracts lead paragraph before first heading (was looking for old `<h2>Summary</h2>` format)

### Changed
- **Meeting report prompt rewritten**: Journalistic headline (max 15 words), hook lead paragraph (not "This report covers..."), structured MP Scorecard with predefined taxonomy (Stance: Advocacy/Inquiry/Critical, Impact: Policy Shift/Budget Allocation/Localised Issue/General Rhetoric, Ministerial Response: Commitment Made/Resolved/Deflected/Unanswered)
- **Executive summary extraction**: Now uses lead paragraph instead of Key Findings bullets
- **Social post extraction**: Uses lead paragraph for more informative posts
- **Illustration prompt**: Specifies Tamil Indian ethnicity, positive-only text constraint ("must contain ONLY 'SJK(T)'")

### Tested
- Regenerated all 6 sitting briefs + meeting report + illustration for 1st Meeting 2025 (26 mentions)
- Created 2nd Meeting 2023 record (19 sittings, only 1 Tamil school mention — too sparse for report)
- Verified: no bracket issues, structured scorecard working, journalistic style confirmed

---

## Email Infrastructure Session (2026-03-06)

### Fixed
- **BREVO_API_KEY missing from Cloud Run** — lost during redeployment, confirmation emails silently failing (DEV MODE). Restored on API service + all Cloud Run jobs.
- **Brevo sender verification** — added noreply@tamilschool.org + feedback@tamilschool.org as verified senders (DKIM + DMARC green). Google Workspace mailboxes created.

### Added
- **`--auto-send` flag** on `compose_news_digest` and `compose_monthly_blast` — broadcasts are composed and sent in one step (for cron automation)
- **`send_urgent_alerts` command** — finds approved urgent articles not yet broadcast, composes + sends alerts automatically
- **News auto-reject** — articles with relevance_score < 3 now auto-rejected on analysis (previously only score >= 3 auto-approved, rest stayed PENDING)
- **Cloud Run job: `sjktconnect-news-digest`** — fortnightly digest compose + auto-send
- **Cloud Run job: `sjktconnect-urgent-alerts`** — daily urgent article check + auto-send
- **Cloud Scheduler: `sjktconnect-fortnightly-digest`** — 1st + 3rd Monday, 9:00 AM MYT
- **Cloud Scheduler: `sjktconnect-urgent-alerts`** — daily 9:30 AM MYT

### Changed
- **Monthly blast job** — updated to use `--auto-send` flag + BREVO_API_KEY
- **All Cloud Run jobs** — updated to latest backend image with BREVO_API_KEY + FRONTEND_URL env vars

### Deployment
- Backend deployed to Cloud Run (new image with auto-send commands)
- All 5 Cloud Run jobs updated to new image
- feature/intelligence-reports merged to main (12 commits) and branch deleted

---

## Sprint 5.5: Intelligence Report Quality (2026-03-06)

### Added
- **Editorial cartoon illustrations**: Imagen 4.0 generates editorial cartoons (The Economist/New Yorker style) for meeting reports. Stored as BinaryField, served via `/api/v1/meetings/<id>/illustration/`
- **Illustration API endpoint** (`parliament/api/views.py`): Serves PNG illustration bytes with correct content type
- **`illustration_url` field** on MeetingReport serializer: Builds absolute URL when illustration exists
- **Frontend illustration display** (`MeetingReportsList.tsx`): Shows cartoon when report is expanded

### Changed
- **Meeting report prompt rewritten** (`generate_meeting_reports.py`): Journalistic style — report don't analyse, Key Findings bullets, MP Scorecard table, Policy Signals, What to Watch sections. Word count scaled by sitting count.
- **Sitting brief prompt rewritten** (`regenerate_briefs.py`): JSON response mode (`headline`, `blurb`, `body_md`, `social`). Descriptive headlines instead of generic "X Tamil School Mentions". MP label format: `**Name, Constituency** —`. Verbatim Malay quotes in blockquotes.
- **Gemini thinking budget**: Set `thinking_budget=1024` for both briefs and reports to prevent output truncation (thinking tokens consume output budget)
- **Executive summary extraction**: Plain text from Key Findings bullets instead of HTML
- **Social post extraction**: Strips bullet markers, takes first finding sentence
- **Removed `smarty` markdown extension**: Caused `&rsquo;` raw text in rendered HTML
- **News auto-triage**: Low-relevance articles (score < 3) now auto-rejected instead of staying PENDING

### Fixed
- **Double brackets**: Added prompt rule "Write SJK(T) on its own, never inside extra brackets"
- **Name repetition in briefs**: Added "Do NOT repeat the MP name in the paragraph text"
- **Double-quoted blockquotes**: Added "Do NOT wrap the quote in double-quotes"
- **JSON parse failures**: Added retry logic for Gemini JSON mode (~9% failure rate on first attempt)
- **Blurb running into body**: Instructed Gemini to start body_md with lead paragraph instead of prepending blurb

### Deployment
- Backend deployed to Cloud Run (migration 0005_add_illustration applied)
- Frontend deployed to Cloud Run (illustration display in expanded reports)
- 1st Meeting 2023 (13 Feb – 4 Apr) used as quality test case: 22 sittings, 8 briefs regenerated, 1 meeting report + illustration generated

---

## Sprint 5.2: Historical Rebuild (2026-03-06)

### Added
- **Speaker extraction improvements** (`hansard/pipeline/searcher.py`): YAB, Tun, Menteri Besar title patterns; 2-page backward lookback; Tuan Pengerusi/Puan Pengerusi filtering
- **MP resolver** (`parliament/services/mp_resolver.py`): Cross-references Gemini output against 222 MP records by constituency code/name, MP name substring matching
- **`rebuild_all_hansards` command**: Re-downloads and re-processes all 97 sittings with flags `--dry-run`, `--skip-analysis`, `--skip-matching`, `--include-failed`, `--limit`
- **18 new tests** (17 searcher + 6 resolver + 1 gemini - 6 existing updated)

### Changed
- **Gemini prompt tightened**: explicit significance scale (1-5 with examples), speaker hint from regex extraction, substance-focused summary, "do not guess" party instruction
- **MP resolver wired into pipeline**: `run_hansard_pipeline` now cross-references after Gemini analysis
- **`.env` fix**: em dash in GEMINI_API_KEY comment caused httpx UnicodeEncodeError

### Rebuild Results
- 97/97 sittings re-processed, 0 failures
- 193 mentions extracted (improved speaker extraction)
- 193/193 Gemini AI analysis completed (0 failures)
- 165 mentions with MP name + party (85% fill rate via resolver)
- 32 MP scorecards updated
- Mention types: 102 POLICY, 48 BUDGET, 25 QUESTION, 6 COMMITMENT, 9 OTHER, 3 THROWAWAY

---

## Sprint 5.4: Electoral Influence + GPS Pin Correction (2026-03-06)

### Added
- **GE15 election fields** on Constituency model: winning margin, total voters, Indian voter percentage
- **Electoral influence API**: computed `electoral_influence` field with ratio and verdict (kingmaker/significant/safe_seat)
- **ElectoralInfluenceCard** component: capsule power meter with gradient fills, DOSM Kawasanku + Wikipedia links
- **`scrape_ge15_results` command**: scrapes undi.info API for all 222 constituencies (GE15 margins, GE14 ethnic voter fallback)
- **`import_ge15_results` command**: CSV fallback for GE15 data import
- **`verify_school_pins` command**: Google Places API comparison for all 528 schools, Excel output with clickable links, `--apply` flag with name-match/duplicate safety checks
- **Clickable MiniMap pin**: opens Google Maps in new tab
- **16 new tests** (5 backend + 11 frontend)

### Changed
- **GPS coordinates corrected**: 519 schools updated to Google Places coordinates, 9 manually corrected
- **Constituency page redesign**: larger title, party badge (amber), icons on stat cards, label-above-number layout
- **Breadcrumb**: now links to state-filtered constituencies list
- **Party badge formatting**: space before parenthesis across all components (e.g. "PH (PKR)" not "PH(PKR)")

### Removed
- DemographicsCard from constituency page (replaced by ElectoralInfluenceCard)

---

## Sprint 5.3: MP Contact Card (2026-03-05)

### Added
- **MP model** (`parliament/models.py`): OneToOne to Constituency, stores name, photo, party, email, phone, fax, social media URLs, service centre address, parlimen profile ID, MyMP slug.
- **MP scrapers** (`parliament/services/mp_scraper.py`): Parsers for parlimen.gov.my listing + profile pages and mymp.org.my sitemap. Handles invalid SSL cert with `verify=False`.
- **`import_mp_profiles` command**: Scrapes both sources, matches to constituencies, creates/updates MP records. Supports `--dry-run` and `--constituency` flags.
- **MP data in API**: `GET /api/v1/constituencies/<code>/` now includes nested `mp` object with contact details and profile URLs.
- **ContactMPCard component**: Constituency sidebar card with circular photo, party badge, Email/Call/Facebook action buttons, service centre address, Parliament + MyMP profile links. Hidden when no MP data.
- **Trilingual i18n**: 5 new strings in EN/TA/MS for the contact card.
- **Shared PaginationBar**: Extracted from 6 components into reusable component (done prior to this sprint).
- **24 new tests** (16 backend + 8 frontend), 1037 total (766 backend + 271 frontend)
- **222 MPs imported** to production (100% with photo/email, 75% with phone, 65% with MyMP slug)

### Changed
- Constituency page sidebar: ContactMPCard sits above ScorecardCard
- `ConstituencyDetailSerializer` includes `mp` field

---

## Sprint 5.1: Pipeline Automation (2026-03-05)

### Added
- **Calendar scraper** (`hansard/pipeline/calendar_scraper.py`): Scrapes parlimen.gov.my for meeting date ranges and individual sitting dates. Creates/updates ParliamentaryMeeting records automatically.
- **Auto brief generator** (`generate_all_pending_briefs()`): Finds sittings with analysed mentions but no SittingBrief, generates briefs automatically.
- **Meeting report generator** (`parliament/services/report_generator.py`): Gemini-powered executive reports for completed meetings. Structure: Key Findings, MP Activity, Policy Signals, What to Watch.
- **Unified pipeline command** (`run_hansard_pipeline`): Single management command orchestrating 7 steps — calendar sync, PDF discovery, school matching, Gemini analysis, scorecards, sitting briefs, meeting reports. Supports `--dry-run`, `--skip-calendar`, `--skip-analysis`.
- **WAT workflow** (`_workflows/hansard-pipeline.md`): Living SOP for the Hansard pipeline with lessons learned.
- **30 new backend tests** (750 total backend)

### Changed
- Cloud Run job `sjktconnect-check-hansards` should now run `run_hansard_pipeline` instead of `check_new_hansards --auto-process` (deployment pending)

---

## UI Polish + Hansard Display Fix (2026-03-04)

### Added
- **Parliament Watch data display**: School pages now show Hansard mentions (were hidden behind APPROVED gate — all 193 mentions were PENDING). Constituency pages show recent mentions below scorecard numbers. `/parliament-watch` page shows sitting briefs.
- **Constituency mentions API**: `GET /api/v1/constituencies/<code>/mentions/` — lists Hansard mentions for a constituency's MP
- **BriefsList component**: Renders sitting briefs with title, mention count, summary, and date
- **News pagination**: Per-page dropdown (5/10/25), page numbers with ellipsis (desktop), compact prev/next (mobile)
- **School leadership empty state**: Added LPS Chairman and Alumni Chairman placeholders
- **Footer social icons**: Instagram and YouTube replace X/Twitter

### Changed
- **SchoolMentionsView**: Now excludes only REJECTED mentions (was: only shows APPROVED). PENDING mentions are now visible.
- **SittingBriefListView**: Now shows all briefs with content (was: only published). Removes manual publish gate.
- **ScorecardCard**: Accepts optional `mentions` prop to show recent mention summaries below scorecard numbers
- **MapFilterPanel**: Collapsible on mobile with chevron toggle, starts collapsed
- **SchoolProfile**: Removed duplicate enrolment numbers from School Details section (already shown in stat cards)

### Fixed
- **News school matching**: Improved `_resolve_school_codes` with abbreviation mapping (Estate↔Ldg, East↔Timur, etc.), noise word stripping, number format normalisation. Matching improved from 76% to 87%.
- **Missing Cloud Run env vars**: Previous deployment wiped env vars — restored SECRET_KEY, DATABASE_URL, GEMINI_API_KEY etc.
- **www.tamilschool.org**: Added domain mapping for www subdomain + CNAME record

---

## Hansard Pipeline: Full Parliament Backfill (2026-03-04)

### Data
- **97 sittings processed** across 5 parliament sessions (Feb 2025 – Mar 2026)
- **193 mentions** of Tamil schools found, all AI-analysed with Gemini 2.5 Flash
- **36 MP scorecards** created/updated
- **33 sitting briefs** generated for all sittings with mentions
- 34 non-sitting days correctly identified and marked as failed

### Fixed
- **Scraper: parlimen.gov.my blocks HEAD requests** — switched `_pdf_exists()` from HEAD to ranged GET (`Range: bytes=0-0`) to detect PDF availability
- **Gemini client: rate limit handling** — added retry with exponential backoff on 429 errors, switched to gemini-2.5-flash model
- **Analysis filter bug** — `analyse_mentions` command used `mp_name=''` to detect unanalysed mentions, but Gemini legitimately returns empty MP names when the speaker can't be identified from the quote. Changed to `ai_summary=''`
- **Brief generator filter** — same fix applied to `generate_brief()`, now uses `ai_summary` instead of `mp_name` to determine if a mention has been analysed

### Changed
- `analyse_mentions` command: added `connection.close()` after each write to prevent stale DB connections

---

## Sprint 4.1–4.2: Donations Feature (2026-03-04)

### Added
- **School bank details**: 3 new fields on School model (`bank_name`, `bank_account_number`, `bank_account_name`), imported from TF Excel for 202 schools
- **`import_bank_details` command**: Import school bank details from TF Excel database (`data/பள்ளிகள் - மாநிலம்.xlsx`)
- **DuitNow QR endpoint**: `GET /api/v1/schools/<moe_code>/duitnow-qr/` — generates PNG QR code with school's bank details
- **Support This School card**: Sidebar card on school pages showing bank name, account number (with copy button), account name, and DuitNow QR code. Only shown for schools with bank data (202/528). Editable via magic link claim.
- **Donations Django app**: New `donations` app with Donation model (UUID PK, order ID, Toyyib Pay fields), Toyyib Pay service (create_bill, verify_callback_hash, process_callback), 3 API endpoints (create donation, callback, status)
- **Donate page**: `/donate` page with preset amounts (RM 10/50/100/250), custom amount, donor info form, Toyyib Pay redirect. Thank-you page with payment status check.
- **DonationForm component**: Client component with amount selection, validation, loading states, error handling
- **Admin panel**: DonationAdmin with list/filter/search/readonly fields
- **i18n**: All donation strings in EN/TA/MS (20 keys in `donate` namespace, 7 keys in `schoolProfile` namespace)

### Dependencies
- Added `qrcode[pil]>=7.0` to backend requirements

### Tests
- 47 new tests: 33 backend (model, service, API, QR) + 14 frontend (SupportSchoolCard, DonationForm)
- Total: 979 tests (714 backend + 265 frontend)

### Configuration (pending deployment)
- Toyyib Pay env vars needed on Cloud Run: `TOYYIBPAY_SECRET_KEY`, `TOYYIBPAY_CATEGORY_CODE`, `TOYYIBPAY_BASE_URL`

---

## Post-Sprint 3.8 Fixes (2026-03-04)

### Added
- **Historical news backfill**: `backfill_news` management command — searches Google News RSS for Tamil school articles (English + Tamil queries), decodes Google News redirect URLs via `googlenewsdecoder`, creates NewsArticle records with deduplication
- **Tamil language news support**: 4 Tamil-script RSS queries (`தமிழ்ப்பள்ளி`, `தமிழ் பள்ளி மலேசியா`, `SJKT தமிழ்`, `தமிழ் பள்ளி ஆசிரியர்`) with correct locale params (`hl=ta`, `ceid=MY:ta`)
- **School name resolution**: AI-extracted school names now matched against database to populate `moe_code` — enables school chip links on news cards
- **School disambiguation**: When multiple schools share a name (e.g. "SJK(T) Saraswathy"), article location clues resolve the correct one
- **Abbreviation matching**: `Ladang↔Ldg`, `Sungai↔Sg`, `Kampung↔Kg`, `Jalan↔Jln` variants matched automatically
- **Multi-word matching**: School names like "Melaka Kubu" now match "Melaka (Kubu)" in database
- **`rematch_schools` command**: Re-resolve unmatched school mentions after matching improvements
- **Mega-menu header**: Data-driven dropdown navigation with grouped items (Explore, Intelligence, Resources, About), desktop dropdowns + mobile accordion, Subscribe/Donate CTAs, 7 stub pages for future routes
- **YMHA migration**: Fix abbreviation casing `Ymha` → `YMHA` for school ABD6101

### Fixed
- **Gemini model upgrade**: `gemini-2.0-flash` → `gemini-2.5-flash` for better analysis accuracy
- **NEWS_WATCH_RSS_FEEDS**: Added missing env var to production settings (was causing empty feed fetches)
- **Non-Tamil school filtering**: News tags now exclude non-Tamil schools; missing `moe_code` renders grey badge instead of broken link
- **Tamil query time filter**: `when:` parameter breaks Google News RSS for non-ASCII queries — now auto-skipped
- **Tamil school name handling**: `_strip_prefix()` handles Tamil suffixes (`தமிழ்ப்பள்ளி`) and prefixes (`தேசிய வகை`); Gemini prompt transliterates Tamil school names to English
- **Header language switcher**: Moved before Subscribe/Donate buttons for correct visual order
- **YMHA abbreviation**: Added to `_UPPER_ABBREVS` set in `schools/utils.py`
- **SJK prefix regex**: Now handles `SJK(T)`, `SJK (T)`, `SJK T` variants

### Data
- 88 English articles + 253 Tamil articles backfilled (March 2025 onwards)
- 297 extracted, all analysed; 183 auto-approved, 191 filtered as irrelevant (Indian school news)

### Dependencies
- Added `googlenewsdecoder>=0.1` to requirements.txt

---

## Homepage Hero Redesign (2026-03-03)

### Fixed
- **InfoWindow close button**: Removed `headerDisabled` prop so the X button works again on map popups

### Changed
- **HeroSection redesign**: Gradient background (blue-950 → indigo-900), glass-morphism stat cards with backdrop-blur, asymmetric layout (1 large Schools card + 2 smaller), search icon on "Find School" button
- **NationalStats redesign**: "National Key Metrics" heading, coloured left-border accent bars (red/blue/green/amber/rose), impact number formatting (e.g. "85,000" → "85,000", "3,200" → "3,000+"), left-aligned card layout
- **Hero description**: Community-driven copy instead of Tamil Foundation branding
- **i18n**: Updated hero description and stats labels in EN/MS/TA — added `stats.heading`, renamed `schoolsUnder30` → `underEnrolled`

---

## Sprint 3.8 — News & Reports Page (2026-03-03)

### Added
- **Public News API**: `GET /api/v1/news/` — paginated list of approved articles with `?search=` and `?category=school|general` filters
- **Auto-approve**: Articles with AI relevance score >= 3 are now automatically approved after analysis
- **News & Reports page**: `/news` with tab filters (All / By School / General), search, article cards, subscribe CTA sidebar, and most mentioned schools sidebar
- **NewsCard component**: Article card with title link, source/date, sentiment badge, AI summary, school chips (linked to school pages), and URGENT badge
- **NewsList component**: Client-side filtering, search, and sidebar with subscribe CTA and top mentioned schools
- **i18n**: 19 new translation keys in EN/MS/TA for the news page

### Changed
- **Navigation**: "Parliament Watch" renamed to "News & Reports" in header and footer (all 3 languages)
- **NewsArticle API**: `mentioned_schools` field now included in serializer response

### Technical
- 785 tests passing (547 backend + 238 frontend) — 28 new tests
- Backend and frontend deployed to Cloud Run
- 7 commits

---

## Sprint 3.7 — Map InfoWindow, School Page Polish & Enrolment Filter (2026-03-03)

### Fixed
- **Enrolment filter**: Schools above the enrolment threshold are now hidden entirely instead of shown as grey pins — reduces visual clutter on the map

### Changed
- **Map InfoWindow redesign**: New popup with school image (or placeholder), assistance/location badges, 3-stat row (students, teachers, ratio), constituency + DUN links, full-width "View School" button
- **School detail page redesign**: 12-col grid layout (7/5 split), 3 elevated stat cards with SVG icons (students, teachers, grade), preschool/special ed info bar, top-aligned title, metadata chip with primary-coloured MOE code
- **SchoolPhotoGallery**: Taller image (400px on desktop), clickable thumbnails overlaid inside the image at bottom-left, attribution overlay with backdrop blur
- **StatCard**: Elevated design with rounded-xl, border, shadow, React.ReactNode icon support with configurable colour
- **SchoolListSerializer**: Added `dun_id`, `dun_code`, `dun_name`, `image_url` fields for map InfoWindow
- **SchoolListView**: Added `select_related("dun")` and `prefetch_related("images")` to avoid N+1 queries

### Added
- `mapInfoWindow` translation namespace (EN/MS/TA) with keys for badges, stats, and CTA

### Technical
- 757 tests passing (532 backend + 225 frontend)
- Both backend and frontend deployed to Cloud Run
- 3 commits: enrolment filter fix, InfoWindow redesign, school page redesign

---

## Sprint 3.6 — Footer, Legal, Contact, School Page & Map Filters (2026-03-03)

### Added
- **Footer redesign**: Dark bg, copyright + social media icons (left), Platform + Legal link columns (right)
- **Legal pages**: Privacy Policy, Terms of Service, Cookie Policy — trilingual (EN/MS/TA)
- **Contact page**: Form (name, email, subject, message) with backend API, sends via Brevo
- **Contact API**: `POST /api/v1/contact/` with 3/hour rate limit, Brevo email integration
- **MapFilterPanel**: Replaces StateFilter — 4 colour modes (Assistance, Location, Programmes, Enrolment), toggle switches, enrolment slider, counter, info note
- **Coloured map pins**: Dynamic pin colours based on active filter mode (assistance: purple/orange, location: blue/green, programmes: purple/blue/orange/grey, enrolment: red/grey)
- **MapFilterPanel tests**: 10 new tests covering all colour modes, toggles, slider, reset
- Contact link in header nav (desktop + mobile)
- `dun_id` field in SchoolDetailSerializer for DUN page linking
- `assistance_type`, `location_type`, `preschool_enrolment`, `special_enrolment` fields in SchoolListSerializer for map filtering
- `mapFilters` translation namespace (all 3 languages)

### Changed
- **School detail page**: Redesigned layout — political representation + MiniMap moved to right sidebar, 5 stat cards (Students, Teachers, Grade, Preschool, Special Ed)
- **Leadership section**: Always shown — displays "Not Available" placeholders when no leaders data
- **Constituency/DUN**: Now clickable links (→ `/constituency/P149`, → `/dun/{id}`)
- **ConstituencySchools**: Shows "only Tamil school" message instead of returning null when empty
- **StatCard**: Added top-border accent (`border-t-2 border-t-primary-500`)
- **Section headers**: Added coloured left-border accents, person icons on leadership
- **SchoolMap**: Uses MapFilterPanel instead of StateFilter, filtering by assistance/location/programmes/enrolment
- **SchoolMarkers**: Accepts `colourMode` and `enrolmentThreshold` props for dynamic pin colouring
- **Search**: "SJKT" now matches "SJK(T)" in search results (parenthesis normalisation)

### Technical
- 757 tests passing (532 backend + 225 frontend)
- New components: MapFilterPanel, ContactForm
- New pages: contact, privacy, terms, cookies

---

## Sprint 3.5 — Tamil Translation Review + Deployment (2026-03-03)

### Fixed
- Tamil translations: 7 vallinam doubling corrections (ஊடகச், புலனாய்வுத், இயங்குப்/த், பள்ளிப், நடவடிக்கைகளைத், புலனாய்வுக்குச்)
- Tamil translations: standardised நுண்ணறிவு → புலனாய்வு for "intelligence" consistency
- Tamil translations: AI → செய்யறிவு (proper Tamil term for artificial intelligence)
- Tamil translations: சந்தா செலுத்துங்கள் → இணையுங்கள் (join, not pay subscription)
- Tamil translations: removed redundant இயங்கு from செய்யறிவு compounds
- Frontend: updated @swc/helpers to 0.5.19 for next-intl compatibility

### Deployed
- Backend: revision sjktconnect-api-00016-vlb (all Sprint 3.3-3.4 changes)
- Frontend: revision sjktconnect-web-00013-ff8 (i18n, hero, about, data provenance)
- Cloud Run jobs updated to latest image (check-hansards, news-pipeline, monthly-blast)

### Technical
- 747 tests passing (532 backend + 215 frontend)
- gcloud CLI fixed: CLOUDSDK_PYTHON updated to Python 3.13

---

## Sprint 3.4 — Homepage, About, Data Provenance & UX (2026-03-03)

### Added
- National summary statistics API endpoint (`GET /api/v1/schools/national-stats/`)
- Homepage hero section with mission statement and national stats bar (528 schools, 75k students, 222 constituencies)
- About page (`/about/`) with mission, methodology, and team information
- Favicon and site metadata (apple-touch-icon, Open Graph, manifest icons)
- Data provenance notes on SchoolProfile ("Data source: MOE, January 2026") and Footer ("Data last updated: January 2026")
- Social proof text on subscribe form
- `translations.ts` utility for translating MOE jargon (enrolment categories, grade levels)
- HeroSection and NationalStats components
- 6 new frontend tests (HeroSection, NationalStats, About page, translations)
- 1 new backend test (national stats endpoint)

### Changed
- School profile: enrolment categories translated from Malay (e.g. "ENROLMEN PRASEKOLAH" → "Preschool Enrolment")
- School profile: grade levels translated (e.g. "GRED A" → "Grade A")
- Claim This Page CTA reframed — emphasises community benefit over claiming
- Parliament Watch page: improved empty state with constructive messaging
- NewsWatchSection: improved empty state with explanation text
- MentionsSection: added context for empty mentions state
- ConstituencyList: filters out constituencies with zero schools
- Constituency page: hides boundary map when no GeoJSON available
- Footer: added About link alongside Subscribe and Contact
- Header: added About link to navigation

### Technical
- 747 tests passing (532 backend + 215 frontend)
- 33 files changed, +1,037 lines

---

## Sprint 3.3 — i18n Infrastructure (2026-03-03)

### Added
- Trilingual support (English, Tamil, Malay) using next-intl
- Locale-prefixed URLs: `/en/`, `/ta/`, `/ms/`
- Language switcher in Header (EN | தமிழ் | BM)
- ~162 strings extracted to `messages/en.json`, `messages/ta.json`, `messages/ms.json`
- Middleware for automatic locale detection and redirect
- Translation completeness tests (all three languages must have matching keys)
- LanguageSwitcher component
- 6 new i18n tests (190 frontend total, 852 overall)

### Changed
- All pages moved under `app/[locale]/` directory
- All internal links use i18n-aware navigation (`@/i18n/navigation`)
- Root `/` redirects to `/en/`
- Layout wraps children with NextIntlClientProvider

---

## Sprint 3.2 — Frontend Layout Redesign (2026-03-02)

### Changed
- School page hero: side-by-side layout on desktop (photo 3/5, name + stats 2/5), stacked on mobile
- Stat cards moved to hero: Students (primary + preschool combined), Teachers, Grade
- Removed SKM stat card, MOE Code detail row, and Full Name detail row
- Enrolment breakdown always shown: School, Preschool, Special Needs (even when 0)
- Assistance type mapped: SBK → Government-Aided (SBK), SK → Government (SK)
- Address format: postcode and city grouped together

### Added
- `SchoolLeader` TypeScript type
- `leaders` field on `SchoolDetail` interface
- School Leadership section in SchoolProfile (Board Chairman, Headmaster, PTA Chair, Alumni Chair)
- 5 new frontend tests (184 total), all 846 tests passing (662 backend + 184 frontend)

---

## Sprint 3.1 — Data Quality + School Leadership (2026-03-02)

### Added
- `to_proper_case()` utility: converts ALL CAPS MOE data to proper title case, preserving abbreviations (SJK(T), PPD, LDG, SG, etc.) and handling apostrophes, Roman numerals, parenthetical expressions
- `format_phone()` utility: standardises Malaysian phone numbers to `+60-X XXX XXXX` format
- Data migration: proper case for 528 schools (names, addresses, states, PPD), lowercase emails, formatted phones
- Import script updated: future MOE re-imports produce proper case automatically
- `SchoolLeader` model: Board Chairman, Headmaster, PTA Chairman, Alumni Association Chairman
- Admin inline for managing school leaders with full contact details
- Public API exposes leader name and role only (phone/email private)
- Unique constraint: one active leader per role per school
- 41 new backend tests (32 utils + 7 model + 3 API → 662 total)

### Design docs
- `docs/plans/2026-03-02-school-page-improvements-design.md`
- `docs/plans/2026-03-02-school-page-improvements-impl.md`

---

## Sprint 2.8 — News Watch Live + Cloud Scheduler Automation (2026-03-02)

### Added
- Public news API endpoint: `GET /api/v1/schools/<moe_code>/news/` — returns approved news articles mentioning a school
- `NewsArticleSerializer` and `SchoolNewsView` in `newswatch/api/`
- Real `NewsWatchSection` component on school pages — replaces placeholder with actual article display (title, source, date, AI summary, sentiment badge, urgency flag)
- `NewsArticle` TypeScript type and `fetchSchoolNews()` API function
- `run_news_pipeline` management command — chains fetch → extract → analyse for Cloud Scheduler
- Cloud Run Jobs: `sjktconnect-news-pipeline` (daily) and `sjktconnect-monthly-blast` (1st of month)
- Cloud Scheduler: `sjktconnect-daily-news` (8:30 AM MYT daily), `sjktconnect-monthly-blast` (9:00 AM 1st of month)
- Clickable photo thumbnails in `SchoolPhotoGallery` — click to swap into hero position (from pre-sprint work, included in deploy)
- 16 new backend tests (7 news API + existing), 9 new frontend tests (NewsWatchSection)

### Fixed
- Fixed gcloud CLI Python path issue (Python 3.11 removed, updated to Python 3.13 via CLOUDSDK_PYTHON)

### Infrastructure
- Backend deployed: revision `sjktconnect-api-00015-9bt`
- Frontend deployed: revision `sjktconnect-web-00012-jfx`
- Updated all Cloud Run Jobs to latest image
- Added `CLOUDSDK_PYTHON` to `~/.bashrc` for permanent gcloud fix

---

## Sprint 2.7 — Monthly Intelligence Blast (2026-03-02)

### Added
- `blast_aggregator.py` service: queries top 5 approved Hansard mentions, top 5 approved news articles, top 3 MP scorecards for a given month
- `compose_monthly_blast` management command with `--month YYYY-MM` and `--dry-run` flags
- `monthly_blast.html` email template with three sections (Parliament Watch, News Watch, MP Scorecard Highlights)
- 23 new backend tests (blast aggregator service + management command)

### Technical
- No new models — reuses existing Broadcast, HansardMention, NewsArticle, MPScorecard
- Audience filter set to MONTHLY_BLAST category for subscriber targeting
- Plain-text fallback auto-generated via strip_tags
- Admin reviews draft via existing broadcast preview UI, sends via existing Brevo infrastructure

## Sprint 2.6 — News AI Analysis + Rapid Response + Review UI (2026-03-02)

### Added
- Gemini Flash AI analysis of extracted news articles: relevance score (1-5), sentiment (POSITIVE/NEGATIVE/NEUTRAL/MIXED), AI summary, mentioned school extraction, urgency flagging
- `news_analyser.py` service: Gemini API wrapper with token budgeting (~3000 chars), structured JSON output, response validation with enum clamping
- `analyse_news_articles` management command: processes EXTRACTED articles in batches (`--batch-size`), warns about urgent articles pending review
- Admin review queue at `/dashboard/news/`: filterable by review status (PENDING/APPROVED/REJECTED) and urgency, sorted urgent-first then by relevance
- Article detail view at `/dashboard/news/<pk>/`: split-screen layout (article body left, AI analysis + actions right), approve/reject/toggle-urgent actions
- Navigation sidebar showing other articles for quick review switching
- "News Watch" nav link in base template
- Migration `0002_add_ai_analysis_fields`: adds 9 fields to NewsArticle (relevance_score, sentiment, ai_summary, mentioned_schools, is_urgent, urgent_reason, ai_raw_response, review_status, reviewed_by, reviewed_at)

### Changed
- NewsArticle model: extended status lifecycle NEW → EXTRACTED → ANALYSED, added PENDING/APPROVED/REJECTED review status
- NewsArticle admin: added AI analysis fields to list display and filters

### Technical
- Follows same Gemini pattern as `parliament/services/gemini_client.py` — structured JSON response, validation with enum clamping, token budgeting
- Review actions use `update_fields` for efficient partial saves
- Queue view uses `LoginRequiredMixin` — admin-only access
- Urgency criteria: school closures, safety crises, funding cuts, political controversies
- 39 new backend tests (news analyser service, management command, admin views, model fields), 758 total (591 backend + 167 frontend)

---

## Sprint 2.5 — News Watch Pipeline: RSS + Article Extraction (2026-03-02)

### Added
- New `newswatch` Django app with `NewsArticle` model (status lifecycle: NEW → EXTRACTED or FAILED)
- RSS fetcher service: parses Google Alerts RSS feeds, unwraps redirect URLs, deduplicates by URL, batch-checks existing articles
- Article extractor service: uses trafilatura to fetch and extract body text, source name, and published date from article URLs
- Management commands: `fetch_news_alerts` (RSS polling, supports `--url` flag or `NEWS_WATCH_RSS_FEEDS` setting) and `extract_articles` (body extraction, `--batch-size` flag)
- Django admin for NewsArticle with list display, status/source filters, search
- New dependencies: feedparser, trafilatura, lxml_html_clean

### Technical
- Google Alerts redirect URL resolution (`google.com/url?...&url=ACTUAL_URL`)
- HTML tag stripping for RSS titles (Google Alerts uses `<b>` tags)
- Batch URL existence check to avoid N+1 queries during RSS import
- Article extraction preserves RSS-sourced published_date, only fills from trafilatura if missing
- Graceful failure handling: download failures and extraction errors set status=FAILED with error message
- 36 new backend tests (model, RSS fetcher, article extractor, management commands), 719 total (552 backend + 167 frontend)

---

## Sprint 2.4 — Subscribe/Unsubscribe Frontend Pages (2026-03-01)

### Added
- `/subscribe/` page with SubscribeForm component: email, name, organisation fields, category preview, success/error/loading states
- `/unsubscribe/[token]/` page with UnsubscribeConfirmation component: auto-calls API on mount, re-subscribe link
- `/preferences/[token]/` page with PreferencesForm component: loads current toggles, save with feedback, unsubscribe link
- Footer updated with "Subscribe to Intelligence Blast" link
- API client functions: `subscribe()`, `unsubscribe()`, `fetchPreferences()`, `updatePreferences()`
- TypeScript interfaces: `SubscribeRequest`, `SubscriberResponse`, `UnsubscribeResponse`, `PreferenceUpdate`

### Technical
- 33 new frontend tests (3 component test files + 1 API test file), 683 total (516 backend + 167 frontend)
- Follows existing patterns: Breadcrumb, metadata, `"use client"` for interactive components, server components for pages
- Dynamic routes use `params: Promise<{ token: string }>` pattern (Next.js 14 App Router)

---

## Sprint 2.3 — Broadcast Sending + Confirmation Email (2026-03-01)

### Added
- Broadcast sender service: sends individual emails via Brevo transactional API with per-recipient tracking
- Each broadcast email includes personalised unsubscribe and preferences links in footer
- Status transitions: DRAFT → SENDING → SENT (or FAILED on error)
- BroadcastRecipient tracks SENT/FAILED per-email with brevo_message_id
- Rate limited: 0.5s between emails to stay within Brevo free tier
- Dev mode: logs to console when no BREVO_API_KEY (no real emails sent)
- Confirmation email service: welcome email on new subscriber with preferences/unsubscribe links
- Management command `send_broadcast --id <pk>` for Cloud Run Job execution
- Broadcast detail view at `/broadcast/<pk>/` with per-recipient delivery status table
- Send button on preview page (POST with JavaScript confirmation dialog)

### Technical
- Atomic conditional UPDATE prevents race condition on concurrent send requests
- Try/finally ensures broadcast never stuck in SENDING state (transitions to FAILED on error)
- Recipient loop uses `select_related("subscriber")` to avoid N+1 queries
- Confirmation email sent outside `transaction.atomic()` to avoid holding DB connection during API call
- HTML template uses `.format()` (not `%s`) to handle content with literal `%` characters
- 32 new tests (sender service + send views + management command + confirmation email), 516 total passing

---

## Sprint 2.2 — Broadcast Models + Admin Compose UI (2026-03-01)

### Added
- New `broadcasts` app with `Broadcast` and `BroadcastRecipient` models
- Broadcast compose form at `/broadcast/compose/` with subject, HTML content, plain text, and audience filters
- Broadcast preview at `/broadcast/preview/<id>/` with sandboxed HTML preview, recipient count, filter summary
- Broadcast list at `/broadcast/` with status, dates, and pagination (50/page)
- Audience filtering service: filter subscribers by category, state, constituency, PPD, enrolment range, SKM eligibility
- `created_by` field on Broadcast for audit trail
- Django admin registration with inline recipient tracking
- Nav link to Broadcasts in base template

### Technical
- Server-side validation for empty subjects and non-numeric enrolment values
- HTML preview sandboxed in `<iframe sandbox="">` to prevent XSS
- States and PPDs dynamically queried from School model (not hardcoded)
- `UniqueConstraint` on (broadcast, subscriber) pair
- 47 new tests (13 model + 15 audience service + 19 views), 484 total passing

---

## Sprint 1.10 — School Page Redesign + Image Fix (2026-03-01)

### Added
- School mentions API endpoint: `GET /api/v1/schools/<moe_code>/mentions/` — returns approved parliamentary mentions
- Multi-photo image harvester: Google Places now fetches up to 3 photos per school (was 1)
- `SchoolImageSerializer` + `images` array in school detail API response
- `SchoolImageData` TypeScript type on frontend
- `SchoolPhotoGallery` component: hero image + thumbnails, fallback chain (Places → satellite → placeholder)
- `SchoolHistory` component: "Help us tell this school's story" CTA with contact link
- `NewsWatchSection` component: placeholder for upcoming news monitoring
- New school page layout: photo gallery → name/Tamil name → stats → details → map → Parliament Watch → News Watch → History → sidebar → Claim button

### Fixed
- Google Maps API key rotation: replaced deleted key in all 528 stored image URLs
- Updated `GOOGLE_MAPS_API_KEY` env var on backend Cloud Run service
- Redeployed frontend + backend with new API key

### Technical
- `MentionsSection` renders approved `HansardMention` records via bridge table
- Image harvester does clean re-harvest (deletes old PLACES images before creating new)
- First Places photo promoted to primary; satellite demoted to secondary
- 437 backend tests passing

---

## Sprint 2.1 — Subscriber Models + Subscribe/Unsubscribe API (2026-03-01)

### Added
- New `subscribers` Django app with `Subscriber` and `SubscriptionPreference` models
- `Subscriber`: email (unique), name, organisation, is_active, unsubscribe_token (UUID), subscribed/unsubscribed timestamps
- `SubscriptionPreference`: per-subscriber toggle for PARLIAMENT_WATCH, NEWS_WATCH, MONTHLY_BLAST categories
- Service layer (`subscriber_service.py`): subscribe (with reactivation), unsubscribe, get/update preferences
- REST API endpoints:
  - `POST /api/v1/subscribers/subscribe/` — create subscriber with all preferences enabled (idempotent)
  - `GET /api/v1/subscribers/unsubscribe/<token>/` — one-click unsubscribe via token
  - `GET/PUT /api/v1/subscribers/preferences/<token>/` — view/update category preferences
- Admin registration with inline preferences
- 51 new tests (16 model + 17 service + 18 API)

### Technical
- Email normalised to lowercase on subscribe
- Duplicate subscribe returns 200 (not 400) — idempotent
- Reactivation: previously unsubscribed users are reactivated on re-subscribe
- Preferences auto-created for all categories on subscribe or first access
- All endpoints are public (no authentication required) — tokens provide access control

### Test count: 426 (375 existing + 51 new)

---

## Sprint 1.9 — Full Stack Deployment + Phase 1 Close (2026-02-28)

### Infrastructure
- New GCP project `sjktconnect` created under `tamilfoundation.org` organisation (previously on personal account)
- Backend deployed as `sjktconnect-api` on Cloud Run (asia-southeast1)
- Frontend deployed as `sjktconnect-web` on Cloud Run (asia-southeast1) — first frontend deployment
- Google Maps API key created and restricted to Maps JS, Static Maps, Places APIs
- CORS configured: frontend origin whitelisted on backend
- Cloud Run job `sjktconnect-check-hansards` recreated in new project
- Cloud Scheduler `sjktconnect-daily-check` recreated (daily 8am MYT)

### Changed
- Frontend Dockerfile: switched from ARG to ENV for `NEXT_PUBLIC_*` build vars (Cloud Build doesn't pass build args)
- Backend ALLOWED_HOSTS and CSRF_TRUSTED_ORIGINS updated for new URLs

### Data
- 528 satellite images harvested into production database (all schools with GPS coordinates)

### Post-Sprint Follow-ups (2026-03-01)
- Custom domain `tamilschool.org` mapped to Cloud Run (auto-verified via domain provider)
- BREVO_API_KEY set on backend; Brevo sender domain `tamilschool.org` authenticated (DKIM + DMARC)
- GEMINI_API_KEY set on backend for AI analysis commands
- Upgraded map markers from deprecated `Marker` to `AdvancedMarker` with indigo `Pin` styling
- Added Google Maps Map ID (`ce9504578e73fb7dd21b6704`) to Dockerfile
- Fixed outreach email encoding: replaced literal em dashes with `&mdash;` entities
- Deleted old `sjktconnect-api` from personal GCP project (`gen-lang-client-0871147736`)
- Removed stale `tamilschool.org.my` domain mapping

---

## Sprint 1.8 — Outreach App + School Images + Email Outreach (2026-02-28)

### Added
- `outreach` Django app (6th app) with `SchoolImage` and `OutreachEmail` models + migration
- `SchoolImage` model: image URL, source (SATELLITE/STREET_VIEW/PLACES/MANUAL), primary flag, attribution, photo reference
- `OutreachEmail` model: recipient, subject, status (PENDING/SENT/FAILED/BOUNCED), Brevo message ID tracking
- `harvest_school_images` management command — Google Static Maps (satellite) + Places API (real photos), `--limit`, `--state`, `--source`, `--dry-run` flags
- `send_outreach_emails` management command — Brevo introduction emails with school page + claim links, `--limit`, `--state`, `--dry-run` flags, skips already-emailed schools
- Image harvester service: `harvest_satellite_image` (GPS → static map URL), `harvest_places_image` (Places API search + photo reference), `harvest_images_for_school` (both sources)
- Email sender service: `send_outreach_email` with Brevo API integration and console fallback in dev
- Admin registration for SchoolImage and OutreachEmail with list display, filters, search
- `SchoolImage` frontend component — responsive image with lazy loading, rounded border
- `GOOGLE_MAPS_API_KEY` backend env var (falls back to `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY`)
- 34 new backend tests: satellite harvest (5), places harvest (6), combined harvest (2), harvest command (5), email sending (4), email model (2), image model (2), email command (6), API image_url (2)
- 3 new frontend tests: SchoolImage component (src/alt, lazy loading, responsive classes)

### Changed
- `SchoolDetailSerializer` now includes `image_url` field (primary image URL from SchoolImage or null)
- School profile page displays hero image above header when `image_url` is available
- `SchoolDetail` TypeScript type extended with `image_url: string | null`
- `INSTALLED_APPS` in base settings: added `outreach`

### Test totals
- Frontend: 134 passing (+3)
- Backend: 375 passing (+34)
- **Total: 509**

---

## Sprint 1.7 — School Data Confirm/Edit + Admin Dashboard (2026-02-28)

### Added
- `IsMagicLinkAuthenticated` DRF permission class in `accounts/permissions.py` — validates session-based Magic Link auth, sets `request.school_contact` and `request.school_moe_code`
- `SchoolEditSerializer` — writable fields for school data (address, phone, enrolment, GPS, etc.), read-only for identity fields
- `GET/PUT /api/v1/schools/{code}/edit/` — authenticated reps can view and update their school's editable fields; creates AuditLog with changed_fields
- `POST /api/v1/schools/{code}/confirm/` — 2-click confirmation: updates `last_verified` timestamp without editing
- Next.js edit page at `/school/[moe_code]/edit/` — pre-filled form with confirm button (green, prominent) + edit form with save/cancel
- `SchoolEditForm` component: 16 fields (3 read-only), confirm and save actions, success/error states, last verified display
- `EditSchoolLink` component: client-side auth check, shows "Edit School Data" link only for authenticated school reps
- Admin verification dashboard at `/dashboard/verification/` (Django templates, login required):
  - Progress bar showing verified/total schools
  - Unverified schools by state table (ordered by count)
  - Recently verified schools table (last 20)
  - Registered school contacts table (last 20)
- `schools/views.py` — `VerificationDashboardView` (LoginRequiredMixin + ListView)
- `schools/urls.py` — dashboard URL routing
- "Verification" nav link in base template for authenticated admin users
- CSS styles: `.card`, `.progress-bar-container`, `.progress-bar`, `.progress-text`, `.data-table`, `.muted`
- Frontend types: `SchoolEditData`, `SchoolConfirmResponse`
- Frontend API functions: `fetchSchoolEdit`, `updateSchool`, `confirmSchool` (all with `credentials: "include"`)
- 32 new backend tests: permission class (4), school edit API (8), school confirm API (6), admin dashboard (14)
- 19 new frontend tests: SchoolEditForm (10), EditSchoolLink (3), API edit functions (6)

### Changed
- School profile page: added `EditSchoolLink` alongside ClaimButton
- `schools/api/urls.py`: added edit/confirm routes before detail route (avoids capture conflicts)
- `sjktconnect/urls.py`: added `schools.urls` include for dashboard

### Test totals
- Frontend: 131 passing (+19)
- Backend: 341 passing (+32)
- **Total: 472**

---

## Sprint 1.6 — Magic Link Authentication (2026-02-27)

### Added
- `accounts` Django app with `MagicLinkToken` and `SchoolContact` models
- Magic link API: `POST /api/v1/auth/request-magic-link/`, `GET /api/v1/auth/verify/{token}/`, `GET /api/v1/auth/me/`
- Token service: 24-hour expiry, UUID tokens, single-use validation
- Email service: Brevo transactional email in production, console logging in development
- @moe.edu.my email validation — matches school by MOE code or stored email
- Session-based authentication after token verification
- Next.js claim flow: `/claim/` (email form), `/claim/verify/[token]/` (verification)
- ClaimForm component: email input with pre-fill from school code, loading/success/error states
- ClaimButton now links to `/claim/?school=MOE_CODE` (was disabled placeholder)
- Types: `MagicLinkResponse`, `AuthUser`, `ApiError`
- API functions: `requestMagicLink`, `verifyMagicLink`, `fetchMe`
- Admin: SchoolContact and MagicLinkToken registered with list display/filters/search
- 33 new backend tests: models (7), token service (5), email validation (5), school matching (4), API endpoints (12)
- 14 new frontend tests: ClaimForm (6), auth API (8)

### Changed
- ClaimButton: active link instead of disabled button

### Test totals
- Frontend: 112 passing (+14)
- Backend: 309 passing (+33)
- **Total: 421**

---

## Sprint 1.5 — Constituency + DUN Pages (2026-02-27)

### Added
- Constituency page `/constituency/[code]` with ISR — MP info, scorecard, boundary map, demographics, school table, DUN list
- DUN page `/dun/[id]` with ISR — ADUN info, demographics, boundary map, school table, parent constituency link
- Constituencies index `/constituencies/` — browsable table with state filter, school counts, MP/party info
- BoundaryMap component: Google Maps with GeoJSON overlay for constituency/DUN boundaries
- ScorecardCard component: Parliament Watch scorecard stats (mentions, questions, commitments)
- DemographicsCard component: Indian population, income, poverty rate, Gini, unemployment
- SchoolTable component: sortable school list with links, enrolment, teacher count, PPD
- ConstituencyList component: filterable table with state dropdown
- "Constituencies" nav link added to Header (desktop + mobile)
- API functions: `fetchConstituencies`, `fetchConstituencyDetail`, `fetchConstituencyGeoJSON`, `fetchDUNs`, `fetchDUNDetail`, `fetchDUNGeoJSON`
- Types: `ConstituencyDetail`, `Scorecard`, `DUN`, `DUNDetail`, `GeoJSONFeature`, `GeoJSONFeatureCollection`
- Loading skeletons for constituency and DUN pages
- SEO metadata for all new pages
- 36 new frontend tests: API (9), ScorecardCard (7), DemographicsCard (7), SchoolTable (7), ConstituencyList (6)

### Test totals
- Frontend: 98 passing (+36)
- Backend: 276 passing (unchanged)
- **Total: 374**

---

## Sprint 1.4 — School Profile Pages (2026-02-27)

### Added
- Dynamic school profile route `app/school/[moe_code]/page.tsx` with ISR (revalidates hourly)
- SchoolProfile component: stat cards (enrolment, teachers, grade, SKM), full detail grid, political representation section
- StatCard component: reusable stat display with number formatting
- Breadcrumb navigation: Home > State > School
- ClaimButton component: "Claim This Page" CTA (disabled, coming in Sprint 1.6)
- MiniMap component: embedded Google Map with single school pin
- MentionsSection component: Parliament Watch mentions with MP name, party, significance, date
- ConstituencySchools sidebar: links to other schools in the same constituency
- Loading skeleton (`loading.tsx`) for school pages
- Not-found page for invalid school codes
- API functions: `fetchSchoolDetail`, `fetchSchoolsByConstituency`, `fetchSchoolMentions`
- `SchoolMention` TypeScript type
- SEO metadata: dynamic title, description, Open Graph tags per school
- 36 new frontend tests: API (5), StatCard (3), Breadcrumb (5), ClaimButton (4), MentionsSection (7), ConstituencySchools (4), SchoolProfile (8)

### Test totals
- Frontend: 62 passing (+36)
- Backend: 276 passing (unchanged)
- **Total: 338**

---

## Sprint 1.3 — Next.js Frontend + School Map (2026-02-27)

### Added
- Next.js 14 project in `frontend/` (App Router, Tailwind CSS, TypeScript)
- Layout: responsive Header with mobile menu, Footer with copyright
- Google Maps integration via `@vis.gl/react-google-maps` + `@googlemaps/markerclusterer`
- Full-width map page at `/` showing 528 school pins with automatic clustering
- Info window on marker click: school name, code, state, enrolment, teachers, constituency
- State filter dropdown — narrows map pins by state, shows count
- Search box with 300ms debounced typeahead — searches schools and constituencies via API
- API client (`lib/api.ts`) with automatic pagination through all school pages
- TypeScript types for School, Constituency, PaginatedResponse, SearchResults
- Dockerfile for Cloud Run deployment (standalone output, port 8080)
- `.env.local.example` for Google Maps API key and API URL configuration
- 26 frontend tests: API client (8), Header (4), Footer (3), StateFilter (5), SearchBox (6)

### Changed
- `.gitignore` updated with Node.js / Next.js entries (node_modules, .next, out)

### Test totals
- Frontend: 26 passing (new)
- Backend: 276 passing (unchanged)
- **Total: 302**

---

## Sprint 1.2 — Django REST API for Schools + Constituencies (2026-02-26)

### Added
- REST API endpoints (12 new):
  - `GET /api/v1/schools/` — list with filters: state, ppd, constituency, skm, min/max enrolment
  - `GET /api/v1/schools/<moe_code>/` — full school profile
  - `GET /api/v1/constituencies/` — list with school_count annotation, state filter
  - `GET /api/v1/constituencies/<code>/` — detail with nested schools + scorecard
  - `GET /api/v1/duns/` — list with state/constituency filters
  - `GET /api/v1/duns/<pk>/` — detail with nested schools
  - `GET /api/v1/scorecards/` — list with constituency/party filters
  - `GET /api/v1/scorecards/<pk>/` — MP scorecard detail
  - `GET /api/v1/briefs/` — published sitting briefs only
  - `GET /api/v1/briefs/<pk>/` — single published brief
  - `GET /api/v1/search/?q=<query>` — cross-entity search (schools, constituencies, MPs)
- `schools/api/serializers.py` — 6 serializers (School list/detail, Constituency list/detail, DUN list/detail)
- `parliament/api/` package — serializers, views, URLs for MPScorecard + SittingBrief
- CORS support via `django-cors-headers` with configurable `CORS_ALLOWED_ORIGINS` env var
- DRF pagination (50 items/page via PageNumberPagination)
- 37 new tests: test_school_api (26), test_parliament_api (11)

### Changed
- `schools/api/urls.py` expanded from 4 GeoJSON routes to 15 total routes
- `schools/api/views.py` expanded with School, Constituency, DUN, Search views
- `corsheaders` added to INSTALLED_APPS and MIDDLEWARE
- REST_FRAMEWORK config added to base settings

### Test totals
- 276 tests passing (239 from Sprint 1.1 + 37 new)

---

## Sprint 1.1 — WKT Boundary Import + GeoJSON API (2026-02-26)

### Added
- `boundary_wkt` TextField on Constituency and DUN models — stores OGC WKT polygon boundaries
- GeoJSON API endpoints (4 new):
  - `GET /api/v1/constituencies/geojson/` — all constituency boundaries as FeatureCollection
  - `GET /api/v1/constituencies/<code>/geojson/` — single constituency boundary
  - `GET /api/v1/duns/geojson/` — all DUN boundaries (filters: `?state=`, `?constituency=`)
  - `GET /api/v1/duns/<pk>/geojson/` — single DUN boundary
- `schools/api/` package: `geojson.py` (WKT-to-GeoJSON via shapely), `views.py` (4 DRF views), `urls.py`
- `shapely>=2.0` and `djangorestframework>=3.15` dependencies
- 19 new tests: test_geojson_api (13), test_geojson_helpers (6)

### Changed
- `import_constituencies` now parses WKT column from CSV and stores on DUN records
- `import_constituencies` computes constituency boundaries by unioning DUN polygons via `shapely.ops.unary_union`
- `rest_framework` added to INSTALLED_APPS
- Test CSV encoding fixed from `utf-8-sig` to `cp1252` (matches real CSV)
- Implementation plan and roadmap updated: Neon references replaced with Supabase, PostGIS risk resolved

### Test totals
- 239 tests passing (220 from Sprint 0.6 + 19 new)

---

## Sprint 0.6 — Deployment + Cloud Scheduler + Documentation (2026-02-26)

### Added
- `hansard/pipeline/scraper.py` — Discovers new Hansard PDFs via HEAD requests to parlimen.gov.my, probing date ranges for `DR-DDMMYYYY.pdf` URLs
- `check_new_hansards` management command — compares discovered PDFs against processed sittings in DB; supports `--days`, `--start`/`--end`, `--auto-process` (chains into `process_hansard`)
- Health check endpoint at `/health/` — returns `{"status": "ok"}` for Cloud Run liveness probes
- Cloud Run service `sjktconnect-api` deployed to asia-southeast1
- Cloud Run job `sjktconnect-check-hansards` — runs `check_new_hansards --auto-process --days 7`
- Cloud Scheduler `sjktconnect-daily-check` — triggers job daily at 8:00 AM MYT
- 22 new tests: test_scraper (11), test_check_new_hansards (10), test_health_check (1)

### Changed
- Database switched from planned Neon PostgreSQL to Supabase PostgreSQL (Tamil Foundation org, Singapore region, free tier)
- Production settings and docs updated from "Neon" to "Supabase"

### Infrastructure
- **Service URL**: https://sjktconnect-api-90344691621.asia-southeast1.run.app
- **Database**: Supabase PostgreSQL (transaction pooler, port 6543)
- **Reference data imported**: 222 constituencies, 613 DUNs, 528 schools, 2,106 aliases
- **Admin user**: admin@tamilfoundation.org

### Test totals
- 220 tests passing (198 from Sprint 0.5 + 22 new)

---

## Sprint 0.5 — Admin Review Queue + Content Publishing (2026-02-25)

### Added
- `MentionReviewForm` — ModelForm for editing AI analysis fields (mp_name, constituency, party, mention_type, significance, sentiment, change_indicator, ai_summary, review_notes)
- 8 Django views in `parliament/views.py`:
  - Admin (login required): ReviewQueueView, SittingReviewView, MentionDetailView, ApproveMentionView, RejectMentionView, PublishBriefView
  - Public: ParliamentWatchView, BriefDetailView
- 8 URL patterns in `parliament/urls.py` with `app_name = "parliament"`
- Root URL wiring: Django built-in LoginView/LogoutView at `/accounts/login/` and `/accounts/logout/`
- `highlight_keywords` template filter — wraps SJK(T) variants (6 regex patterns) in `<mark>` tags
- 7 templates: base.html (navbar + footer), queue, sitting_review, detail (split-screen), watch, brief, login
- `static/css/style.css` — full stylesheet with CSS variables, responsive split-screen grid, mention cards with status-coloured borders, keyword highlight styling
- 49 new tests: test_views (33), test_highlight (12), test_forms (4)

### Fixed
- Approve/reject redirect bug — was pointing to `mention-detail` with sitting ID (wrong lookup), fixed to redirect to `sitting-review`
- Empty significance field crash — IntegerField received `''` from blank ChoiceField. Fixed with `TypedChoiceField(coerce=int, empty_value=None)`

### Design decisions
- Split-screen review: left panel shows verbatim quote with keyword highlights + context; right panel shows editable AI analysis form
- Approve saves form edits + sets status in one POST; reject only saves review_notes + status
- PublishBriefView delegates to `generate_brief()` then sets `is_published=True`
- Public views have no auth requirement; admin views use `LoginRequiredMixin`
- ChoiceFields include blank option `("", "---")` so reviewers can clear AI-set values

### Test totals
- 198 tests passing (149 from Sprint 0.4 + 49 new)

---

## Sprint 0.4 — Gemini AI Analysis + MP Scorecard (2026-02-25)

### Added
- `parliament` app with `MPScorecard` and `SittingBrief` models
- Service modules in `parliament/services/`:
  - `gemini_client.py` — Gemini Flash API wrapper using `google.genai` SDK, structured JSON output, token budgeting (~1500 chars per call), response validation with enum clamping
  - `scorecard.py` — aggregates all analysed mentions per MP: total, substantive (significance >= 3), questions, commitments. Caches school count and enrolment from constituency. Idempotent recalculation with stale scorecard cleanup.
  - `brief_generator.py` — generates markdown sitting brief, renders to HTML, creates social post (<= 280 chars). Falls back to all analysed mentions if none approved yet.
- `analyse_mentions` management command — processes unanalysed mentions via Gemini, with `--dry-run`, `--limit`, `--sitting-date` options
- `update_scorecards` management command — full recalculation of all MP scorecards
- Admin registration for MPScorecard and SittingBrief
- 38 new tests: gemini_client (12), scorecard (13), brief_generator (13) — all Gemini calls mocked
- `google-genai` and `markdown` added to requirements.txt

### Design decisions
- Used `google.genai` SDK (not deprecated `google.generativeai`) — client pattern instead of global configuration
- Response validation: enum fields clamped to valid values, significance clamped 1-5, missing fields get sensible defaults
- Cross-platform date formatting helper (Windows lacks `%-d` strftime flag)
- Scorecard `update_or_create` pattern: full recalculation each run, stale records deleted
- Brief generator prefers APPROVED mentions but falls back to all analysed for early-stage use (before Sprint 0.5 review queue)

### Test totals
- 149 tests passing (111 from Sprint 0.3 + 38 new)

---

## Sprint 0.3 — School Name Matching (2026-02-25)

### Improved (code simplification pass)
- Hoisted `_BOUNDARY_WORDS` set and prefix regex to module-level constants in `matcher.py` (were recreated per call)
- Cached `_get_tracked_models()` in `signals.py` — was resolving on every Django signal
- Changed tracked models from `list` to `set` for O(1) membership checks
- Consolidated duplicate regex patterns for `s.j.k.(t)` / `s.j.k(t)` in `normalizer.py`
- Removed unused imports (`STOP_WORDS`, `re`) and unused variables (`all_alias_keys`, `quote`)
- Fixed f-string logging to use `%s` lazy formatting in `signals.py`

### Added
- `SchoolAlias` model — stores multiple name variants per school (official, short, common, SJKT, Hansard-discovered)
- `MentionedSchool` bridge model — links HansardMention to School with confidence score and match method
- `seed_aliases` management command — auto-generates ~4 aliases per school from official/short names
- Pipeline modules in `hansard/pipeline/`:
  - `matcher.py` — two-pass matching: exact alias lookup (100% confidence) then trigram similarity with difflib fallback
  - `stop_words.py` — 20 high-frequency words excluded from fuzzy matching (school prefixes + location words)
- pg_trgm extension migration (conditional — skips on SQLite, applies on PostgreSQL)
- Matcher integrated into `process_hansard` pipeline (Step 7, with `--skip-matching` flag)
- Admin registration for SchoolAlias and MentionedSchool
- 41 new tests: matcher (19), seed_aliases (11), stop_words (7), models (4)

### Design decisions
- Candidate extractor uses Malay boundary words (dan, di, yang, untuk, etc.) to stop capturing after the school name
- Progressive shortening: candidates trimmed word-by-word from right for exact match boundary detection
- Confidence < 80% auto-flagged as needs_review for human verification
- HANSARD alias type preserved during `--clear` re-seeding

### Test totals
- 111 tests passing (70 from Sprint 0.2 + 41 new)

---

## Sprint 0.2 — Hansard Download + Text Extraction + Keyword Search (2026-02-25)

### Added
- `hansard` app with HansardSitting and HansardMention models
- Pipeline modules in `hansard/pipeline/`:
  - `downloader.py` — HTTP download with retries, Content-Disposition support, parlimen.gov.my SSL workaround
  - `extractor.py` — pdfplumber text extraction (page by page)
  - `normalizer.py` — text normalisation: Unicode NFKC, lowercase, whitespace collapse, SJK(T) variant canonicalisation
  - `searcher.py` — keyword search with ±500 chars context extraction and verbatim quote mapping
  - `keywords.py` — primary (12) and secondary (7) keyword lists, DB school name loader
- `process_hansard <url>` management command with `--sitting-date`, `--catalogue-variants`, `--dest-dir` options
- Date extraction from Hansard filename pattern (DR-DDMMYYYY.pdf)
- Admin registration for HansardSitting and HansardMention
- 44 new tests: normaliser (13), searcher (12), downloader (10), pipeline integration (6), models (3)
- pdfplumber and requests added to requirements.txt

### Tested against real data
- 3 real Hansard PDFs processed (26 Jan, 28 Jan, 23 Feb 2026)
- 5 mentions found across 2 sittings (1 sitting had zero mentions — expected)
- Variant catalogue: "sjk(t)" (3 occurrences), "sekolah jenis kebangsaan tamil" (2 occurrences)
- Normaliser correctly handles: SJK(T), SJKT, S.J.K.(T), S.J.K(T), non-breaking spaces

### Test totals
- 70 tests passing (26 from Sprint 0.1 + 44 new)

---

## Sprint 0.1 — Project Scaffold + Reference Data Import (2026-02-25)

### Added
- Django project scaffold with split settings (base/development/production)
- `core` app: AuditLog model with post_save/post_delete signals and request middleware
- `schools` app: Constituency, DUN, School models
- `import_constituencies` management command — imports 222 constituencies and 613 DUNs from Political Constituencies CSV
- `import_schools` management command — imports 528 SJK(T) schools from MOE Excel, with GPS verification CSV override
- 26 tests across 3 test files (models, import_constituencies, import_schools)
- Project infrastructure: requirements.txt, Dockerfile, pytest.ini, .env.example, .gitignore, .dockerignore

### Fixed
- DUN model: changed from `code` as primary key to auto-generated PK with `unique_together = (code, constituency)` — DUN codes like "N01" repeat across all 13 states
- CSV encoding: Political Constituencies CSV uses cp1252, not UTF-8
- MOE Excel format: PARLIMEN/DUN columns contain names only (no codes), added name-based lookup fallback

### Data verification
- 222 constituencies, 613 DUNs, 528 schools imported
- 528/528 schools linked to constituency (100%)
- 513/528 schools linked to DUN (97% — 15 KL schools have no DUN, correct)
- 476/528 GPS coordinates verified from verification CSV
