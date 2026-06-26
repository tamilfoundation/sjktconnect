# v2.0.1 — Reliability + Security + SEO Foundation (v2.0 series complete)

**Tagged**: 2026-06-26
**Supersedes**: v2.0 (tagged earlier 2026-06-26 at end of Sprint 24, covered Sprint 23+24 only).
**Spans (cumulative since v1.x)**: Sprint 23 (2026-05-11) → Sprint 29 + small-change-lane (2026-06-26)
**Spans (delta vs v2.0)**: Sprint 25 → Sprint 29 + 2026-06-26 small-change-lane
**Live revisions at tag**: `sjktconnect-api-00135-kxm`, `sjktconnect-web-00127-vhh`, all 7 Cloud Run jobs synced.
**Tests at tag**: 1436 backend (`pytest`) + 367 frontend (`jest`).

v2.0 was tagged at Sprint 24 close (2026-06-26 early) covering the Recovery Cut + Quality Overhaul narrative. The 5 sprints since (Urgent Alerts, two School Page UX bug-bash sprints, SEO URL Slug, Security & Dependency Refresh) plus the 2026-06-26 SEO audit small-change-lane all warranted a release tag too — they're substantial. Per owner choice, framed as `v2.0.1` to keep `v2.0` as the milestone marker, with `v2.0.1` capturing the cleanup-to-production-ready work.

The v2.0 series collectively marks the point where:

1. The broadcast pipeline became reliable enough to leave the `sjktconnect-monthly-blast` scheduler running unattended (Sprint 23 + later News Digest Stuck-Loop Fix).
2. The news matcher actually consults its own curated alias table (Sprint 24 architectural fix).
3. School pages have SEO-friendly URLs that put the school name in the path (Sprint 28).
4. Dependency CVEs are cleared and broadcast admin endpoints have explicit role gates (Sprint 29 audit-driven).
5. Legacy URL 404s are 301'd at Cloudflare (small-change-lane 2026-06-26).

Months of incremental work consolidated under one release narrative. The next milestone (v2.1) will be content-quality on the genuinely thin pages (DUN, constituency) — surfaced by the 2026-06-26 SEO audit but deferred from v2.0 per owner decision that school pages don't need redesign.

---

## Features Delivered

### Monthly digest pipeline (Sprint 24)

- **One card per story.** A 47-article month now renders as ~10 story cards, ranked by a hybrid score `(article_count × 2) + max_relevance + severity_bonus`. Multi-source coverage dominates but high-impact single articles still compete. Dropped articles roll into a "Plus N other articles" footer so coverage is never silently hidden. See [`backend/broadcasts/services/topic_clusterer.py`](../backend/broadcasts/services/topic_clusterer.py).
- **Schools in the Spotlight** redesigned as a 2-column table (State + Schools). Counts inline as dim `(N)` next to state names. All schools listed without truncation.
- **Take Action** redesigned as unified editorial cards — white background, brand-purple top accent, brand-coloured icons. Replaces the prior lime/blue/amber pastels. See [`backend/templates/broadcasts/monthly_blast_v2.html`](../backend/templates/broadcasts/monthly_blast_v2.html).
- **Recess banner** propagated through every monthly-analyst section.
- **State names** normalised at storage. "Wilayah Persekutuan Kuala Lumpur" → "W.P. Kuala Lumpur" across frontend, API, email, SEO. Single source of truth at storage via `format_state()` in [`backend/schools/utils.py`](../backend/schools/utils.py). Migration `schools/0011_normalise_state_names` rewrites 15 School + 9 Constituency rows.

### News matching (Sprint 24 + 27 + 28 + 28.1)

