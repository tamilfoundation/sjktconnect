# Sprint 28.1 Retrospective — Sprint 28 Follow-up Bundle

**Closed**: 2026-06-26
**Wall time**: ~3h end-to-end. 9 owner-reported issues, 9 commits, 11 api deploys + 7 web deploys.
**Scope**: post-Sprint-28-deploy testing surfaced cascade of related bugs across edit flow, validation, ISR cache, naming, news matcher.

## What Was Built

1. **GPS edit unblocked for SUPERADMIN** — removed `gps_lat`/`gps_lng` from `read_only_fields`; added serializer `.update()` SUPERADMIN gate; threaded `context={"request": request}` from the view. + frontend round-to-7dp + serializer-side quantize so Google-Maps-paste precision (15 dp) doesn't 400.
2. **ISR cache invalidation actually works on slug URLs now** — `revalidatePath(segment, 'page')` looked like the right Next.js API but doesn't invalidate cached slug instances in our setup. Client now passes the literal slug; route handler revalidates the actual canonical URL.
3. **TIADA accepted in phone validators** — MOE's "no value" marker passes through both FE and BE.
4. **Leader phones normalised to +60-X XXX XXXX** — serializer-side normalisation on save + migration 0013 backfill. Discovered `format_phone` didn't recognise mobile prefixes (010-019); migration 0014 rerun after fix.
5. **`Kg.Simee` → `Kg. Simee`** — `to_proper_case` now inserts space between dot-joined token parts. Migration 0012 fixes 3 affected schools (also CEP.NIYOR KLUANG, K.PATHMANABAN).
6. **MP CTA in monthly blast points to /constituencies** — template fix.
7. **7 Ladang Labu Bhg 4 articles relabelled** — new `relabel_labu_mistags` command; `rematch_schools` couldn't fix them because first-resolution overwrote the Gemini-extracted name.
8. **Kathumba + Jawa Lane aliases added** — migration `hansard/0011` covers silent-h Tamil transliteration (KBD0053) and English↔Malay translation (NBD4070).

## What Went Well

- **Owner-flagged → diagnosed → shipped feedback loop was tight.** Most fixes cycled in under 15 minutes from report. The rapid-deploy infrastructure (api + web in parallel, jobs sync, ISR cache-bust) held up under the volume.
- **Two-layer validation pattern paid off again.** TIADA, GPS precision, phone normalisation — each landed simultaneously in FE (UX) and BE (trust boundary). No "fix the UX but the API still 400s" surprises.
- **Owner-correct diagnoses guided real fixes.** Twice this turn the user pushed back on my proposed fix layer (Strategy 5 patch → "but we use aliases"; "save still shows green but view stays stale"). Both pushbacks were right; my first cut wasn't. Listened, redirected, shipped the proper fix. Sprint 28's lesson on this is paying out.
- **`format_phone` bug surfaced via migration log** — running `migration 0013` printed "+0 normalised" — that wasn't expected (M. Jeyakumar's number should have matched). 30 seconds of grep'ing area-code lists found that mobile prefixes weren't recognised. Without that telemetry I'd have shipped and silently believed it worked.
- **Single-file scope per fix kept blast radius small.** Almost every commit touches <5 files. Easy to revert if anything broke; easy to scan in PR review.

## What Went Wrong

