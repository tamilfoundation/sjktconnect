# v2.0 — Recovery Cut + Quality Overhaul

**Tagged**: 2026-06-26
**Spans**: Sprint 23 (2026-05-11) + Sprint 24 (2026-06-26)
**Live revisions**: `sjktconnect-api-00121-7hb`, `sjktconnect-web-00115-82q`

This is the project's first numbered release tag. The v2.0 cut marks the point where the broadcast pipeline became reliable enough to leave the `sjktconnect-monthly-blast` scheduler running unattended — and where the news matcher actually consults its own curated alias table.

---

## Features Delivered

### Monthly digest pipeline (Sprint 24)

- **One card per story.** A 47-article month now renders as ~10 story cards, ranked by a hybrid score `(article_count × 2) + max_relevance + severity_bonus`. Multi-source coverage dominates but high-impact single articles still compete. Dropped articles roll into a "Plus N other articles" footer so coverage is never silently hidden.
- **Schools in the Spotlight** redesigned as a 2-column table (State + Schools). Counts are inline as dim `(N)` next to state names. All schools listed without truncation.
- **Take Action** redesigned as unified editorial cards — white background, brand-purple top accent, brand-coloured icons. Replaces the prior lime/blue/amber pastels.
- **Recess banner** propagated through every monthly-analyst section (the Recovery Cut had only fixed the executive summary).
- **State names** normalised at storage. "Wilayah Persekutuan Kuala Lumpur" → "W.P. Kuala Lumpur" across frontend, API, email, SEO. Single source of truth; zero per-component formatting needed.

### News matching (Sprint 24)

- **`SchoolAlias` table now consulted by the news matcher** (Strategy 1.5 in `_resolve_school_codes`). Single IN-query against normalised forms of `{original name, distinctive part, every variant, each prefixed with "SJK(T) "}` — one DB round-trip activates 1,500+ existing seeded aliases AND every HANSARD-source alias added via migrations. The matcher had never consulted the alias table before this release — an architectural gap discovered mid-sprint by an unlinked-tag screenshot.
- **Variant generator** now bridges bracket↔single-quote (`(Timur)` ⇄ `'Timur'`) and drops/adds Ladang/Ldg prefix.
- **Spelling-drift aliases** for the four most-common cases that journalists vary: Jenderata/Jendarata (4 schools), Kuala Kubu Baru/Bharu, St Teresa/Theresa Convent, West Country (Timur)/'Timur'. 31 alias rows total across migrations `hansard/0008` + `hansard/0009`.
- **Letter↔digit boundary** bridging in variant generation (`PJS1` ⇄ `PJS 1`, general — also `Boh1` ⇄ `Boh 1`).
- **`rematch_schools`** now safe on Windows (forces UTF-8 stdout for Tamil-character article titles).

### Broadcast send reliability (Sprint 23 + later News Digest Stuck-Loop Fix)

- **Duplicate-Broadcast guard at compose time.** Aborts if a SENT/SENDING/DRAFT broadcast already exists with matching `kind` + coverage window. The 2026-05-02 duplicate-April incident (4 Broadcast rows, ~80-300 subs got the same digest twice) cannot recur.
- **Brevo quota allowance** (transient, not terminal). Quota exhaustion now sends what fits today and leaves the broadcast SENDING for the daily `resume-sending` job to drain across days. A failed quota *probe* also leaves the broadcast SENDING (retry tomorrow) instead of FAILED. Un-breaks urgent alerts whose audience exceeds the daily cap.
- **14-day coverage-anchored fortnight guard** on news digest. Weekly cron, fortnightly cadence enforced in data — eliminates the double-fire-at-day-8 bug. Calendar-self-healing after any delay.
- **Headline subjects** for news digest broadcasts (big-story title becomes the subject).
- **Per-kind sender name** — `NEWS_DIGEST` + `URGENT_ALERT` arrive from "SJK(T) News"; everything else stays "SJK(T) Connect". Sender address unchanged so DKIM/DMARC unaffected.
- **`Broadcast.Status.CANCELLED`** formalised in the model (no schema change, choices-only migration `broadcasts/0007`). Already present in prod data from earlier manual repairs.
- **Stuck-anchor tripwires** — `compose_news_digest` warns at 21-day coverage windows and aborts at 35+ days unless `--force-window` is passed.
- **FAILED-broadcast sweep** — `resume_sending` exits non-zero (`BROADCAST_FAILED_ALERT`) while any broadcast is FAILED with `updated_at` in the last 7 days. Turns silent FAILED rows into red daily job executions in the Cloud Run alert feed.
- **Recess detection** (`HansardSitting.status=COMPLETED` filter) sets `parliament_was_in_session=False` for recess months so digests don't ship blank Parliament Watch panes during recess.

