# Self-Correcting Report Engine — Retrospective (2026-03-07)

## What Was Built
- 4-layer quality architecture: Generator, Evaluator, Corrector, Learner
- QualityLog model recording every evaluation cycle
- quality_flag (GREEN/AMBER/RED) on SittingBrief and ParliamentaryMeeting
- Evaluator service: separate Gemini call scoring output against 3-tier rubric
- Corrector service: targeted re-prompt + deterministic code fixes, 3-attempt circuit breaker
- School name repairer: comma removal, filler word removal, fuzzy matching
- Learner service: recurring pattern detection across quality logs
- Integration into both brief generator and report generator
- Permanent quality rubric, prompt version registry, learner patterns file
- Full design document (535 lines, approved before implementation)

## What Went Well
- Brainstorming-first approach: full design doc written and approved before any code
- Subagent-driven execution: 10 implementation tasks dispatched sequentially, each with fresh context
- Zero regressions: 898 tests passing after all changes, no existing test broken
- Clean separation: evaluator, corrector, learner are independent services, easy to test and evolve
- Fail-open design prevents the quality engine from blocking publication
- Circuit breaker prevents infinite correction loops

## What Went Wrong
- Git push failed due to expired HTTPS token for tamilfoundation account — delayed final push
- No major code issues — the subagent approach caught small issues (model field names, unique constraints) per-task

## Design Decisions
- **Fail-open evaluator**: If Gemini API is down, reports publish without evaluation rather than blocking
- **Verdict recomputed, not trusted**: The evaluator AI returns a verdict, but we recompute it from the tier scores — don't trust AI to grade its own work correctly
- **Rubric is permanent, prompts are temporary**: The rubric survives model changes; prompts are versioned and disposable
- **3-attempt circuit breaker**: Hard cap prevents runaway API costs from infinite correction loops
- **Learner writes to files, not code**: Pattern flags go to markdown files that agents read — no automatic code changes

## Numbers
- 12 commits
- 46 new tests (898 backend total)
- 7 new files created (4 services, 3 docs)
- 3 existing files modified (models, brief generator, report generator)
- 1 migration added
- Design doc: 535 lines
- Rubric: 85 lines
