# Hansard Pipeline Automation — Design Document

**Date**: 2026-03-05
**Status**: Approved
**Approach**: Unified pipeline command (Approach A)

## Problem

The Hansard pipeline is only partially automated. The daily Cloud Scheduler discovers new PDFs and extracts mentions, but 5 downstream steps are manual:

- AI analysis (Gemini) — 115 of 193 mentions never analysed, invisible on parliament-watch
- School matching — 65 of 78 visible mentions have no school links (trigram too slow on remote DB)
- MP scorecards — not recalculated after new data
- Sitting briefs — require manual admin action
- Meeting reports — fully manual

Additionally:
- Many mentions have no MP attribution (speaker extraction is weak)
- Briefs are template-based lists, not insightful summaries
- ParliamentaryMeeting records are created manually

## Design

### Architecture: WAT Framework

- **Workflow**: `_workflows/hansard-pipeline.md` — living SOP, updated with learnings after each iteration
- **Agent**: Claude — reads workflow, orchestrates steps, handles failures
- **Tools**: Python scripts in `hansard/pipeline/` and `parliament/services/` — deterministic, testable

### The Unified Pipeline

One management command `run_hansard_pipeline` replaces the current `check_new_hansards --auto-process` in Cloud Scheduler. Runs daily at 8:00 AM MYT.

```
Step 1: sync_calendar           [NEW]     [No AI]    Scrape parlimen.gov.my calendar
Step 2: discover + process      [EXISTS]  [No AI]    Download PDFs, extract text, keyword search
Step 3: match_mentions          [EXISTS]  [No AI]    Link mentions to schools (difflib fallback)
Step 4: analyse_mentions        [EXISTS]  [Gemini]   MP, sentiment, significance, summary
Step 5: update_scorecards       [EXISTS]  [No AI]    Recalculate MP stats
Step 6: generate_briefs         [MODIFY]  [Gemini]   AI-generated sitting summaries
Step 7: generate_meeting_report [NEW]     [Gemini]   Executive synthesis after meeting ends
```

Each step wrapped in try/except — failure in one step does not block others.

### Step 1: Calendar Scraper

**File**: `hansard/pipeline/calendar_scraper.py`

Scrapes `https://www.parlimen.gov.my/takwim-dewan-rakyat.html?uweb=dr&`:
- Main page: 3 meeting blocks per year with date ranges
- Detail pages (`?id=N&ssid=M`): individual sitting dates per meeting

Creates/updates `ParliamentaryMeeting` records with `start_date`, `end_date`, `name`, `short_name`, `term`, `session`, `year`. Idempotent — no-op if meeting already exists with matching dates.

URL patterns:
- Main: `takwim-dewan-rakyat.html?uweb=dr&`
- Detail: `takwim-dewan-rakyat.html?uweb=dr&id={meeting_number}&ssid={penggal}`
- SSL verification disabled (known invalid cert on parlimen.gov.my)

### Step 2: Speaker Extraction Improvement

**File**: `hansard/pipeline/searcher.py` (modify)

Current problem: keyword searcher extracts quotes but often misses the speaker. Hansard PDFs follow a consistent format:

```
Tuan Sivakumar a/l Varatharaju [Batu Gajah]: Tuan Yang di-Pertua, saya ingin...
```

Improvement: look backwards from each keyword match to find the most recent speaker line. Pattern: title (Tuan/Puan/Dato'/Yang Berhormat) + name, optionally with `[Constituency]`.

Gemini's role changes from "guess the MP" to "validate/enrich" — adds party, classifies mention type, assigns significance/sentiment, writes summary.

### Step 3: School Matching

No code changes needed. The pipeline calls `match_mentions()` on unmatched mentions. Uses Python difflib fallback (not pg_trgm) to avoid the remote DB performance issue.

### Step 4: Mention Analysis

No structural changes. The pipeline calls `analyse_mentions` on mentions with empty `ai_summary`. Tighter prompt: one sentence summaries, factual, no filler.

### Step 5: Scorecards

No changes. Calls existing `update_all_scorecards()`.

### Step 6: AI-Generated Sitting Briefs

**File**: `parliament/services/brief_generator.py` (modify)

Replace the template-based brief with a Gemini call. Input: all analysed mentions for a sitting. Output: narrative summary.

Prompt principles:
- Substance dictates length — 1 procedural mention gets 2 sentences; 6 MPs debating budget could be 300 words
- One opening line capturing the day's theme
- Factual, analytical, no padding or repetition
- Every sentence must add information or insight

Finds sittings with analysed mentions but no brief, generates automatically.

### Step 7: Meeting Report Generator

**File**: `parliament/services/report_generator.py` (new)

Trigger: `today > meeting.end_date` and `meeting.report_html` is empty.

Input to Gemini: all sitting briefs for the meeting period + aggregate stats (total mentions, unique MPs, schools mentioned).

Output: `report_html`, `executive_summary` (first 2-3 sentences for card preview), `social_post_text` (280 chars).

Prompt principles:
- Structure: Key Findings, MP Activity, Policy Signals, What to Watch
- Length matches substance — 200 words for quiet meetings, up to 1,000 for significant ones
- No repetition of what briefs already cover — this is the "so what?"
- Factual, analytical, executive-grade

Happens at most 3 times per year.

### Historical Rebuild

**File**: `hansard/management/commands/rebuild_all_hansards.py` (new)

One-time command to re-process all historical Hansards with the improved speaker extraction and tighter prompts:

1. Fetch all completed HansardSitting records
2. Re-download each PDF, re-extract, re-search with improved speaker extraction
3. Delete old mentions, replace with fresh ones
4. Run downstream: match, analyse, scorecards, briefs, reports

Flags: `--dry-run`, progress logging, rate limiting (0.5s between Gemini calls).

Schedule: run once at a quiet hour after the pipeline code is built. ~97 sittings, ~193 mentions, estimated ~10 minutes.

### Pipeline Command

**File**: `hansard/management/commands/run_hansard_pipeline.py` (new)

Flags:
- `--dry-run` — show what each step would do
- `--skip-calendar` — skip calendar sync
- `--skip-analysis` — skip Gemini calls

### Cloud Run Changes

Update `sjktconnect-check-hansards` job image to run `run_hansard_pipeline` instead of `check_new_hansards --auto-process`. Same schedule (daily 8:00 AM MYT). Requires `GEMINI_API_KEY` env var on the job.

## New Files

| File | Purpose | AI? |
|------|---------|-----|
| `hansard/pipeline/calendar_scraper.py` | Scrape parliamentary calendar | No |
| `hansard/management/commands/run_hansard_pipeline.py` | Unified pipeline orchestrator | No |
| `parliament/services/report_generator.py` | Meeting report generator | Yes |
| `hansard/management/commands/rebuild_all_hansards.py` | One-time historical rebuild | Uses existing |
| `_workflows/hansard-pipeline.md` | WAT workflow SOP | N/A |

## Modified Files

| File | Change |
|------|--------|
| `hansard/pipeline/searcher.py` | Improve speaker name extraction |
| `parliament/services/brief_generator.py` | Replace template with Gemini call |
| `parliament/services/gemini_client.py` | Add brief/report prompts, tighten mention prompt |

## Guiding Principles

- Substance dictates length, never pad
- Every sentence adds information or insight
- Each level adds insight, not length: mention = what was said, brief = what happened that day, report = what it means
- Speaker attribution comes from the parser (factual), not Gemini (inference)
- Pipeline is idempotent — safe to re-run
- Failures in one step don't block others
- Workflow document updated with learnings after each iteration