- **Multiple revalidatePath shapes wasted ~2 cycles.** First fix: pass moe_code, revalidate bare-code only. Second: also revalidate segment with `'page'` type — looked right per docs but didn't actually work. Third: pass literal slug, revalidate that. The Next.js docs for `revalidatePath(path, 'page')` semantics for dynamic segments are ambiguous; should have tested with `curl` BEFORE shipping the second attempt. Lesson already in `lessons.md` ("curl-200 isn't sufficient evidence a client-side fix shipped") — also applies to revalidation: "the route handler returning 200 with the expected path list isn't evidence the cache was actually busted".
- **First GPS fix was incomplete** — moved fields out of `read_only_fields` + added `.update()` gate, but didn't pass `context` from the view. Saw the bug; fixed the visible part; missed the wiring. Should have run a curl-PATCH against the deployed api to verify before declaring done. Lesson: when fixing a "silently dropped" bug, the verification must be end-to-end with the actual UI path, not a unit test of one component.
- **Workspace `.gitignore` pattern `fix_*.py` ate my management command.** Created `fix_labu_mistags.py`, committed, deployed — but the file wasn't in the git index. Caught when execution failed in prod. Renamed to `relabel_labu_mistags.py`, but the first prod-image upload had already taken the original. Cost: one extra api redeploy. Lesson: the workspace anti-clutter rule (`fix_*`, `debug_*`, etc.) is right, but if your "this is a keeper" command needs a non-`fix_` name from the start. Promote/name properly at creation, not after.
- **`relabel_labu_mistags` was reactive cleanup that should have been part of Sprint 28** — Sprint 28's alias-generator fix was the proper systemic answer, but the 7 existing rows needed a one-off rewrite the alias fix couldn't reach. I documented this gap at Sprint 28 close as "operational follow-up" and the owner asked about it directly here. Lesson: at Sprint close, if a systemic fix leaves existing data wrong, the cleanup is part of the sprint, not a follow-up. Either ship it or explicitly defer with an owner-visible "this is what stays broken until X" line.

## Design Decisions

(See `docs/decisions.md` updates — minor additions only since the major patterns are already documented.)

1. **Literal slug in revalidate payload** beats trying to make `revalidatePath(segment, 'page')` work. The dynamic-segment form is well-documented but unreliable in practice for our specific Next 16 + Cloudflare setup. Sending the slug is one extra string in the JSON body; trivial cost, deterministic invalidation.
2. **`format_phone` mobile prefix recognition** — owner's data has more mobile phones than landlines (cabinet members, leadership). The original implementation predated this reality. The extension to 010-019 is small; no need to over-engineer with a phone library when MCMC numbering plan is stable.
3. **`relabel_*` naming convention for one-off cleanup commands** — `fix_*` is gitignored as scratch; `cleanup_*` reads as routine; `relabel_*` is specific and discoverable.

## Numbers

| Metric | Sprint 28 close | Sprint 28.1 close | Delta |
|---|---|---|---|
| Backend tests | 1424 | **1424** | 0 (test-count-neutral fixes — most existing tests just got their expectations updated) |
| Frontend tests | 366 | **367** | +1 (new validation case for TIADA) |
| api revisions | 00121 | 00133-2cf | +11 |
| web revisions | 00118 | 00125-9jl | +7 |
| Commits | f95064d | 1c3032b | +9 |
| Files touched | — | ~16 | — |
| Wall time | — | ~3h | — |

### Articles correctly tagged after Sprint 28.1

| School | Articles before | After |
|---|---:|---:|
| NBD4079 SJK(T) Ladang Labu Bhg 4 | 2 | **9** |
| ABDB006 SJK(T) Ladang Jendarata Bahagian Alpha Bernam | 4 false | **0** |
| MBD0067 SJK(T) Ldg Kemuning Kru Division | 3 false | **0** |
| KBD0053 SJK(T) Ldg Katumba | 0 | **1** |
| NBD4070 SJK(T) Lorong Java | 1 | **2** |

## Operational state

All migrations applied: `schools/0012`, `schools/0013`, `schools/0014`, `hansard/0011`. `seed_aliases` ran on prod after the alias extensions. `rematch_schools` + `relabel_labu_mistags` ran on prod. All 7 jobs synced to api `00133-2cf`. ISR cache-busted twice. No pending operational follow-ups.

## What I'd do differently

- **Smoke-test revalidation before second deploy.** First slug fix attempt looked right in code but silently didn't work. A 30-second curl-then-verify sequence ("save → revalidate → fetch → assert old data is gone") would have caught it before deploy. Add to lessons: when adopting a Next.js API for cache invalidation, the test is "did the rendered HTML actually change", not "did the API return 200".
- **At Sprint close, audit "is there leftover data that the systemic fix won't reach"** — Sprint 28's alias-generator fix was correct AND complete-for-future, but left 7 existing wrong rows. The cleanup command should have been part of that sprint's deliverable, not surfaced when the owner noticed the discrepancy a few hours later.
