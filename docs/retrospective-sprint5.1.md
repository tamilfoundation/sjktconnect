# Sprint 5.1 Retrospective — Pipeline Automation

**Date**: 2026-03-05
**Duration**: Single session

## What Was Built

Automated the full Hansard pipeline end-to-end:
1. Calendar scraper — parlimen.gov.my meeting dates
2. Auto brief generator — batch sitting briefs
3. Meeting report generator — Gemini executive synthesis
4. Unified pipeline command — 7 steps in sequence
5. WAT workflow — living SOP

## What Went Well

- **WAT framework applied properly**: Workflow → Agent → Tools separation. The pipeline command is the orchestrator, individual scripts are the tools, the workflow document captures learnings.
- **Brainstorming skill caught design issues early**: Identified that the problem was not just "automate analysis" but "the whole pipeline has manual gaps" — calendar sync, briefs, meeting reports all needed automation.
- **Subagent-driven development worked efficiently**: 4 implementation tasks dispatched as subagents, each producing clean code with tests. Spec review caught no issues.
- **Calendar data source identified**: parlimen.gov.my provides structured calendar data including individual sitting dates — eliminates need for heuristic meeting boundary detection.

## What Went Wrong

- Nothing significant. Sprint was focused and well-scoped.
- The subagent for Task 4 (pipeline command) didn't stage its files for commit — caught during manual review.

## Design Decisions

- **Single unified command over separate scheduled jobs**: Simpler to reason about, guaranteed ordering, single point of monitoring.
- **Brief generation stays template-based for now**: Sprint 5.2 will upgrade to Gemini-powered briefs with tighter prompts. This sprint focused on the pipeline infrastructure.
- **Meeting report uses Gemini**: Only happens 3x/year, high value, needs synthesis across multiple briefs.
- **Python difflib fallback for matching**: pg_trgm too slow over network to Supabase. Local difflib is fast and good enough.

## Numbers

- 5 commits
- 30 new tests (750 backend total)
- 4 new files, 2 modified files
- 0 bugs found
