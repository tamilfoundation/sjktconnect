# Self-Correcting Meeting Report Engine — Design Document

**Status:** APPROVED
**Date:** 2026-03-07
**Author:** tamiliam + Claude
**Scope:** Sitting briefs (step 13) and meeting reports (step 14) of the Hansard pipeline

---

## 1. Problem Statement

The SJK(T) Connect Hansard pipeline produces sitting briefs and meeting reports from parliamentary proceedings. Currently:

- The report generator (`generate_meeting_reports.py`, 527 lines) has **zero tests**
- There is **no validation** that output meets user needs — only that it exists
- There is **no feedback loop** — the system generates and publishes without learning
- **Illustration drift**: every illustration converges on the same generic template (Parliament dome, sad women in saris, school building) regardless of report content
- **Data errors propagate**: a wrong school name in a sitting brief flows undetected into the meeting report
- **School name variants** (e.g., "SJK(T) Ladang, Mentakab") go unlinked because the matcher doesn't try punctuation-repair transformations

The pipeline works today because it was hand-tuned. It cannot operate autonomously at production quality without a self-correcting layer.

## 2. Design Principles

1. **Credibility is the asset.** Any output that could make users say "you can't trust SJK(T) Connect" is a red line violation. Everything else is improvable.
2. **Fix near the source.** Errors in sitting briefs cascade into meeting reports. Catch them at the brief level.
3. **Absence is a signal.** A meeting with zero Tamil school mentions still gets a short-form report — silence in Parliament is newsworthy.
4. **The rubric is permanent, prompts are temporary.** The rubric defines what "good" means and survives model changes. Prompts are model-specific and versioned.
5. **Quality over cost.** Use the best available model (Gemini 3.0 when available). But hard-cap retries to prevent infinite loops.
6. **Self-correction that repeats becomes prevention.** Repairs applied repeatedly at the corrector level should migrate upstream into the extraction/matching layer.

## 3. Architecture

Four layers wrap around the existing pipeline's steps 13 (sitting briefs) and 14 (meeting reports):

```
┌─────────────────────────────────────────────┐
│  GENERATOR                                  │
│  Existing pipeline output (brief or report) │
│  + code-level post-processing               │
└──────────────────┬──────────────────────────┘
                   ▼
┌─────────────────────────────────────────────┐
│  EVALUATOR                                  │
│  Separate AI call scoring output against    │
│  rubric. Returns PASS / FIX / REJECT with   │
│  specific feedback per criterion.           │
└────────┬─────────┬─────────┬────────────────┘
      PASS       FIX     REJECT
         │         │    (red line)
         │         ▼         │
         │  ┌─────────────┐  │
         │  │  CORRECTOR  │  │
         │  │  attempt≤3? │  │
         │  │  Yes → fix  │  │
         │  │  → re-eval  │  │
         │  │  No → publish│  │
         │  │  with flag  │  │
         │  └─────────────┘  │
         │                   │
         ▼                   ▼
┌─────────────────────────────────────────────┐
│  PUBLISH                                    │
│  Save to database, set is_published=True    │
│  Warning flag + explanatory note if needed  │
└──────────────────┬──────────────────────────┘
                   ▼
┌─────────────────────────────────────────────┐
│  LEARNER                                    │
│  Log quality data, detect patterns,         │
│  maintain prompt version registry           │
└─────────────────────────────────────────────┘
```

## 4. Where the Engine Applies

### 4.1 Stage A: After Sitting Brief Generation

**Trigger:** A new `SittingBrief` is created by `generate_all_pending_briefs()`.

**What the evaluator checks:**
- School names mentioned in the brief are linked to school pages
- Constituency names mentioned are linked to constituency pages
- MP names match known MPs in the database (or are clearly "Unidentified")
- Factual claims (amounts, dates) are traceable to the mention's `ai_summary`
- No fabricated information beyond what the Gemini analysis produced
- Language is accessible (no unexplained acronyms like PPKI, KPM, JKR)

**What the corrector can fix:**
- Re-run school/constituency linkification
- Apply school name repair (comma removal, reordering, fuzzy match)
- Re-prompt for jargon explanation
- Flag unresolvable MP names with "Unidentified MP" label

**Frequency:** ~30-40 briefs per meeting (one per sitting that has mentions).

### 4.2 Stage B: After Meeting Report Generation

**Trigger:** A meeting's `end_date` has passed and `report_html` is empty.

