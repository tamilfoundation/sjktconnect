# SJK(T) Connect — Quality Rubric

This rubric defines what "good" means for sitting briefs, meeting reports,
and illustrations. It is model-agnostic and prompt-agnostic. Changes require
justification linked to user feedback or Learner pattern flags.

---

## Tier 1: Red Lines (Block Publication)

Any of these = verdict REJECT:

1. **Fabricated facts** — claims not traceable to source mentions/briefs
2. **Wrong attribution** — statement attributed to wrong MP or constituency
3. **Hallucinated schools** — school name not in the 528-school database
4. **Empty output** — any required section is blank or placeholder
5. **Internal contradiction** — sections contradict each other

## Tier 2: Quality Gates (Fix If Below Threshold)

Each scored 1-10. Average < 6 or any single < 5 = verdict FIX.

### For Sitting Briefs

1. **School linkification** — every school name is linked to its school page
2. **Constituency linkification** — every constituency is linked
3. **MP attribution** — MP names verified against database or labelled "Unidentified"
4. **Factual traceability** — claims traceable to the mention's ai_summary
5. **Accessibility** — no unexplained acronyms (PPKI, KPM, JKR)
6. **No fabrication** — no information beyond what the source mention contains

### For Meeting Reports

1. **Headline specificity** — tells what happened, not that something happened
2. **Key Findings specificity** — contains amounts, dates, names, commitments
3. **MP Scorecard traceability** — entries traceable to sitting briefs
4. **Executive Response tracking** — time-lag noted where applicable
5. **Actionability** — "What to Watch" gives advice a school board can act on
6. **Structure completeness** — all applicable sections present
7. **Word count** — within guidance range for sitting count
8. **School linkification** — school names linked to school pages
9. **Constituency linkification** — constituency names linked
10. **Jargon-free** — no unexplained acronyms

### For Illustrations

1. **Content relevance** — reflects this report's specific findings
2. **Emotional register** — matches report's dominant theme
3. **Visual distinctness** — different from previous report's illustration
4. **Representation** — Tamil Indian representation present and respectful
5. **Text compliance** — no text other than "SJK(T)" in the image

## Tier 3: Drift Detection (Log Only)

Never affects verdict. Logged for Learner analysis:

- **Illustration similarity** — same composition as recent reports
- **Headline pattern** — formulaic headline structure repeated
- **Advice formulaic** — "What to Watch" uses same framing repeatedly
- **Tone drift** — editorial commentary creeping in

---

## Verdict Logic

```
IF any Tier 1 check fails       -> REJECT
ELSE IF average Tier 2 < 6      -> FIX
ELSE IF any single Tier 2 < 5   -> FIX
ELSE                             -> PASS
```

## Sparse Meeting Handling

When a meeting has fewer than 3 matched school mentions, the evaluator uses
an adapted rubric — it does not penalise missing sections (MP Scorecard,
Executive Responses, Policy Signals) that were intentionally omitted due to
data sparsity.

## Circuit Breaker

- Maximum 3 total attempts (1 original + 2 corrections)
- Attempt 3 with red line violations: publish with RED flag
- Attempt 3 with only Tier 2 issues: publish with AMBER flag + explanatory note
- Any attempt passes: publish with GREEN flag