- **`SchoolAlias` table now consulted by the news matcher** (Strategy 1.5 in `_resolve_school_codes` — see [`backend/newswatch/services/news_analyser.py`](../backend/newswatch/services/news_analyser.py)). Single IN-query against normalised forms; activates 1,500+ seeded aliases AND every HANSARD-source alias added via migrations. The matcher had never consulted the alias table before this release — an architectural gap discovered mid-Sprint-24.
- **Variant generator** bridges bracket↔single-quote (`(Timur)` ⇄ `'Timur'`), drops/adds Ladang/Ldg prefix, and bridges letter↔digit boundaries (`PJS1` ⇄ `PJS 1`, also `Boh1` ⇄ `Boh 1`).
- **Spelling-drift aliases** for the most-common cases: Jenderata/Jendarata (4 schools), Kuala Kubu Baru/Bharu, St Teresa/Theresa Convent, West Country (Timur)/'Timur', Kathumba/Katumba (silent-h), Jawa Lane/Lorong Java (English↔Malay). 45+ alias rows across migrations `hansard/0008`, `0009`, `0010`, `0011`.
- **`Bhg ⇔ Bahagian ⇔ Division` bridge in `seed_aliases.py`** (Sprint 28). For schools whose name contains the keyword + a number/Roman numeral, the generator now emits both synonym variants automatically. Closes the systemic gap that mis-tagged 7 Labu articles to the only-school-with-Bahagian (ABDB006) and only-school-with-Division (MBD0067).
- **`relabel_labu_mistags` one-off cleanup** (Sprint 28.1) — relabelled 7 historical mis-tagged articles; deleted in Sprint 29 per cleanup rule.
- **`rematch_schools --force-all`** flag (Sprint 28.1) — re-processes articles whose mentions already have moe_codes; needed for cases where the first-resolution overwrote the Gemini-extracted name.
- **UTF-8 stdout** on `rematch_schools` for Tamil-character article titles (was crashing on Windows cp1252).

### Broadcast send reliability (Sprint 23 + later News Digest Stuck-Loop Fix + Sprint 25)

- **Duplicate-Broadcast guard at compose time.** Aborts if a SENT/SENDING/DRAFT broadcast already exists with matching `kind` + coverage window. The 2026-05-02 duplicate-April incident (4 Broadcast rows, ~80–300 subs got the same digest twice) cannot recur.
- **Brevo quota allowance** (transient, not terminal). Quota exhaustion sends what fits today and leaves the broadcast SENDING for the daily `resume-sending` job to drain across days. A failed quota *probe* also leaves SENDING (retry tomorrow) instead of FAILED. Un-breaks urgent alerts whose audience exceeds the daily cap.
- **14-day coverage-anchored fortnight guard** on news digest. Weekly cron, fortnightly cadence enforced in data — eliminates the double-fire-at-day-8 bug. Calendar-self-healing after any delay.
- **Headline subjects** for news digest broadcasts (big-story title becomes the subject).
- **Per-kind sender name** — `NEWS_DIGEST` + `URGENT_ALERT` arrive from "SJK(T) News"; everything else stays "SJK(T) Connect". Sender address unchanged so DKIM/DMARC unaffected.
- **`Broadcast.Status.CANCELLED`** formalised in the model (migration `broadcasts/0007`).
- **Stuck-anchor tripwires** — `compose_news_digest` warns at 21-day coverage windows and aborts at 35+ days unless `--force-window` is passed.
- **FAILED-broadcast sweep** — `resume_sending` exits non-zero (`BROADCAST_FAILED_ALERT`) while any broadcast is FAILED with `updated_at` in the last 7 days.
- **Recess detection** (`HansardSitting.status=COMPLETED` filter) sets `parliament_was_in_session=False` for recess months.
- **Urgent Alert review-by-default** (Sprint 25). `URGENT_ALERT_REQUIRE_REVIEW` default flipped to `true` in [`backend/sjktconnect/settings/base.py`](../backend/sjktconnect/settings/base.py). The 09:30 MYT cron now creates DRAFT broadcasts only — admin sanity-checks before send.
- **Send-Test admin endpoint** (Sprint 25). `POST /broadcast/send-test/<pk>/` with up to 5 arbitrary recipient emails, `[TEST]` subject prefix, bypasses Brevo quota gate, leaves broadcast DRAFT. Lets admins verify a Parliament Watch / Urgent Alert / Monthly Blast draft on their own inbox before releasing.
- **Kind filter dropdown** on broadcast list (Sprint 25) — `?kind=URGENT_ALERT` etc. narrows the admin view.