**What the evaluator checks:**
- All applicable sections present (see Section 5 for sparse meeting handling)
- Headline is specific to this meeting's content
- Key Findings cite specific figures, dates, or names from sitting briefs
- MP Scorecard table entries are traceable to sitting briefs
- Executive Responses track time-lag where applicable
- "What to Watch" gives concrete, actionable advice
- No internal contradictions between sections
- Illustration reflects the specific report content, not a generic template
- Illustration is visually distinct from previous reports
- Word count within guidance range

**What the corrector can fix:**
- Re-prompt with evaluator's specific feedback (targeted, not full rewrite)
- Re-generate illustration with more specific visual direction
- Apply code fixes (brackets, HTML entities, table formatting)
- Apply school name repair on unlinked names in report text

**Frequency:** 3-4 reports per year.

## 5. Sparse Meeting Handling

When a meeting has fewer than 3 matched school mentions, the generator produces a **short-form report**:

- **Headline** — still specific (e.g., "Tamil Schools Absent from Budget Debate as Parliament Focuses Elsewhere")
- **Lead paragraph** — acknowledges the absence and contextualises it
- **Single finding** — what was said (if anything), or what was notably not said
- **What to Watch** — what the absence signals for the community

Sections omitted: MP Scorecard, Executive Responses, Policy Signals (insufficient data).

The evaluator uses an adapted rubric for short-form reports — it does not penalise missing sections that were intentionally omitted due to sparsity.

A meeting with **zero mentions** still gets a report. The absence of Tamil school discussion in Parliament is itself intelligence worth publishing.

## 6. The Evaluator

### 6.1 Implementation

A separate Gemini API call (not the same call that generated the report). The evaluator receives:

**Inputs:**
- The generated output (brief or report)
- The source material (mention `ai_summary` fields for briefs; sitting briefs for reports)
- The previous report (for drift detection, reports only)
- The illustration (for relevance check, reports only)
- The rubric criteria (structured list)
- The list of valid schools (528 names + MOE codes) and MPs (222 names + constituencies)

**Output (structured JSON):**

```json
{
  "verdict": "PASS | FIX | REJECT",
  "attempt": 1,
  "tier1_red_lines": {
    "fabricated_facts": {"pass": true, "details": null},
    "wrong_attribution": {"pass": true, "details": null},
    "hallucinated_schools": {"pass": false, "details": "SJK(T) Ladang Bintang not found in school database"},
    "empty_output": {"pass": true, "details": null},
    "internal_contradiction": {"pass": true, "details": null}
  },
  "tier2_quality": {
    "structure_complete": {"score": 10, "feedback": null},
    "headline_specificity": {"score": 6, "feedback": "Headline is generic — 'Tamil School Mentions in Parliament'. Should reference the dominant theme."},
    "key_findings_specificity": {"score": 9, "feedback": null},
    "actionability": {"score": 7, "feedback": "'What to Watch' says 'monitor developments' — too vague. Name the specific commitment to track."},
    "school_linkification": {"score": 8, "feedback": "SJK(T) Ladang, Mentakab unlinked — possible comma-separated name"},
    "mp_attribution": {"score": 10, "feedback": null},
    "jargon_free": {"score": 9, "feedback": null},
    "word_count": {"score": 10, "feedback": null},
    "illustration_relevance": {"score": 4, "feedback": "Illustration shows generic sad scene. Report is about a RM2B budget commitment — should reflect positive development."}
  },
  "tier3_drift": {
    "illustration_similarity": "HIGH — same composition as previous 2 reports",
    "headline_pattern": "OK — different structure from previous",
    "advice_formulaic": "MILD — 'What to Watch' uses same framing as last report",
    "tone_drift": "OK"
  },
  "unlinked_schools": ["SJK(T) Ladang, Mentakab"],
  "repair_suggestions": ["Try removing comma: SJK(T) Ladang Mentakab"]
}
```

### 6.2 Verdict Logic

```
IF any tier1 check fails → verdict = REJECT
ELSE IF average tier2 score < 6/10 → verdict = FIX
ELSE IF any tier2 score < 5/10 → verdict = FIX
ELSE → verdict = PASS
```

Tier 3 drift flags never affect the verdict — they are logged for the Learner only.

### 6.3 Evaluator Prompt

The evaluator prompt is separate from the generator prompt and maintained independently. It includes:

- The full rubric with scoring criteria
- Instructions to cross-reference claims against source material
- The complete school list (names + codes) for hallucination detection
- The complete MP list (names + constituencies + parties) for attribution verification
- Instructions to compare illustration content against report findings
- Previous report text for drift detection

The evaluator prompt is also versioned (see Section 9).

## 7. The Corrector

