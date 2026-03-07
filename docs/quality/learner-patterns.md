# Learner Pattern Flags

Recurring issues detected by the quality engine. When a flag is resolved
(code change made), move it to the Resolved section with the commit reference.

## Active Flags

### FLAG-001: Minister name hallucination (CRITICAL)
- **Detected**: 2026-03-07, 3rd Meeting 2025 report
- **Issue**: Gemini generated "Datuk Seri Dr. Zaliha binti Mustafa" as Minister of Education. The actual MOE is Dato' Sri Fadhlina binti Sidek. Dr. Zaliha is Minister of Health.
- **Root cause**: MP model has no `portfolio` field. Neither the generator nor the evaluator has a cabinet reference to verify minister names against. Gemini hallucinated from stale training data.
- **Fix required**:
  1. Add `portfolio` field to MP model (e.g. "Minister of Education")
  2. Scrape portfolio from parlimen.gov.my (increase lookback to ~50 pages for minister profiles)
  3. Pass cabinet reference to report generator prompt
  4. Pass cabinet reference to evaluator for Tier 1 `wrong_attribution` verification
- **Severity**: Tier 1 red line — wrong attribution. Destroys credibility.

### FLAG-002: "Unknown MP" in Executive Responses
- **Detected**: 2026-03-07, 3rd Meeting 2025 report
- **Issue**: First Executive Response row lists "Unknown MP" as the minister who committed to rebuilding SJK(T) Ladang Jeram.
- **Root cause**: Report generator prompt doesn't enforce that every executive response must identify the responding minister. Evaluator rubric's `executive_response_tracking` criterion is about time-lag, not attribution.
- **Fix required**:
  1. Add `executive_response_attribution` to report Tier 2 criteria in rubric and evaluator
  2. Update report generator prompt to require minister identification for every response
  3. With FLAG-001 fix, the cabinet reference would help the generator identify ministers

### FLAG-003: Unlinked school names due to missing aliases
- **Detected**: 2026-03-07, 3rd Meeting 2025 report
- **Issue**: "SJK(T) Serendah" not hyperlinked (official name likely "SJK(T) Ladang Serendah"). "SJK(T) Semantan" may link incorrectly (official: "SJK(T) Ladang Semantan").
- **Root cause**: seed_aliases does not generate "without Ladang" variants. 294 schools affected. MPs commonly drop "Ladang" when referencing schools.
- **Fix required**: Add "without Ladang" alias variant to seed_aliases command.
- **Already tracked**: Listed in CLAUDE.md Next Sprint section.

### FLAG-004: Report structure not serving multiple audiences
- **Detected**: 2026-03-07, external review of 3rd Meeting 2025 report
- **Issue**: Report caught between audiences — too thin for policy wonk, too jargon-heavy for parent, not actionable enough for school board. Key gaps:
  - No plain-language "30-second read" paragraph at top
  - Acronyms not expanded (PPKI, JPN, MBPK, SJK(C))
  - "What to Watch" is paragraphs, not an actionable checklist
  - No Hansard quotes (makes report unusable for journalists)
  - No historical context (is RM2 billion more/less than last year?)
  - MP Scorecard Impact categories undefined (no legend for "General Rhetoric" vs "Policy Shift")
  - Executive Response verdicts undefined ("Commitment Made" vs "Resolved" unexplained)
  - Numbers lack context (new money vs reallocation?)
- **Fix required**: Restructure report prompt to produce layered output:
  1. 30-second plain-language summary (no acronyms)
  2. What Parliament did (decisions with context)
  3. Who drove it (MP Scorecard with legend)
  4. What the government committed to (with credibility assessment)
  5. What schools should do now (actionable checklist)
  6. What we're watching (follow-up items)
- **Reference models**: TheyWorkForYou (UK), Politico Playbook, Malaysiakini explainer boxes

### FLAG-005: Impact classification imbalance
- **Detected**: 2026-03-07, 3rd Meeting 2025 report
- **Issue**: 10 of 15 MPs classified as "General Rhetoric" impact. Suggests the classifier defaults to it when unsure.
- **Root cause**: Report generator prompt's impact taxonomy may not have enough guidance to distinguish between General Rhetoric and more specific categories.
- **Fix required**: Review impact taxonomy definitions in report generator prompt. Consider whether "General Rhetoric" is too broad a catch-all.

## Resolved Flags

_No resolved flags yet._
