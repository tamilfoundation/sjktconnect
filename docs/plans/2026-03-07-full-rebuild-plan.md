# Full Hansard Rebuild — Operational Plan

**Goal:** Rebuild all existing mentions with the improved pipeline (20-page speaker lookback, tightened Gemini prompt, MP resolver, improved school matching), then process missing 2022-2024 meeting periods. Regenerate all briefs and reports.

**Why:** Existing data was extracted with old code — missing speakers, unmatched schools, weak analysis. The pipeline has been significantly improved but the data hasn't been rebuilt.

**Cost:** ~200+ Gemini API calls (Flash tier, well within 10K RPD limit). No monetary cost beyond existing API quota.

---

## Current State

| ID | Meeting | Sittings | Mentions | Report | Action |
|----|---------|----------|----------|--------|--------|
| 8 | 1st Meeting 2023 (Feb-Apr) | 11 (C:11) | 27 | Yes (rebuilt once) | REBUILD |
| 9 | 2nd Meeting 2023 (May-Jun) | 19 (C:11 F:8) | 1 | No | REBUILD |
| 1 | 1st Meeting 2025 (Feb-Mar) | 23 (C:17 F:6) | 12 | Yes | REBUILD |
| 2 | Special Meeting 2025 (May) | 1 (C:1) | 0 | No | SKIP (no mentions) |
| 3 | 2nd Meeting 2025 (Jul-Aug) | 24 (C:19 F:5) | 20 | Yes | REBUILD |
| 4 | 3rd Meeting 2025 (Oct-Dec) | 44 (C:35 F:9) | 68 | Yes | REBUILD |
| 5 | 1st Meeting 2026 (Jan-Mar) | 32 (C:19 F:13) | 6 | Yes | REBUILD |
| 6 | 2nd Meeting 2026 (future) | 0 | 0 | No | SKIP (future) |
| 7 | 3rd Meeting 2026 (future) | 0 | 0 | No | SKIP (future) |

FAILED sittings (44 total) are non-sitting days (Fridays, recesses) that return HTML instead of PDF. These are correctly failed and should stay as-is.

## Missing Meeting Periods (not yet in database)

From the parlimen.gov.my archive (15th Parliament):
1. **1st Term, 1st Meeting** (Dec 2022 - Feb 2023) — first session of 15th Parliament
2. **2nd Term, 3rd Meeting** (Oct 2023 - Dec 2023)
3. **3rd Term, 1st Meeting** (Feb 2024 - Apr 2024)
4. **3rd Term, 2nd Meeting** (Jul 2024 - Aug 2024)
5. **3rd Term, 3rd Meeting** (Oct 2024 - Dec 2024)

The calendar scraper only fetches the current term. These must be discovered via `check_new_hansards --start --end`.

---

## Phase 1: Rebuild Existing Meetings

For each meeting with completed sittings, rebuild mentions using `rebuild_all_hansards`.

### Step 1: Dry run
```bash
cd backend
python manage.py rebuild_all_hansards --dry-run
```
Verify: lists ~113 completed sittings, shows expected mention counts.

### Step 2: Rebuild extraction only (no Gemini yet)
```bash
python manage.py rebuild_all_hansards --skip-analysis
```
This re-downloads PDFs, re-extracts text, re-searches with improved speaker extraction (20-page lookback), re-matches schools. No Gemini calls = fast.

### Step 3: Run Gemini analysis
```bash
python manage.py run_hansard_pipeline --skip-calendar
```
This analyses all un-analysed mentions, runs MP resolver, updates scorecards, generates briefs.

### Step 4: Regenerate reports
```bash
python manage.py generate_meeting_reports
```
Generates fresh reports for all meetings that have mentions.

### Step 5: Verify
Check mention counts, MP identification rate, school matching rate, report quality.

---

## Phase 2: Process Missing Meeting Periods (2022-2024)

For each missing period, discover and process PDFs using date ranges.

### Period 1: 1st Term, 1st Meeting (Dec 2022 - Feb 2023)
```bash
python manage.py check_new_hansards --start 2022-12-01 --end 2023-02-12 --auto-process
```

### Period 2: 2nd Term, 3rd Meeting (Oct 2023 - Dec 2023)
```bash
python manage.py check_new_hansards --start 2023-10-01 --end 2023-12-31 --auto-process
```

### Period 3: 3rd Term, 1st Meeting (Feb 2024 - Apr 2024)
```bash
python manage.py check_new_hansards --start 2024-02-01 --end 2024-04-30 --auto-process
```

### Period 4: 3rd Term, 2nd Meeting (Jul 2024 - Aug 2024)
```bash
python manage.py check_new_hansards --start 2024-07-01 --end 2024-08-31 --auto-process
```

### Period 5: 3rd Term, 3rd Meeting (Oct 2024 - Dec 2024)
```bash
python manage.py check_new_hansards --start 2024-10-01 --end 2024-12-31 --auto-process
```

After each: create ParliamentaryMeeting records, assign sittings, run analysis + matching + briefs + reports.

---

## Phase 3: Final Verification and Deploy

1. Run full test suite (`pytest`)
2. Verify all meetings have reports
3. Spot-check 2-3 reports for quality (no Unidentified MP, schools matched, proper HTML)
4. Deploy backend to Cloud Run
5. Verify on tamilschool.org

---

## Risks

- **parlimen.gov.my SSL/blocking**: Known issue, handled (verify=False, ranged GET)
- **Gemini rate limits**: 1000 RPM, 10K RPD on Flash tier. With 0.5s sleep between calls, ~200 calls = ~2 minutes. Well within limits.
- **Database connection**: Must use direct connection (port 5432) for bulk writes, not pooler.
- **Missing PDFs**: Some dates won't have PDFs (recesses, non-sitting days). These correctly fail and are skipped.