### 7.1 Three Pathways

**Pathway 1: Re-prompt Gemini (content issues)**

Constructs a targeted correction prompt:

```
You previously generated this report:
[draft]

An independent evaluator identified these issues:
[evaluator feedback — only the failed criteria]

Source material (ground truth):
[sitting briefs]

Fix ONLY the flagged issues. Preserve all sections and content that passed evaluation.
Do not introduce new information not present in the source material.
```

Used for: generic headlines, vague advice, missing specificity, unexplained jargon, tone issues, missing sections.

**Pathway 2: Code fix (mechanical issues)**

Deterministic post-processing, no AI call:
- `(SJK(T))` → `SJK(T)` (bracket regex)
- HTML entity leakage → decode entities
- Table separator bloat → clamp to correct column count
- Re-run school/constituency linkification against current database

Applied automatically before evaluation (pre-cleanup) and again if evaluator still flags them.

**Pathway 3: School name repair (data issues)**

When the evaluator flags an unlinked school name:

1. **Strip punctuation** — remove commas, periods, semicolons within the name and re-match
2. **Drop common filler** — remove "di", "dan" that may have been captured and re-match
3. **Fuzzy match** — trigram similarity on the cleaned name against all aliases
4. **If match found** — update the report text with the correct linked name
5. **If no match found** — leave unlinked, log for Learner as "possible new school name variant"

**Pathway 4: Re-generate illustration (visual issues)**

When the evaluator flags the illustration as generic or mismatched:

1. Extract the dominant theme from Key Findings (celebration? crisis? funding? neglect?)
2. Build a targeted illustration prompt:
   - Specify the scene inspired by **this specific report's** findings
   - Include negative constraints based on drift detection ("Do NOT use the composition of a generic school building with sad onlookers")
   - Specify the emotional register (positive for commitments, concerned for delays, etc.)
3. Re-generate with Imagen

### 7.2 Circuit Breaker

- **Maximum 3 total attempts** (1 original generation + 2 correction cycles)
- Each attempt goes: Generator/Corrector → Evaluator → decision
- **Attempt 3 still has red line violations** → publish with `quality_flag = RED`, log for human review. This should be extremely rare — it means Gemini is consistently fabricating despite explicit instructions not to.
- **Attempt 3 has only Tier 2 issues** → publish with `quality_flag = AMBER` and explanatory notes appended to the report
- **Any attempt passes** → publish with `quality_flag = GREEN`

The quality flag is stored on the database record so the frontend can optionally display a quality indicator or the system can filter reports by quality in future analysis.

### 7.3 Correction Targeting

The corrector does NOT regenerate the entire report on each attempt. It sends:
- The current draft (preserving what passed)
- Only the failed criteria with specific feedback
- The source material for fact-checking

This minimises the risk of "fixing one thing, breaking another" — a common failure mode in iterative AI correction.

## 8. The Learner

### 8.1 Quality Ledger (Database Model)

```python
class QualityLog(models.Model):
    """Records every evaluation cycle for a brief or report."""

    # What was evaluated
    content_type = models.CharField(max_length=20)  # "brief" or "report"
    sitting_brief = models.ForeignKey(SittingBrief, null=True)
    meeting = models.ForeignKey(ParliamentaryMeeting, null=True)

    # Generation context
    prompt_version = models.CharField(max_length=20)  # e.g., "v3"
    model_used = models.CharField(max_length=50)  # e.g., "gemini-2.5-flash"
    attempt_number = models.IntegerField()

    # Evaluator output
    verdict = models.CharField(max_length=10)  # PASS, FIX, REJECT
    tier1_results = models.JSONField()  # Red line check results
    tier2_scores = models.JSONField()   # Quality gate scores
    tier3_flags = models.JSONField()    # Drift detection flags

    # Corrections applied
    corrections_applied = models.JSONField(default=list)
    # e.g., [{"type": "re-prompt", "target": "headline", "feedback": "..."},
    #        {"type": "name-repair", "original": "SJK(T) Ladang, Mentakab",
    #         "repaired": "SJK(T) Ladang Mentakab", "school_code": "CBD7094"}]

    # Final outcome
    quality_flag = models.CharField(max_length=10)  # GREEN, AMBER, RED

    created_at = models.DateTimeField(auto_now_add=True)
```

### 8.2 Pattern Detection

After every report cycle completes (all briefs + report evaluated and published), the Learner runs pattern detection queries against the quality ledger:

