# Sprint 36 Retrospective — Site-quality omnibus

**Duration**: 2 days, 2026-07-05 → 2026-07-07
**Commits**: 14
**Deploys**: 3 api (last: `sjktconnect-api-00161-wx2`), 6 web (last: `sjktconnect-web-00191-mhb`)
**Tests**: 1519 → 1528 backend (+9), 366 frontend (unchanged)

## What Was Built

Three unrelated owner-flagged threads that each mattered but none warranted a standalone sprint. Bundling them into one close entry lets them share the retrospective + deploy overhead:

1. **Tamil Foundation canonical-name rename** across the whole surface (emails, donate page, About, Privacy, Terms) in en/ms/ta. MCEF (which is a separate org — not a Tamil Foundation alias) purged. Trilingual canonical set saved to memory. Owner-set Tamil + Malay style rules applied (Pertubuhan not Organisasi; பண்பாடு not கலாச்சாரம்; no மற்றும் in authored Tamil).

2. **Newsletter improvements**: News-Watch fortnightly digest gets the same letterhead header as the monthly blast; `Forward to a friend` copy updated to reference the news blast + a link back to `/en/news`; `resume_sending` gained a 20h min-batch guard to prevent the fortnightly digest + resume cron from both draining the same broadcast in one calendar day.

3. **Map + search UX**: 528 pins on the country/state map now cluster via `@googlemaps/markerclusterer` (the dep was in package.json since Sprint 1.3 but had never been wired); InfoWindow made responsive for 320-375px mobile viewports; search placeholder simplified to schools-only.

4. **Search overhaul**: `/api/v1/search/` now queries the `SchoolAlias` table (1500+ rows for Hansard matching, never used for public search until now); adds `name_tamil` search for Tamil-script users; alias generator extended with 8 common Malay abbrev pairs (Sri/Seri, Bkt/Bukit, etc.). Prod re-seed added 597 fresh variant rows.

## What Went Well

