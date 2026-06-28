# Sprint 32 Retrospective — Per-school enrolment trend + admin polish bundle

**Closed**: 2026-06-29
**Effort**: ~10h across 2 days, 12 commits
**Final state**: api `sjktconnect-api-00143-5ml`, web `sjktconnect-web-00173-9mg`

## What Was Built

What started as a research question ("can we get historical SJK(T) enrolment data?") landed as the most data-dense per-school feature on the platform plus a stack of operational fixes the owner surfaced along the way.

1. **8-year per-school enrolment trend** — new model + migration + bulk-import command + 6-snapshot historical backfill (3,152 rows in prod) + a properly-scaled SVG line chart on every school's right sidebar. Conditional colour: emerald if Δ ≥ 0, rose if Δ < 0. No chart-lib dependency. Stitch-prototyped first.
2. **Hansard pipeline retries late-publish PDFs** — new `NO_PDF` status + `--retry-failed-days=7` default flag so yesterday's failures get re-attempted before today's discovery. 145 historical false-FAILED rows cleaned up.
3. **Parliament Watch `noStore()` safeguard** — fixed a user-visible "0 meetings tracked" regression caused by a build-time api blip baking empty data into the 24h ISR cache.
4. **Admin direct photo upload** — closed the Sprint 14 design gap (only community users could upload; SUPERADMIN had no path).
5. **Community-upload attribution** — "Uploaded by {name}" replaces generic "Community upload" in the lightbox, with the MOE-DL "KPM-Guru" suffix stripped.
6. **Pending-moderation badge on UserMenu** — admins now see a red count badge on their avatar + a direct deep-link to the queue.
7. **5-photo gallery dropout** — silent off-by-one in SchoolPhotoGallery.
8. **Support card cleanup** — removed broken plain-text "DuitNow QR" (Maybank-rejected with `MB02`), tightened layout, removed the instruction box.

## What Went Well

- **Owner-supplied historical files** (OneDrive 4 × XLSX) transformed an abstract research question into a real feature in <2 hours from "discovered" to "live with 6-snapshot timeseries". Without those files we'd still be staring at a single-snapshot baseline. Lesson: ask before researching.
- **Deep-research workflow paid for itself** despite the synthesis step failing. The 30 Jun 2022 archive.data.gov.my snapshot was found via the workflow's fan-out search; without it we'd be at 5 snapshots not 6.
- **Stitch-first kept the chart redesign cheap.** Two passes (initial design + colour-flip approval) before any code was written. The Stitch screen also gave a precise visual contract — "X-axis years evenly spaced, Y-axis value-scaled with gridlines" was unambiguous and shipped in one round.
- **Inline-SVG chart vs chart-lib**: zero bundle impact, fully SSR-able, no hydration concerns. Worth the ~200 lines of layout math.
- **`noStore()` safeguard** (commit `0a06f51`) is the kind of fix that future-proofs the platform — one bad build during any future deploy can't poison a 24h cache again. Cost: 12 lines.

## What Went Wrong

### 1. Six chart-height iterations before settling

**Symptom**: shipped the chart at H=200 (Sprint 32 initial), got "card too short", bumped to H=300, got "now too tall", went to H=240, got "still tall", finally H=180 was right. Five deploys for a single CSS value.

**Root cause**: I never *measured* either card's height before guessing — relied on visual inference from screenshots and arithmetic estimates that were off by ~140px. When the user finally asked "what is the height of the school details box?" I measured (334px) in 2 seconds and realised both cards were already within 10px of each other on the 300×240 build.

**What system change prevents recurrence**: when a layout dimension question comes up, **measure first via Playwright `getBoundingClientRect()` before adjusting**. Added to `docs/lessons.md`.

### 2. Background deploy + concurrent edit = stale builds

**Symptom**: owner reported the support-card layout change still wasn't visible after I'd queued the deploy. Investigation: I'd started a `cloud run deploy` in the background, then immediately edited the source for the *next* change. The background build captured the source *at start time*, not *at commit time* — so the deploy that landed had only the first edit, not the second.

This happened twice in a row on the support-card sequence (QR removal → layout change → instruction-box removal). Three separate deploys, each capturing a different source snapshot.

**Root cause**: `gcloud run deploy --source .` packages the local directory at the moment the command runs, not at any specific git revision. Background-then-edit creates a race that only resolves correctly if each edit waits for its own deploy.

