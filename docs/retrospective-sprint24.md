# Retrospective — Sprint 24: Monthly Digest Quality Overhaul + Scheduling Resume

**Started**: 2026-05-11 (engineering tasks 1–9)
**Resumed**: 2026-06-25
**Closed**: 2026-06-26

## What Was Built

Sprint 24 was originally scoped as a 16-task plan to make the monthly digest good enough to un-pause the `sjktconnect-monthly-blast` scheduler. Tasks 1–9 (recess prompt, news triage, topic clustering, schools-by-state, template overhaul, footer CTAs, smoke test) landed on 2026-05-15. The session resumed 41 days later and expanded into seven new sub-tasks (10b–10h) covering things the original spec didn't anticipate:

- **News section collapse (10b)** — 47 articles in a month now render as ~10 story cards with a hybrid score `(article_count × 2) + max_relevance + severity_bonus`. Dropped + Other-bucket articles tally into a "Plus N other articles" footer so coverage is never silently hidden. Lead-article picker is deterministic (highest relevance → earliest published_date → lowest pk).
- **State normalisation (10c)** — `format_state()` collapses "Wilayah Persekutuan Kuala Lumpur" → "W.P. Kuala Lumpur" at storage. Migration `schools/0011` rewrites 15 School + 9 Constituency rows (also title-cases the historical Constituency UPPERCASE drift). Frontend, API, email, SEO all get the compact form with zero per-component formatting.
- **Preview HTML5 shell (10c)** — `--preview-html` wraps the bare-div email body in an HTML5 shell with `<meta charset="UTF-8">` + Tamil-capable font fallback. Solves the Windows-cp1252 mojibake when opening the preview file in a browser. Hero image inlines as base64 data URL so the file is fully self-contained.
- **Jenderata aliases (10d)** — Migration `hansard/0008` adds 14 HANSARD aliases for 4 schools where article spelling ("Jenderata") differs from MOE canonical ("Jendarata"). One-letter difference; explicit aliases are safer than fuzzy matching.
- **April 2026 frontend label (10e)** — 9 hardcoded strings updated across `en.json` / `ms.json` / `ta.json` after discovery that the 27 May MOE re-import wasn't reflected in the data-source label.
- **MOE file references (10f)** — `import_schools` docstring + help + CLAUDE.md Data Files table point at `SenaraiSekolahWeb_April2026.xlsx`.
- **Take Action editorial cards (10g)** — Replace lime/blue/amber pastels with unified white + brand-purple top accent + brand-coloured icons. Content updates per user feedback.
- **News matcher Strategy 1.5 + variant additions + KKB/St Teresa/West Country aliases (10h)** — Investigation of June 2026 unlinked-tag screenshots revealed that the news matcher had **never** consulted the `SchoolAlias` table. Wired alias lookup as a single IN-query against `{name, distinctive, every variant, each prefixed with "SJK(T) "}`. Plus bracket↔single-quote and drop/add Ladang/Ldg variants. Migration `hansard/0009` adds 17 alias rows for the 4 specific articles from the screenshots.

Plus operational work during close:
- Two api deploys (`00120-25k` → `00121-7hb`), one web deploy (`00114-2jq`), one ISR cache-bust revision (`00115-82q`).
- `update_jobs.sh` run twice to sync 7 Cloud Run jobs.
- `rematch_schools` re-resolved historical news articles against new aliases (all 5 originally-broken articles from the screenshots now fully resolved).
- May 2026 monthly blast composed + sent (Broadcast 86, 490 recipients).
- `sjktconnect-monthly-blast` scheduler un-paused.

## What Went Well