### Data + content quality

- **MOE April 2026 refresh** applied to prod 2026-05-28 (528 schools updated). New `import_schools --skip-fields` flag preserves clean contact data when the upstream MOE file types phone/postcode as floats (the April release dropped Malaysian leading zeros).
- **Topic clustering** of monthly digest news articles (Gemini, fail-open). New `--preview-html PATH` flag on `compose_monthly_blast` for safe local renders (no Broadcast row, no Brevo call). Preview output is now self-contained (HTML5 shell, UTF-8 charset, base64-inlined hero image) so the file renders correctly when opened directly from disk.
- **News triage** — Gemini prompt tightened, 4-domain blocklist for off-topic real-estate news (`edgeprop.my`, `propertyguru.com.my`, `iproperty.com.my`, `mudah.my`). Auto-approve threshold unchanged at `relevance >= 3`.

### Operational hardening (post-2026-05-20 silent-rot recovery)

- **`backend/scripts/update_jobs.sh`** — idempotent, reads `sjktconnect-api`'s current image and syncs all 7 Cloud Run jobs to match. **Mandatory after every backend deploy** — the silent-rot incident (21 days of crashed news-pipeline runs) was caused by jobs running pre-migration code while the api service had moved on.
- **Cloud Monitoring alert policy** (id `7654330557139407611`) fires on 2+ failed Cloud Run job executions in 24h, notifying `admin@tamilfoundation.org`.

---

## Behaviour Changes

- `monthly-blast` Cloud Scheduler **un-paused** (was PAUSED since 2026-05-02). Auto-fires on the 1st of each month at 09:00 MYT. June 2026 blast composes + sends 1 Jul 09:00 MYT.
- State filter chips, school detail pages, SEO metadata, search results, and email templates now display **"W.P. Kuala Lumpur"** instead of "Wilayah Persekutuan Kuala Lumpur". Backwards-compatibility: the migration's `reverse_code` can rewrite back if needed.
- News article school tags that previously rendered as gray unlinked text (because the matcher couldn't resolve them) now resolve and link to school pages. Verified by `rematch_schools` against historical articles.
- Monthly digest subject line is now `"<Month Year>: <Gemini headline>"` (Sprint 23 dynamic subject). The May 2026 blast was the first using this format: "May 2026: Private Sector Boosts SJK(T) Ladang Labu; Sedenak Gets Piped Water…".
- The "Data source: Ministry of Education, January 2026" label on school pages now reads "April 2026" (matches the actual import).

---

## Known Issues / Outstanding Items

- **None blocking.** The 240 PENDING recipients of Broadcast 86 (May 2026 blast) drain at the next `sjktconnect-resume-sending` cron (~27 Jun 10:00 MYT). All 490 expected to be delivered by 28 Jun.
- **TD-12** — `hansard/pipeline/extractor.py` at 26% coverage. Test-coverage padding; not blocking anything.
- **TD-06** — Supabase egress monitoring checkpoint (PROVISIONALLY RESOLVED pending observation).

---

## Architecture Notes (Step 2)

No service-boundary or tech-stack changes since v1.x. The only cross-cutting architectural shift worth flagging:

- **`SchoolAlias` is now shared between Hansard and News matchers.** It still lives in the `hansard` app for historical reasons (cross-cutting concern that grew in one app), and is imported as `from hansard.models import SchoolAlias` in `newswatch/services/news_analyser.py`. A future refactor could move it to `schools/models.py` — out of scope for v2.0; not blocking; logged in `docs/decisions.md`.

---

## Security / Access Notes (Step 3)

No authentication-model changes, no new secrets, no role changes since v1.x. The 401 the local sender hit during the May 2026 send was an environment issue (no BREVO_API_KEY in my local `.env`), not a security regression — it correctly refused to send rather than spoofing the request.

Cloud Run env vars unchanged. Brevo API key, Gemini API key, Cloudflare zone-scoped token, Toyyib Pay credentials, Gmail OAuth credentials all in place from prior sprints.

---

## Deployment State (Step 5)

Already live as of 2026-06-26:

- `sjktconnect-api-00121-7hb` at 100% traffic
- `sjktconnect-web-00115-82q` at 100% traffic (with ISR cache busted post-`rematch_schools`)
- All 7 Cloud Run jobs synced via `update_jobs.sh`
- 3 migrations applied (`schools/0011`, `hansard/0008`, `hansard/0009`)
- `monthly-blast` scheduler ENABLED
- May 2026 blast (Broadcast 86) in flight: 250/490 sent on 2026-06-26, remainder draining over 2-3 days

**Tests**: 1389 backend (0 failed, 139.94s) + 320 frontend.