- **The Tamil Foundation rename swept cleanly the first time** because I checked all three locale files + all Django template locations before touching one string. Zero regressions.
- **Canonical-names memory landed early**. Once I saved it, every subsequent copy question could be answered by referencing the memory file — no drift, no re-litigation.
- **Search overhaul had a clean bucket model** with useful ranking (moe_code > canonical alias > direct name > tamil > weak alias). Deterministic sort within a bucket → tests could assert stable positions. Direct-name bucket as belt-and-braces meant the pre-existing test (which didn't seed aliases) still passed.
- **Prod verification via curl right after seed_aliases ran** confirmed all three canonical demos worked (`Sri Alam`, `Sungai Muar`, `Bahagian 4`). One-command validation of a change touching 528 schools + a query engine rewrite.

## What Went Wrong

### 1. I got the Malay style rule inverted, then had to sweep again

**Symptom**: Owner-set Malay rule was "always Pertubuhan, never Organisasi". I recorded it in memory as the exact opposite ("always Organisasi, never Pertubuhan") and swept 4 `pertubuhan` occurrences → `organisasi`. Owner caught it within one turn.

**Root cause**: I read the owner's guidance too quickly and confidently paraphrased in the wrong direction. Then I codified my paraphrase into memory before it was verified.

**System change**: When an owner sets a language-usage rule, quote their exact wording back and confirm the direction before writing memory. Added to `docs/lessons.md`.

### 2. Map clustering v1 crashed the map page

**Symptom**: First attempt at wiring MarkerClusterer with vis.gl's `<AdvancedMarker>` + ref-callback-into-state pattern triggered a React error boundary immediately on map mount.

**Root cause**: vis.gl re-instantiates the underlying `AdvancedMarkerElement` on every parent render. My guard `prev[key] === marker` never held because the element identity kept changing → 528 setState calls per render → infinite update loop → React bailed.

**System change**: (a) Reverted immediately (5 minutes wall-clock) to restore the map. (b) Skipped vis.gl's `<AdvancedMarker>` component entirely for v2 — went straight to raw `google.maps.marker.AdvancedMarkerElement` in a single `useEffect`. Lesson added to `docs/lessons.md`: don't pair `<AdvancedMarker>` + ref-callback + setState with clusterer.

### 3. Map clustering v2 rendered ZERO pins

**Symptom**: v2 deploy shipped. Page rendered without crashing but showed no school pins at all. Prior state (pre-clustering) had all 528 pins; new state showed none.

**Root cause**: I removed the vis.gl `<AdvancedMarker>` JSX to avoid the ref-callback pattern from v1. But `<AdvancedMarker>` was ALSO the thing that triggered vis.gl to auto-load the `google.maps.marker` library. Once removed, `google.maps.marker.PinElement` was undefined at runtime, and my defensive `!google.maps?.marker?.PinElement` guard silently no-op'd the whole effect. Result: no crash, no pins, no error in the console. The worst kind of failure — "renders but empty".

**System change**: v2.1 fix: `useMapsLibrary("marker")` from vis.gl to explicitly trigger the load, gate the effect on the returned namespace being non-null, use `markerLib.PinElement` (not the global). Lesson added: when swapping vis.gl JSX for raw Maps API calls, always audit which libraries the JSX was auto-loading and replace each with `useMapsLibrary`. Silent-empty bugs are worse than crashes because they don't fire error boundaries or console errors.

### 4. Job execution failed on first try because of `--args` semantics

**Symptom**: `gcloud run jobs execute --args=manage.py --args=seed_aliases` failed with "container may have exited abnormally" twice.

**Root cause**: Cloud Run Jobs store the entire command as `args` (there's no separate `command` field). The existing job's args were `[python, manage.py, run_hansard_pipeline]`. My override `[manage.py, seed_aliases]` dropped the leading `python` → container tried to exec `manage.py` directly with no interpreter → crash.

**System change**: `--args=python --args=manage.py --args=seed_aliases` (include the interpreter). Fix took one iteration once the YAML export showed the args layout. Not enough of a repeat-risk to add to `lessons.md` — this was self-inflicted by not reading the job spec first.

## Design Decisions

### Direct-name search kept as bucket #3 (belt-and-braces)

**Decision**: SearchView's ranked buckets include `moe_code` (1), strong alias (2), direct name/short_name icontains (3), name_tamil (4), weak alias (5). Direct-name is redundant when aliases are seeded — every school's name is already in the OFFICIAL/SHORT alias rows.

**Alternatives considered**:
- Query aliases only + drop direct-name: cleaner, less code. Rejected because it made the pre-existing test (which doesn't seed aliases) fail. Any test that creates a School without also seeding its aliases would silently break search — chore to enforce, easy to forget.
- Force seed_aliases in the test base class: rejected — adds coupling between test setup and a mgmt command; slows every test class.

**Rationale**: Direct-name is a ~free query on an already-indexed field. If aliases are ever stale (e.g. a school added between deploys, DB restored from an older snapshot), search keeps working. Ranked below strong alias so it doesn't compete for the #1 slot on a canonical name search.

**Trade-offs**: Slightly more query work per search (one extra `School.objects.filter(Q(name__icontains) | Q(short_name__icontains))`). Fine for a 528-row table with indexes.

**Revisit if**: The table grows past ~10k schools (won't happen — MOE's SJK(T) count is stable) OR search latency measurably degrades.

### Two separate crons instead of a single-window guard

**Decision**: The double-send fix was a min-hours guard inside `resume_sending`, not a reshuffle of cron times. `sjktconnect-fortnightly-digest` still fires at 09:00 MYT; `sjktconnect-resume-sending` still fires at 10:00 MYT.

**Alternatives considered**:
- Move `sjktconnect-resume-sending` to 06:00 MYT (before compose crons): fragile. Brevo quota reset timing isn't guaranteed exactly at UTC midnight, and 06:00 MYT is 22:00 UTC of the previous day — quota may not have refreshed yet.
- Merge the two into one compose-then-drain cron: bigger change, ties the compose cadence to the drain cadence.
- Add a compose-side lock: introduces state that both jobs would need to check.

**Rationale**: The min-hours guard is a targeted fix at the point where the incorrect behaviour manifests. Cron times stay independent, which matches how the operator thinks about them ("digest fires Monday morning; drain runs daily").

**Trade-offs**: `resume_sending` now has one more state check per broadcast. Adds one `.aggregate(Max("sent_at"))` per broadcast per run — negligible.

**Revisit if**: The 20h choice ever silently skips an intended drain (owner reports a broadcast stuck in SENDING for >2 days).

## Numbers

- **Commits**: 14
- **Deploys**: 3 api + 6 web
- **Tests**: 1528 backend + 366 frontend
- **Prod aliases table**: 3050 → 4182 (+597 fresh variants, mostly Sri/Seri, Bkt/Bukit, Sungai/Sg, etc.)
- **Wall-clock**: ~1.5 working days of active engagement across 2 calendar days
- **Prod state at close**: api `sjktconnect-api-00161-wx2`, web `sjktconnect-web-00191-mhb`
