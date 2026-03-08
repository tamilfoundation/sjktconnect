"""Evaluator service — scores generated output against the quality rubric.

Uses a separate Gemini API call to evaluate sitting briefs and meeting reports.
Returns structured EvaluationResult with verdict (PASS/FIX/REJECT/AMBER), tier
scores, and repair suggestions.

Fail-safe: if API key is missing, returns PASS (fail-open for dev).
If API call fails, returns AMBER (needs human review).
"""

import json
import logging
import os
from dataclasses import dataclass, field

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

PROMPT_VERSION = "v1"
MODEL = "gemini-2.5-flash"


@dataclass
class EvaluationResult:
    verdict: str  # PASS, FIX, REJECT, AMBER
    tier1_results: dict = field(default_factory=dict)
    tier2_scores: dict = field(default_factory=dict)
    tier3_flags: dict = field(default_factory=dict)
    unlinked_schools: list = field(default_factory=list)
    repair_suggestions: list = field(default_factory=list)
    evaluator_error: bool = False


def _compute_verdict(tier1: dict, tier2: dict) -> str:
    """Compute verdict from tier1 red lines and tier2 quality scores."""
    # Tier 1: any failure -> REJECT
    for check in tier1.values():
        if not check.get("pass", True):
            return "REJECT"

    # Tier 2: avg < 6 or any single < 5 -> FIX
    scores = [v["score"] for v in tier2.values() if "score" in v]
    if scores:
        if any(s < 5 for s in scores):
            return "FIX"
        if sum(scores) / len(scores) < 6:
            return "FIX"

    return "PASS"


def _pass_result() -> EvaluationResult:
    """Return a default PASS result (fail-open)."""
    return EvaluationResult(verdict="PASS")


def _amber_result() -> EvaluationResult:
    """Return an AMBER result indicating evaluator failure."""
    return EvaluationResult(verdict="AMBER", evaluator_error=True)


EVALUATOR_PROMPT = """\
You are a quality evaluator for SJK(T) Connect parliamentary reports about
Tamil schools in Malaysia.

Evaluate the following {content_type} against the rubric below. Cross-reference
all claims against the source material provided.

RUBRIC — Tier 1 (Red Lines):
- fabricated_facts: Are there claims not traceable to the source material?
- wrong_attribution: Is any statement attributed to the wrong MP?
- hallucinated_schools: Are there school names not in the school database?
- empty_output: Are any required sections blank or placeholder?
- internal_contradiction: Do sections contradict each other?

RUBRIC — Tier 2 (Quality Gates, score 1-10):
{tier2_criteria}

RUBRIC — Tier 3 (Drift Detection):
- illustration_similarity: Does the illustration look like previous ones?
- headline_pattern: Is the headline formulaic?
- advice_formulaic: Does "What to Watch" repeat previous framing?
- tone_drift: Is editorial commentary creeping in?

SCHOOL DATABASE (valid names):
{school_names}

MP DATABASE (valid names):
{mp_names}

{previous_context}

SOURCE MATERIAL:
{source_material}

OUTPUT TO EVALUATE:
{output_text}

Return a JSON object with this exact structure:
{{
  "verdict": "PASS or FIX or REJECT",
  "tier1_red_lines": {{
    "fabricated_facts": {{"pass": true/false, "details": "...or null"}},
    "wrong_attribution": {{"pass": true/false, "details": "...or null"}},
    "hallucinated_schools": {{"pass": true/false, "details": "...or null"}},
    "empty_output": {{"pass": true/false, "details": "...or null"}},
    "internal_contradiction": {{"pass": true/false, "details": "...or null"}}
  }},
  "tier2_quality": {{
    "<criterion>": {{"score": 1-10, "feedback": "...or null"}}
  }},
  "tier3_drift": {{
    "illustration_similarity": "OK/MILD/HIGH",
    "headline_pattern": "OK/MILD/HIGH",
    "advice_formulaic": "OK/MILD/HIGH",
    "tone_drift": "OK/MILD/HIGH"
  }},
  "unlinked_schools": ["school names found in text but not linked"],
  "repair_suggestions": ["suggested fixes"]
}}
"""

REPORT_TIER2_CRITERIA = """\
- structure_complete: Are all applicable sections present? (1-10)
- headline_specificity: Does the headline tell what happened? (1-10)
- key_findings_specificity: Do findings cite figures/dates/names? (1-10)
- mp_scorecard_traceability: Are scorecard entries traceable to briefs? (1-10)
- executive_response_tracking: Is time-lag noted where applicable? (1-10)
- executive_response_attribution: Is every executive response attributed to a named minister with correct portfolio? (1-10)
- actionability: Can a school board act on "What to Watch"? (1-10)
- word_count: Is it within guidance range? (1-10)
- school_linkification: Are school names linked? (1-10)
- jargon_free: No unexplained acronyms? (1-10)"""

BRIEF_TIER2_CRITERIA = """\
- school_linkification: Are school names linked to school pages? (1-10)
- constituency_linkification: Are constituency names linked? (1-10)
- mp_attribution: Are MP names verified or labelled "Unidentified"? (1-10)
- factual_traceability: Are claims traceable to the ai_summary? (1-10)
- accessibility: No unexplained acronyms? (1-10)
- no_fabrication: No info beyond what the source contains? (1-10)"""