- **The user's "investigate first" instinct paid off.** The screenshot showing unlinked tags led to discovering the SchoolAlias architectural gap. If we'd just added more aliases via migration without auditing the matcher, the Jenderata migration shipped in 10d would have been completely inert — the news matcher wouldn't have read it. The investigation surfaced the real root cause before more time was wasted.
- **Hybrid score formula validated against real data.** First render of the April 2026 preview with the new top-N cap produced 8 cards from 47 articles + 23 footer remainder. Math added up; the Dengkil cluster (4 source articles) collapsed cleanly to 1 card. No tuning needed.
- **Test discipline held through scope creep.** Each sub-task (10b through 10h) added tests before/alongside the code change. Final suite: 1389 passed, 0 failed. The +14 net tests across 6 files would have been impossible to retrofit if we'd shipped first and tested later.
- **Live verification before commit.** The matcher fix was verified against the actual prod DB ("'SJK(T) Ladang Sungai Muar' → RESOLVED to JBD7068") before commit, not after. Caught that 2/4 cases would resolve from code alone (Sungai Muar via existing SHORT alias, West Country via bracket variant) and only 2 needed the migration data.
- **`--preview-html` mode + in-place sample patching** kept Gemini/Imagen spend low. Most iterations on schools-by-state layout and Take Action design happened by patching the existing rendered sample HTML in place, not by re-rendering ($0.05 per render avoided ×4–5 iterations).

## What Went Wrong

### 1. The news matcher silently bypassed the alias table for the entire project's history

- **What happened**: `_resolve_school_codes` was structured as six in-table strategies against `School.short_name`, with no consultation of `SchoolAlias`. The hansard matcher (separate code path) used aliases; the news matcher didn't. This silently invalidated every HANSARD-source alias for news matching — including the Jenderata migration shipped earlier in this same sprint.
- **Root cause**: parallel implementation of two matchers (hansard in 2026-03, news in 2026-03) by the same author in adjacent sprints without an architectural decision to share the lookup table. The matchers each grew their own strategy stack. The shared table was right there but the news matcher never referenced it.
- **System change**: Strategy 1.5 added in 10h (single IN-query against alias_normalized for {name + distinctive + variants + prefixed forms}). Lesson added to `docs/lessons.md`: when two services match against the same concept, audit shared-state lookups before adding strategies — a third strategy in the wrong matcher is worse than a one-line lookup against the canonical table.

### 2. The Take Action redesign was lost mid-session

- **What happened**: The redesign was applied to `monthly_blast_v2.html` in the working tree but never committed. During later investigation work (specifically the `git checkout HEAD -- backend/schools/utils.py backend/schools/tests/test_utils.py` operation used to isolate parallel uncommitted PJS changes from my commit), the template change to `monthly_blast_v2.html` was also silently reverted as a working-tree side-effect of `git apply` operations on the snapshot patches. Discovered only when staging the news-matcher commit — the modified file was missing from `git status`.
- **Root cause**: the snapshot-and-revert pattern was applied per-file but not audited per-file afterwards. The user's parallel work in `utils.py`/`test_utils.py` was snapshotted before revert; my Take Action change in `monthly_blast_v2.html` was NOT snapshotted (it was not a parallel file) but was lost during the snapshot/revert dance because the file's working-tree state wasn't preserved across operations.
- **System change**: lesson added to `docs/lessons.md` — when using the snapshot-revert-edit-restore pattern to isolate parallel work in shared files, **first run `git stash -u --keep-index` for the rest of the working tree as a safety net**, OR snapshot every uncommitted file (not just the ones being isolated). The redesign was straightforward to re-apply (8 minutes) but losing 30 minutes of design work to an avoidable git ripple is the kind of mistake that compounds.

### 3. ISR cache served stale data after rematch_schools ran

- **What happened**: Deploy sequence was `migrations → api → jobs sync → web → smoke test → rematch_schools`. The web deploy happened *before* `rematch_schools`, so bots/visitors between the web deploy and the rematch populated the fresh container's ISR cache with the OLD mentioned_school data (empty moe_codes → gray unlinked tags). User saw stale gray tags on the West Country article minutes after rematch confirmed all 5 articles fully resolved in the DB.
- **Root cause**: deploy-order assumption that "fresh container = empty ISR cache" ignored the window between deploy and data refresh. Any visitor in that window seeds the cache with old data, and the cache then holds for 24h.
- **System change**: lesson added to `docs/lessons.md` — for any deploy that depends on a separate data-refresh step (`rematch_schools`, `import_schools`, bulk data fixes), the correct order is **data refresh first, then web deploy** OR **data refresh + ISR cache bust after web deploy**. The cache-bust env-var pattern from the 2026-05-20 silent-rot recovery worked here exactly as designed (`--update-env-vars=ISR_CACHE_BUST=$(date +%s)` flushed the cache; West Country tag turned blue on next refresh).

