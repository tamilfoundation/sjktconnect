"""Context builder — assembles domain context for Gemini prompts.

Loads the curated report-context.json and enriches it with runtime
data (MP portfolios, school names) for injection into prompts.
"""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

CONTEXT_JSON_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "report-context.json"


def load_context_json() -> dict:
    """Load the versioned context JSON file.

    Returns the parsed dict. Raises FileNotFoundError if missing.
    """
    with open(CONTEXT_JSON_PATH) as f:
        return json.load(f)


def build_context() -> dict:
    """Build full context dict: static JSON + runtime data.

    Returns a dict with all static context plus:
    - school_names: list of active school short names
    - mp_portfolios: list of dicts with mp name and portfolio
    """
    from parliament.models import MP
    from schools.models import School

    ctx = load_context_json()

    # Runtime: school names for linkification verification
    ctx["school_names"] = list(
        School.objects.filter(is_active=True)
        .values_list("short_name", flat=True)
    )

    # Runtime: MP portfolios for minister attribution verification
    ctx["mp_portfolios"] = list(
        MP.objects.exclude(portfolio="")
        .values("name", "portfolio", "constituency__name")
    )

    return ctx


def format_context_for_prompt(ctx: dict) -> str:
    """Format context dict as a text block for prompt injection.

    Returns a string suitable for appending to a Gemini prompt.
    """
    sections = []

    # Cabinet reference
    cabinet = ctx.get("cabinet", {})
    if cabinet:
        lines = ["CABINET REFERENCE (use to verify minister names):"]
        for key, info in cabinet.items():
            lines.append(f"- {info['portfolio']}: {info['minister']}")
        sections.append("\n".join(lines))

    # Glossary
    glossary = ctx.get("glossary", {})
    if glossary:
        lines = ["GLOSSARY (expand these acronyms on first use):"]
        for abbr, defn in glossary.items():
            lines.append(f"- {abbr}: {defn}")
        sections.append("\n".join(lines))

    # Taxonomy definitions
    taxonomy = ctx.get("taxonomy", {})
    if taxonomy:
        lines = ["TAXONOMY DEFINITIONS:"]
        for category, values in taxonomy.items():
            lines.append(f"\n{category.title()}:")
            for label, defn in values.items():
                lines.append(f"  - {label}: {defn}")
        sections.append("\n".join(lines))

    # National baseline
    baseline = ctx.get("national_baseline", {})
    if baseline:
        lines = [
            "NATIONAL BASELINE:",
            f"- {baseline.get('total_sjkt', 528)} SJK(T) schools",
            f"- {baseline.get('total_students', 69900)} students",
            f"- {baseline.get('total_teachers', 5460)} teachers",
            f"- {baseline.get('under_enrolled_schools', 154)} under-enrolled (< {baseline.get('under_enrolled_threshold', 150)} students)",
        ]
        sections.append("\n".join(lines))

    # RPM reference
    rpm = ctx.get("national_education_plan", {})
    if rpm:
        lines = [f"NATIONAL EDUCATION PLAN: {rpm.get('name', 'RPM 2026-2035')}"]
        lines.append(f"Status: {rpm.get('status', '')}")
        lines.append(f"Relevance: {rpm.get('relevance', '')}")
        for commitment in rpm.get("key_commitments", []):
            lines.append(f"  - {commitment}")
        sections.append("\n".join(lines))

    # MP portfolios (runtime)
    portfolios = ctx.get("mp_portfolios", [])
    if portfolios:
        lines = ["MP PORTFOLIOS (for attribution verification):"]
        for mp in portfolios:
            lines.append(f"- {mp['name']}: {mp['portfolio']} ({mp.get('constituency__name', '')})")
        sections.append("\n".join(lines))

    return "\n\n".join(sections)