def evaluate_report(
    report_html: str,
    source_briefs: str,
    school_names: list[str],
    mp_names: list[str],
    previous_report: str = "",
) -> EvaluationResult:
    """Evaluate a meeting report against the quality rubric."""
    api_key = os.environ.get("GEMINI_API_KEY", "").split("#")[0].strip()
    if not api_key:
        logger.warning("GEMINI_API_KEY not set — evaluator returning PASS (fail-open)")
        return _pass_result()

    previous_context = ""
    if previous_report:
        prev_trimmed = previous_report[:3000]
        previous_context = f"PREVIOUS REPORT (for drift detection):\n{prev_trimmed}"

    prompt = EVALUATOR_PROMPT.format(
        content_type="meeting report",
        tier2_criteria=REPORT_TIER2_CRITERIA,
        school_names="\n".join(school_names[:100]),
        mp_names="\n".join(mp_names[:50]),
        previous_context=previous_context,
        source_material=source_briefs[:15000],
        output_text=report_html[:15000],
    )

    return _call_evaluator(api_key, prompt)


def evaluate_brief(
    brief_html: str,
    source_summaries: str,
    school_names: list[str],
    mp_names: list[str],
) -> EvaluationResult:
    """Evaluate a sitting brief against the quality rubric."""
    api_key = os.environ.get("GEMINI_API_KEY", "").split("#")[0].strip()
    if not api_key:
        logger.warning("GEMINI_API_KEY not set — evaluator returning PASS (fail-open)")
        return _pass_result()

    prompt = EVALUATOR_PROMPT.format(
        content_type="sitting brief",
        tier2_criteria=BRIEF_TIER2_CRITERIA,
        school_names="\n".join(school_names[:100]),
        mp_names="\n".join(mp_names[:50]),
        previous_context="",
        source_material=source_summaries[:10000],
        output_text=brief_html[:10000],
    )

    return _call_evaluator(api_key, prompt)


def _call_evaluator(api_key: str, prompt: str) -> EvaluationResult:
    """Make the Gemini API call and parse the response."""
    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.1,
                max_output_tokens=4096,
                response_mime_type="application/json",
            ),
        )
        data = json.loads(response.text)
    except Exception:
        logger.exception("Evaluator API call failed — returning AMBER (fail-safe)")
        return _amber_result()

    tier1 = data.get("tier1_red_lines", {})
    tier2 = data.get("tier2_quality", {})
    tier3 = data.get("tier3_drift", {})

    # Recompute verdict from data (don't trust the AI's verdict)
    verdict = _compute_verdict(tier1, tier2)

    return EvaluationResult(
        verdict=verdict,
        tier1_results=tier1,
        tier2_scores=tier2,
        tier3_flags=tier3,
        unlinked_schools=data.get("unlinked_schools", []),
        repair_suggestions=data.get("repair_suggestions", []),
    )


@dataclass
class MentionEvaluation:
    """Lightweight evaluation result for a single mention (no API call)."""
    warnings: list = field(default_factory=list)
    confidence: float = 1.0


_FINANCIAL_TERMS = {
    "rm", "ringgit", "juta", "million", "billion", "bilion",
    "peruntukan", "allocation", "budget", "bajet", "dana", "fund",
}


def evaluate_mention(mention) -> MentionEvaluation:
    """Deterministic quality check on a single analysed mention.

    No API call — uses heuristic rules only.
    Returns MentionEvaluation with warnings and confidence score.
    """
    warnings = []
    confidence = 1.0

    excerpt = f"{mention.context_before} {mention.verbatim_quote}".lower()

    # Check 1: Speaker presence
    if mention.mp_name:
        mp_lower = mention.mp_name.lower()
        found = mp_lower in excerpt
        if not found:
            # Try surname fragments
            fragments = [
                w for w in mention.mp_name.split()
                if len(w) > 2 and w.lower() not in {"a/l", "a/p", "bin", "binti", "b.", "bt."}
            ]
            found = any(f.lower() in excerpt for f in fragments)

        if not found:
            warnings.append(f"Speaker '{mention.mp_name}' not found in excerpt")
            confidence -= 0.3

    # Check 2: Significance sanity
    excerpt_len = len(mention.verbatim_quote or "")
    if excerpt_len < 100 and (mention.significance or 0) > 3:
        warnings.append(
            f"High significance ({mention.significance}) for short excerpt "
            f"({excerpt_len} chars)"
        )
        confidence -= 0.2

    # Check 3: BUDGET type consistency
    if mention.mention_type == "BUDGET":
        has_financial = any(term in excerpt for term in _FINANCIAL_TERMS)
        if not has_financial:
            warnings.append(
                "Mention type is BUDGET but no financial terms found in excerpt"
            )
            confidence -= 0.15

    confidence = max(0.0, min(1.0, confidence))
    return MentionEvaluation(warnings=warnings, confidence=round(confidence, 2))