**Recurring failures:**
- Same Tier 2 criterion scoring < 6 in 3+ consecutive reports → flag for prompt improvement
- Same school name repair applied across multiple reports → flag for upstream fix in candidate extractor
- Illustration relevance consistently low → flag for illustration prompt redesign

**Trends:**
- Average quality scores trending down across reports → flag for investigation
- Correction count trending up → system is getting worse, not better
- New red line violations appearing → possible model regression after upgrade

**Output:** Pattern flags are written to `docs/quality/learner-patterns.md`:

```markdown
# Learner Pattern Flags

## Active Flags

### FLAG-001: Illustration drift (detected 2026-03-07)
- **Pattern:** illustration_relevance scored < 5 in 3/3 reports
- **Root cause:** Imagen prompt is too generic, converges on same template
- **Recommended fix:** Restructure illustration prompt to lead with
  specific scene description derived from Key Findings, add negative
  constraints against previous compositions
- **Status:** Open

### FLAG-002: Comma-separated school names (detected 2026-03-07)
- **Pattern:** "SJK(T) Ladang, Mentakab" repaired in 2 reports
- **Root cause:** Hansard transcription uses commas within school names
- **Recommended fix:** Add comma-removal variant to candidate extractor
  in matcher.py, not just corrector
- **Status:** Open — migrate fix upstream
```

An agent reviewing this file knows exactly what to fix and where. When a flag is resolved (code change made), it moves to a "Resolved" section with the commit reference.

### 8.3 Prompt Version Registry

Stored as a structured file at `docs/quality/prompt-registry.md`:

```markdown
# Prompt Version Registry

## meeting_report

| Version | Date | Model | Avg Score | Reports | Key Change |
|---------|------|-------|-----------|---------|------------|
| v1 | 2026-03-05 | gemini-2.5-flash | 5.2 | 1 | Initial prompt |
| v2 | 2026-03-05 | gemini-2.5-flash | 6.1 | 1 | JSON response mode |
| v3 | 2026-03-06 | gemini-2.5-flash | 7.8 | 1 | Journalistic rewrite, MP taxonomy |

## sitting_brief

| Version | Date | Model | Avg Score | Briefs | Key Change |
|---------|------|-------|-----------|--------|------------|
| v1 | 2026-03-05 | gemini-2.5-flash | 7.5 | 26 | Initial prompt |

## evaluator

| Version | Date | Model | Key Change |
|---------|------|-------|------------|
| v1 | 2026-03-07 | gemini-2.5-flash | Initial rubric |

## illustration

| Version | Date | Model | Key Change |
|---------|------|-------|------------|
| v1 | 2026-03-06 | imagen-4.0 | Initial prompt |
```

When an agent upgrades the model (e.g., Gemini 2.5 Flash → Gemini 3.0), it:
1. Generates a test report using the new model with the current prompt
2. Evaluates it against the rubric
3. Compares scores against the registry's baseline for the current prompt version
4. If scores improve → adopt new model, log new registry entry
5. If scores degrade → keep current model, log the comparison for investigation

## 9. Data Model Changes

New models to add:

```
QualityLog          — evaluation records (Section 8.1)
```

New fields on existing models:

```
SittingBrief        — quality_flag (GREEN/AMBER/RED)
ParliamentaryMeeting — quality_flag (GREEN/AMBER/RED)
```

New files:

```
parliament/services/evaluator.py      — evaluator service
parliament/services/corrector.py      — corrector service
parliament/services/learner.py        — learner service
parliament/services/name_repairer.py  — school name repair utilities
docs/quality/learner-patterns.md      — pattern flags (Learner output)
docs/quality/prompt-registry.md       — prompt version tracking
docs/quality/rubric.md                — the permanent quality rubric
```

Modified files:

```
parliament/services/brief_generator.py    — integrate evaluator/corrector loop
parliament/management/commands/generate_meeting_reports.py — integrate evaluator/corrector loop
parliament/models.py                      — QualityLog model, quality_flag fields
```

## 10. The Rubric (Permanent Document)

The rubric is maintained separately at `docs/quality/rubric.md`. It is model-agnostic and prompt-agnostic. It defines what "good" means for end users of SJK(T) Connect:

**For sitting briefs:**
- Every school name mentioned is linked to its school page
- Every constituency mentioned is linked to its constituency page
- MP names are verified against the MP database or labelled "Unidentified"
- Factual claims are traceable to the Gemini analysis of the source mention
- Language is accessible to a PTA chairman with no political background
- No fabricated information beyond what the source mention contains