**What system change prevents recurrence**: when multiple changes are coming in fast, **either (a) queue them all into one commit and ONE deploy, or (b) wait for each deploy to land before starting the next edit**. Don't background-deploy then edit. Added to `docs/lessons.md`.

### 3. ISR-bust env-var change didn't actually serve the new code

**Symptom**: after the deploy-race above, I tried to recover by bumping `ISR_CACHE_BUST`. The page kept serving the old support card.

**Root cause**: `gcloud run services update --update-env-vars` creates a new revision but uses the **same container image** as the prior revision. If the prior revision's image was built from stale source (per the deploy race above), the env-var bump doesn't help — you get a new revision with empty fetch cache but the same broken code.

**What system change prevents recurrence**: ISR-bust via env var only works when the latest *built* image already has the code you want to serve. If you've been background-deploying with concurrent edits, you may need to trigger a fresh `--source .` build before busting cache. Added to `docs/lessons.md`.

### 4. Zero tests for any of the Sprint 32 features

**Symptom**: `SchoolEnrolmentSnapshot`, `import_enrolment_snapshots`, `EnrolmentTrend`, `admin_image_upload_view`, the badge — all shipped without tests.

**Root cause**: bias toward shipping during owner-driven iteration. Each piece felt small enough to skip tests "for now". Compounded: 5 small "no-test" shippings = a feature-area with no regression net.

**What system change prevents recurrence**: noted as test-debt in CHANGELOG. Next sprint should be a no-feature catch-up: write tests for the Sprint 32 surface area (admin upload endpoint permission gates, snapshot import command, enrolment_history serializer field, sparkline render states).

### 5. Broken QR shipped in Sprint 4.1 and stayed broken for ~2 months until owner tested it

**Symptom**: support card carried a plain-text "DuitNow QR" since Sprint 4.1 that no real banking app could parse. Discovered today when the owner finally tried scanning it with Maybank.

**Root cause**: the original implementation was authored as if "DuitNow QR" just meant "QR containing the bank account number". Real DuitNow QR is a strict EMVCo TLV payload with a PayNet-issued merchant ID + CRC16. No test ever scanned it; no automated check would catch it.

**What system change prevents recurrence**: payment integrations need a **real-device smoke test before ship**. Added to `docs/lessons.md`: any UI claiming "scan to pay" must be tested with at least one real banking app before merging to main.

## Design Decisions

### Why inline-SVG instead of Recharts / Chart.js / Apex

Considered Recharts (~50 KB gzipped). For a single 6-point line chart on each school page, that's massive. Inline SVG with manual coordinate math: ~200 lines, 0 KB dependency, fully SSR-able (no client-only quirks), no hydration boundary. Trade-off accepted: chart features (zoom, pan, animated transitions) would be hard to add later. We don't need them for this use case.

### Why "discrete-year X positioning" instead of true time-fraction

Owner wanted "the latest 2026 value to align with the 2026 tick". With time-fraction positioning, a 30 April 2026 snapshot lands at ~92% of the X axis (because X axis runs to Dec 2026). Two solutions: (a) shrink X_END to the latest data date, (b) snap each data point to its calendar-year-start position. Chose (b) — simpler, matches how readers parse "yearly trend" charts, and the gap between Mar 2025 and Apr 2026 (real spacing) wasn't useful information anyway.

### Why conditional colour (emerald/rose) instead of single brand colour

Owner ask. Trend-direction colour communicates the school's story at a glance — a green-line school is doing fine; a red-line school is in decline. Indigo-only would have been visually consistent but less informative. The accent strip on the card stays indigo (matches sibling cards) so it's not a complete brand break.

### Why remove the QR entirely instead of trying to generate a real one

Real DuitNow QR requires a PayNet-issued merchant ID per school, registered via each school's bank. We'd need 200+ schools to individually register as DuitNow merchants. 6-month project, school-by-school onboarding. Not feasible. Removing the broken one + providing the account number with a Copy button is honest and works for any Malaysian bank's DuitNow Transfer flow.

## Numbers

- 12 commits
- 6 web deploys, 2 api deploys
- 6 SVG height iterations on one chart
- 6 historical per-school enrolment snapshots imported (3,152 rows)
- 528 schools now show an 8-year trend chart
- 0 tests added (debt)
- ~10h elapsed time