### School page UX (Sprints 26 + 27 + 28 + 28.1)

- **Phone + email validation** on all admin edit forms (Sprint 26). New [`frontend/lib/validation.ts`](../frontend/lib/validation.ts) with `isValidPhone()`, `isValidEmail()`, `phoneError()`, `emailError()`. `EditableField` extended with `error`/`pattern`/`patternTitle` props. Server-side mirror in `SchoolEditSerializer.validate_phone/fax` + `SchoolLeaderAdminSerializer.validate_phone`. Three locales (en/ms/ta).
- **MY-specific phone digit-count rules** (Sprint 28). Mobile (`01X`) 10–11 digits, landline (`0[2-9]`) 9–10 digits, `+60` normalisation. Truncated numbers like `012209000` now fail.
- **TIADA accepted as phone sentinel** (Sprint 28.1). MOE's "no value" marker passes through both FE and BE validators. Any-case `TIADA`, `N/A`, `none`, `-` accepted.
- **Leader phones normalised on save** (Sprint 28.1). `SchoolLeaderAdminSerializer.validate_phone` now `format_phone()`s the input. Migrations `schools/0013` + `schools/0014` backfill existing leader rows to `+60-X XXX XXXX`. `format_phone` itself extended to recognise mobile prefixes (010–019).
- **Session Type → `SelectField`** dropdown (Sprint 26 #2). Constrained to the 2 MOE-published SESI values; backend `validate_session_type` rejects anything else.
- **MP `tel:` URL strips multi-number** (Sprint 26 #6) — `firstPhoneForTelUri()` in `ContactMPCard.tsx` splits on `/`, `,`, `;`.
- **MP Facebook hidden for generic ParlimenMY URLs** (Sprint 26 #5) — two-layer fix: frontend `isUsableMpFacebookUrl()` + backend `is_generic_facebook_url()` in `parliament/services/mp_scraper.py`.
- **State filter `?state=Selangor` crash fix** (Sprint 26 #4). `FitBoundsOnStateFilter` now coerces DRF string `gps_lat`/`gps_lng` via `Number()` + `Number.isFinite()` before `bounds.extend()`.
- **Tamil name de-duplicated** from `SchoolProfile` details box (Sprint 26 #3) — single source of truth in the hero.
- **GPS edit unblocked for SUPERADMIN** (Sprint 28.1). 4-layer bug fix: removed `gps_lat`/`gps_lng` from `read_only_fields`, added serializer `.update()` SUPERADMIN gate, threaded `context={"request": request}` from the view, frontend rounds to 7 dp on input + serializer-side quantize.
- **`Kg.Simee` → `Kg. Simee`** (Sprint 28.1). `to_proper_case` now inserts space between dot-joined token parts. Migration `schools/0012` fixes 3 affected schools (KG.SIMEE, CEP.NIYOR KLUANG, K.PATHMANABAN).

### SEO (Sprint 28)

- **`/school/<name-slug>-<city-slug>-<moe-code>` canonical URL.** School pages now have SEO-friendly URLs containing the school name and city, not just a code. `subramaniya-barathee-gelugor-pbd1088` instead of `PBD1088`. New [`frontend/lib/urls.ts`](../frontend/lib/urls.ts) with `schoolPath()`, `parseSchoolSlug()`, `isCanonicalSchoolSlug()`. Page handler accepts both slug AND legacy bare-code; non-canonical visits 301 to the canonical slug. Sitemap + JSON-LD `@id`/`url` + `<link rel=canonical>` all emit the slug form.
- **Cloudflare legacy URL 301s** (2026-06-26 small-change-lane). 148 of 157 GSC 404 URLs cleared: `/{en,ta,ms}/claim*` (legacy magic-link URLs from Sprint 11a deletion) and `*.aspx` (pre-revamp Tamil Foundation site URLs) both 301 to `/`. Cloudflare ruleset `1af056d066e44a5885c933227a413981` extended to 3 rules total (the 2 new ones + Sprint 22's www→root canonical).

### Server-side ISR revalidation (Sprint 27 + 28.1 + 29)

- **Backend-driven cache invalidation after admin edits.** Sprint 27 added a `/api/revalidate` Next.js route handler; Sprint 28.1 fixed it to revalidate the literal slug URL (the dynamic-segment form `revalidatePath(..., 'page')` is unreliable in Next 16). Sprint 29 (TD-21) moved the trigger backend-side: [`backend/schools/services/revalidation.py`](../backend/schools/services/revalidation.py) POSTs to the route handler after `serializer.save()` in `SchoolEditView` + leader CRUD endpoints, sending a shared `X-Revalidate-Token` header. Browser-side trigger removed. Closes both the DoS amplifier (unauthenticated route) AND the "stale browser fails to revalidate" failure mode.

### Data + content quality

- **MOE April 2026 refresh** applied 2026-05-28. New `import_schools --skip-fields` flag preserves clean contact data when the upstream MOE file types phone/postcode as floats.
- **Topic clustering** of monthly digest news articles (Gemini, fail-open). New `--preview-html PATH` flag on `compose_monthly_blast` for safe local renders.
- **News triage** — Gemini prompt tightened, 4-domain blocklist for off-topic real-estate news.
- **9 frontend label strings** updated `January 2026 → April 2026` across en/ms/ta.

### Operational hardening (post-2026-05-20 silent-rot recovery + Sprint 29)

- **`backend/scripts/update_jobs.sh`** — idempotent, reads `sjktconnect-api`'s current image and syncs all 7 Cloud Run jobs to match. **Mandatory after every backend deploy** — the silent-rot incident (21 days of crashed news-pipeline runs) was caused by jobs running pre-migration code while the api service had moved on.
- **Cloud Monitoring alert policy** (id `7654330557139407611`) fires on 2+ failed Cloud Run job executions in 24h, notifying `admin@tamilfoundation.org`.
- **Broadcast admin views SUPERADMIN-gated** (Sprint 29, TD-20). New `SuperuserRequiredMixin` in [`backend/broadcasts/views.py`](../backend/broadcasts/views.py) combines `LoginRequiredMixin` + `UserPassesTestMixin` with role-aware `handle_no_permission`: anonymous → 302 login, authenticated non-superuser → 403. Applied to all 6 broadcast admin views. Replaces undocumented "Google OAuth ≠ Django User row" invariant.
- **Dependency CVE refresh** (Sprint 29, TD-19). Django 5.2.11 → 5.2.15 (16 CVEs), Pillow 11.3.0 → 12.2.0 (7 CVEs on community upload path), cryptography 46.0.5 → 49.0.0 (5 CVEs), lxml 6.0.2 → 6.1.1 (1 CVE). npm side: `ws` high cleared, `next-intl` 4.9.1 → 4.13.0 (proto-pollution), `postcss` < 8.5.10 → ≥ 8.5.10 via npm `overrides` (XSS). From 28 npm vulns to 19 (all jest dev-chain, test-only, deferred).

---

## Behaviour Changes

- `monthly-blast` Cloud Scheduler **un-paused** (was PAUSED since 2026-05-02). Auto-fires on the 1st of each month at 09:00 MYT.
- School page URLs are now `/school/<name-slug>-<city-slug>-<moe-code>` (e.g. `/en/school/subramaniya-barathee-gelugor-pbd1088`). Old bare-code URLs 301 to the canonical slug.
- State filter chips, school detail pages, SEO metadata, search results, and email templates now display **"W.P. Kuala Lumpur"** instead of "Wilayah Persekutuan Kuala Lumpur".
- News article school tags that previously rendered as gray unlinked text now resolve and link to school pages.
- Monthly digest subject line is `"<Month Year>: <Gemini headline>"`. May 2026 example: "May 2026: Private Sector Boosts SJK(T) Ladang Labu; Sedenak Gets Piped Water…".
- "Data source" label on school pages now reads "April 2026".
- MP CTA in monthly blast points to `/{locale}/constituencies` (was `/parliament-watch`).
- Phone numbers (school + leader) display canonical `+60-X XXX XXXX` form throughout.
- Broadcast admin endpoints (`/broadcast/*`) now return 403 for any signed-in non-superuser. Previously they relied on the architectural invariant that only `createsuperuser` created Django Users.

---

## Known Issues / Outstanding Items (post-v2.0)

- **TD-06 / TD-24**: Supabase egress monitoring checkpoint was scheduled for 2026-05-08 and never recorded. Pending operational check (1-line: open Cloud Monitoring dashboard `f1722366-2df9-4446-9941-7cda5c019615`, record last-7-day MB/day).
- **TD-12**: `hansard/pipeline/extractor.py` at 26% coverage. Test-coverage padding; not blocking. Deferred per `docs/decisions.md`.
- **19 jest dev-chain npm vulns**: test-only, never bundled. Auto-fix wants a SemVer-major jest regression which is worse than the moderate finding. Stays deferred until upstream patches in-major.
- **Future SEO follow-up**: 2026-07-17 GSC re-pull target. If "Crawled - currently not indexed" remains >300, revisit DUN/constituency page enrichment (those are the genuinely thin pages, not school pages).

---

## Architecture Notes

No service-boundary or tech-stack changes since v1.x. Cross-cutting items worth flagging:

- **`SchoolAlias` is now shared between Hansard and News matchers.** Still lives in the `hansard` app for historical reasons (cross-cutting concern that grew in one app), imported as `from hansard.models import SchoolAlias` in [`backend/newswatch/services/news_analyser.py`](../backend/newswatch/services/news_analyser.py). A future refactor could move it to `schools/models.py` — out of scope for v2.0; logged in `docs/decisions.md`.
- **`SuperuserRequiredMixin`** lives inline in [`backend/broadcasts/views.py`](../backend/broadcasts/views.py) rather than as a project-wide helper. Premature abstraction across 3 apps that share no other code. Extract if a second app needs the same gate.
- **Server-driven ISR revalidation** uses a shared-secret header (`X-Revalidate-Token`). Chosen over HMAC-signed payloads or JWT-like tokens because the threat is DoS amplification, not replay/tampering. Easy rotation: regenerate the secret + update both Cloud Run env vars. See `docs/decisions.md`.

---

## Security / Access Notes

- **Dependency CVEs cleared** (Sprint 29). See above.
- **Broadcast admin endpoints** now explicitly SUPERADMIN-gated (was implicitly safe via architectural invariant).
- **`/api/revalidate` Next route handler** now requires `X-Revalidate-Token` header (was unauthenticated DoS amplifier).
- **`REVALIDATE_TOKEN`** added to Cloud Run env vars on both `sjktconnect-api` + `sjktconnect-web` (matching opaque value). `REVALIDATE_WEBHOOK_URL=https://tamilschool.org/api/revalidate` on api only.
- **Cloud Run env vars otherwise unchanged**. Brevo API key, Gemini API key, Cloudflare zone-scoped token, Toyyib Pay credentials, Gmail OAuth credentials all in place from prior sprints.
- No new role models, no PII handling changes.

---

## Deployment State at tag

- `sjktconnect-api-00135-kxm` at 100% traffic
- `sjktconnect-web-00127-vhh` at 100% traffic
- All 7 Cloud Run jobs synced via `update_jobs.sh`
- Migrations applied since v1.x baseline: `broadcasts/0007` (CANCELLED status), `schools/0011` (W.P. state names), `schools/0012` (Kg.Simee space), `schools/0013` + `0014` (leader phone backfill), `hansard/0008` (Jenderata), `hansard/0009` (KKB/St Teresa/West Country), `hansard/0010` (Bahagian/Division), `hansard/0011` (Kathumba/Jawa Lane).
- `monthly-blast` scheduler ENABLED.
- Cloudflare ruleset id `1af056d066e44a5885c933227a413981` has 3 rules: legacy `/claim*` + `*.aspx` 301s, plus the Sprint 22 www-canonical.
- Cloud Run env vars set on both services: `REVALIDATE_TOKEN` (matching). api also has `REVALIDATE_WEBHOOK_URL`.

**Tests at tag**: 1436 backend (`pytest`) + 367 frontend (`jest`).