**For meeting reports:**
- Headline tells the reader what happened, not that something happened
- Key Findings contain specific amounts, dates, names, or commitments
- MP Scorecard entries are traceable to sitting briefs
- Executive Responses track government responsiveness, including time-lag
- "What to Watch" gives advice a school board can act on next Monday
- Illustration captures the dominant theme of this specific report
- Report does not contradict itself across sections
- Absence of mentions is reported honestly, not padded

**For illustrations:**
- Visual scene reflects the specific findings (positive news → positive imagery)
- Illustration is visually distinct from the previous report's illustration
- Tamil Indian representation is present and respectful
- No text other than "SJK(T)" appears in the image
- Emotional register matches the report's dominant theme

This rubric evolves slowly and deliberately. Changes require justification linked to user feedback or Learner pattern flags.

## 11. Operational Notes

### 11.1 When Does the Engine Run?

- **Sitting briefs:** Evaluated immediately after generation, as part of the daily pipeline run. The evaluator/corrector loop adds ~30 seconds per brief (one extra Gemini call + potential correction).
- **Meeting reports:** Evaluated immediately after generation, when a meeting's end_date passes. The full loop (up to 3 attempts) may take 5-10 minutes including illustration regeneration.

### 11.2 Cost Estimate

Per meeting report cycle (assuming worst case — 3 attempts):
- 3 Gemini generator calls (report) ≈ $0.01
- 3 Gemini evaluator calls ≈ $0.01
- 3 Imagen illustration calls ≈ $0.09
- ~30 Gemini evaluator calls for briefs ≈ $0.05
- **Total per meeting: ~$0.16 worst case**
- **Annual (4 meetings): ~$0.64**

Cost is negligible. Quality model upgrades (Gemini 3.0) may cost more per call but at this volume it remains trivial.

### 11.3 Failure Mode

If the Gemini API is completely down:
- Generator fails → sitting/report not generated → existing pipeline error handling applies
- Evaluator fails → treat as PASS (fail-open) → publish without evaluation → log the gap
- Corrector fails → publish current draft with AMBER flag → log for manual review

The engine should never block publication entirely due to evaluator/corrector failures. A report without quality checks is better than no report at all.

### 11.4 Circuit Breaker Behaviour

```
Attempt 1: Generate → Evaluate → REJECT (red line: hallucinated school)
Attempt 2: Correct (re-prompt with feedback) → Evaluate → FIX (headline generic)
Attempt 3: Correct (re-prompt headline) → Evaluate → PASS → Publish (GREEN)

OR

Attempt 1: Generate → Evaluate → REJECT (fabricated budget figure)
Attempt 2: Correct → Evaluate → REJECT (still fabricated)
Attempt 3: Correct → Evaluate → REJECT (still fabricated)
→ Publish with RED flag, log for human review
→ Learner flags: "model consistently fabricates for this meeting — investigate source data"
```

## 12. What This Design Does NOT Cover

- **Upstream pipeline improvements** (steps 1-12) — these are separate work items. The Learner may flag patterns that require upstream fixes, but this design doesn't implement them.
- **User feedback collection** — future enhancement. Currently the rubric is defined by design, not user signals. A future version could incorporate click-through rates, time-on-page, or direct feedback.
- **A/B testing of prompts** — at 3-4 reports/year, sample size is too small for statistical A/B testing. Prompt improvement is deliberate, not experimental.
- **Real-time monitoring dashboard** — the quality ledger is queryable data, but no dashboard is built. A future sprint could add one.

## 13. Implementation Sequence

The implementation should follow this order to build on stable foundations:

1. **Quality rubric document** — write `docs/quality/rubric.md` (the permanent standard)
2. **QualityLog model + migrations** — database support for logging
3. **Evaluator service** — the AI-powered rubric scorer
4. **Evaluator tests** — validate scoring logic with known-good and known-bad reports
5. **School name repairer** — comma removal, fuzzy re-match utilities
6. **Corrector service** — re-prompt, code fix, name repair, illustration regeneration
7. **Corrector tests** — validate each correction pathway
8. **Integration into brief generator** — wrap existing brief generation with evaluate/correct loop
9. **Integration into report generator** — wrap existing report generation with evaluate/correct loop
10. **Report generator tests** — the critical gap identified in the pipeline evaluation
11. **Learner service** — quality ledger logging, pattern detection
12. **Prompt registry + learner patterns files** — initial versions
13. **End-to-end test** — generate a report for a known meeting, verify full loop
14. **WAT workflow / skill** — codify the improved process for agent operation

Steps 1-2 are foundational. Steps 3-7 are the engine. Steps 8-10 are integration. Steps 11-13 are the learning layer. Step 14 locks it all in.