### 4. Local sender's Brevo 401 left Broadcast 86 in a half-sent state

- **What happened**: `compose_monthly_blast --auto-send` ran locally with `SJKTCONNECT_ALLOW_PROD_DB=1` pointed at Supabase. Compose succeeded (Broadcast row + 490 PENDING recipients created). The sender then immediately failed at the Brevo quota probe with HTTP 401 (no BREVO_API_KEY in my local `.env`), but had already flipped the Broadcast status to SENDING. The "Broadcast 86 sent." log message was misleading — nothing was sent. Required a follow-up `gcloud run jobs execute sjktconnect-resume-sending` to actually drain the recipients.
- **Root cause**: the `--auto-send` path sets `status=SENDING` before any send happens, and the error path doesn't roll back the status. Plus the local environment isn't representative of prod (no BREVO_API_KEY) but the command pretended otherwise.
- **System change**: deferred to Sprint 25 (urgent-alerts + Parliament Watch sprint). Either: (a) add a `--no-sender` flag for compose-only-from-local + always trigger sends via Cloud Run jobs, OR (b) detect missing BREVO_API_KEY upfront in `--auto-send` and bail before flipping status. Either keeps `Broadcast.status` honest. Not blocking — the resume-sending job recovered the broadcast cleanly in this case.

## Design Decisions

(Full entries appended to `docs/decisions.md`.)

- **Storage normalisation for state names** (hybrid approach) — chose to rewrite stored values via migration rather than format at display time. Zero frontend changes; single source of truth. Trade-off: storage encodes display style, but the W.P. abbreviation is a stable canonical form for Malaysia, so this trade-off is comfortable for the foreseeable future.
- **Hybrid scoring for cluster ranking** — `(count × 2) + max_relevance + severity_bonus` chosen over (a) article-count alone (would ignore high-impact singles) or (b) Gemini-driven top-N (more expensive + less predictable). Deterministic + cheap + testable.
- **Surgical aliases over fuzzy matching** for one-letter spelling drift (Jenderata/Jendarata, Baru/Bharu, Theresa/Teresa). Risk of false positives from a fuzzy threshold low enough to bridge "Baru/Bharu" was too high (other school names like "Penang"/"Penag" would falsely match). Curated alias migrations scale fine for the long tail of journalist spelling variations.

## Numbers

- **Tests**: 1389 backend (+14 net) + 320 frontend (unchanged). 139.94s full backend run.
- **Migrations applied to prod**: 3 (`schools/0011`, `hansard/0008`, `hansard/0009`). Total 24 + 14 + 17 = 55 rows written.
- **Deploys**: 2 api (`00120-25k`, `00121-7hb`), 2 web (`00114-2jq`, `00115-82q` cache-bust). All 7 Cloud Run jobs synced twice.
- **Broadcast 86**: 490 recipients. 250 drained on send day (213 DELIVERED + 22 SENT + 15 BOUNCED = 3% hard-bounce rate, auto-deactivated by Sprint 8.6 webhook handler). 240 PENDING to drain over the next 1–2 days.
- **Wall time**: ~5 hours active work spread across two sessions (2026-05-15 + 2026-06-25/26).
- **API spend** (Gemini + Imagen): ~$0.30 across preview re-renders + real compose runs. Hero image generation is the dominant cost (~$0.04/render).
- **Commits**: 8 on `origin/main` (9b657f2, a7c3591, 8ae155e, 13cef72, 88cd95e, 1566617, b060f64, 5b307d8, 5341d55) — 7 mine + 1 parallel PJS work attributed to user.
