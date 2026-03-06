# Data Quality Fixes — Retrospective (2026-03-06)

## What Was Built
- Data migration to normalise school name abbreviations (Ldg/Sg/Bkt/Kg -> full form)
- Matcher improvement: punctuation stripping in candidate extraction
- Gmail OAuth setup for feedback@tamilschool.org
- Fixed 11 failing tests (env var mocking)

## What Went Well
- Root cause analysis: identified MOE data inconsistency as source of matching failures (95 schools with "Ldg" vs 198 with "Ladang")
- User's instinct to fix source data directly (rather than expand aliases) was the right call — cleaner solution
- Migration ran cleanly on production (110 schools normalised)
- Matching improved from 28% to 46% (38 -> 62 matched)

## What Went Wrong
- Supabase connection pooler (port 6543) extremely slow for per-row trigram queries — matching 96 mentions took over 10 minutes via pooler
- Cloud Run rematch job initially timed out (600s default) — had to increase to 1800s
- Investigation revealed 72 "unmatched" mentions are all generic category references ("SJK(C) dan SJK(T)") — no actual school names to match

## Design Decisions
- **Data migration over alias expansion**: Fixing school names in the source table means all downstream code (aliases, matching, display) benefits automatically
- **Reversible migration**: Included reverse function (Ladang->Ldg etc.) for safety
- **Punctuation fix in matcher**: Commas after school names ("SJK(T) Ladang Jeram, kejayaan...") were preventing exact matches

## Numbers
- 110 schools normalised (abbreviations expanded)
- 2,106 aliases re-seeded
- 62/134 mentions matched (was 38)
- 72 mentions correctly unmatched (generic references)
- 851 backend tests passing
- Cloud Run rematch job: 6m33s execution time
