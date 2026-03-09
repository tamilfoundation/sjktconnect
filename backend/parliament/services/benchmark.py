"""Quality benchmark service — runs evaluators across all content and builds
a structured report for comparison across pipeline versions.

Functions:
    benchmark_mentions(use_gemini=False) — deterministic mention evaluation
    benchmark_briefs() — evaluate all briefs via Gemini evaluator
    benchmark_reports() — evaluate all reports via Gemini evaluator
    build_benchmark_report(label, mention_results, brief_results, report_results)
"""

import logging
from collections import Counter
from datetime import datetime, timezone

from hansard.models import HansardMention
from parliament.models import MP, ParliamentaryMeeting, SittingBrief
from parliament.services.evaluator import (
    EvaluationResult,
    PROMPT_VERSION,
    evaluate_brief,
    evaluate_mention,
    evaluate_report,
)
from schools.models import School

logger = logging.getLogger(__name__)


def _get_school_and_mp_names() -> tuple[list[str], list[str]]:
    """Return lists of school and MP names for the evaluator."""
    school_names = list(School.objects.values_list("short_name", flat=True))
    mp_names = list(MP.objects.values_list("name", flat=True))
    return school_names, mp_names


def _result_to_dict(result: EvaluationResult) -> dict:
    """Convert an EvaluationResult to a JSON-serialisable dict."""
    return {
        "verdict": result.verdict,
        "tier1_results": result.tier1_results,
        "tier2_scores": result.tier2_scores,
        "tier3_flags": result.tier3_flags,
        "unlinked_schools": result.unlinked_schools,
        "repair_suggestions": result.repair_suggestions,
        "evaluator_error": result.evaluator_error,
    }


def benchmark_mentions(use_gemini: bool = False) -> list[dict]:
    """Evaluate all analysed mentions using deterministic checks.

    Args:
        use_gemini: If True, adds a placeholder gemini field (not yet implemented).

    Returns:
        List of dicts with mention metadata and evaluation results.
    """
    mentions = (
        HansardMention.objects
        .exclude(ai_summary="")
        .select_related("sitting")
        .order_by("sitting__sitting_date", "id")
    )

    results = []
    for mention in mentions:
        eval_result = evaluate_mention(mention)
        item = {
            "mention_id": mention.id,
            "sitting_date": str(mention.sitting.sitting_date),
            "mp_name": mention.mp_name,
            "mention_type": mention.mention_type,
            "significance": mention.significance,
            "deterministic": {
                "speaker_verified": mention.speaker_verified,
                "confidence": eval_result.confidence,
                "warnings": eval_result.warnings,
            },
        }
        if use_gemini:
            item["gemini"] = {"note": "not yet implemented"}
        results.append(item)

    return results


def benchmark_briefs() -> list[dict]:
    """Evaluate all briefs with non-empty summary_html.

    Returns:
        List of dicts with brief metadata and evaluation results.
    """
    briefs = (
        SittingBrief.objects
        .exclude(summary_html="")
        .select_related("sitting")
        .order_by("sitting__sitting_date")
    )

    school_names, mp_names = _get_school_and_mp_names()
    results = []

    for brief in briefs:
        # Gather source summaries from the brief's sitting's mentions
        source_summaries = "\n\n".join(
            brief.sitting.mentions
            .exclude(ai_summary="")
            .values_list("ai_summary", flat=True)
        )

        eval_result = evaluate_brief(
            brief_html=brief.summary_html,
            source_summaries=source_summaries,
            school_names=school_names,
            mp_names=mp_names,
        )

        word_count = len(brief.summary_html.split())
        results.append({
            "brief_id": brief.id,
            "sitting_date": str(brief.sitting.sitting_date),
            "title": brief.title,
            "quality_flag": brief.quality_flag,
            "word_count": word_count,
            "evaluation": _result_to_dict(eval_result),
        })

    return results


def benchmark_reports() -> list[dict]:
    """Evaluate all meeting reports with non-empty report_html.

    Returns:
        List of dicts with meeting metadata and evaluation results.
    """
    meetings = (
        ParliamentaryMeeting.objects
        .exclude(report_html="")
        .order_by("start_date")
    )

    school_names, mp_names = _get_school_and_mp_names()
    results = []

    for meeting in meetings:
        # Gather source briefs from the meeting's sittings
        source_briefs = "\n\n".join(
            SittingBrief.objects
            .filter(sitting__meeting=meeting)
            .exclude(summary_html="")
            .values_list("summary_html", flat=True)
        )

        eval_result = evaluate_report(
            report_html=meeting.report_html,
            source_briefs=source_briefs,
            school_names=school_names,
            mp_names=mp_names,
        )

        word_count = len(meeting.report_html.split())
        results.append({
            "meeting_id": meeting.id,
            "short_name": meeting.short_name,
            "quality_flag": meeting.quality_flag,
            "word_count": word_count,
            "evaluation": _result_to_dict(eval_result),
        })

    return results


def build_benchmark_report(
    label: str,
    mention_results: list[dict],
    brief_results: list[dict],
    report_results: list[dict],
) -> dict:
    """Build a full benchmark report with meta, summary, and detail sections.

    Args:
        label: Human-readable label for this benchmark run.
        mention_results: Output from benchmark_mentions().
        brief_results: Output from benchmark_briefs().
        report_results: Output from benchmark_reports().

    Returns:
        JSON-serialisable dict with meta, summary, and detail.
    """
    # --- Mentions summary ---
    mention_confidences = [
        m["deterministic"]["confidence"] for m in mention_results
    ]
    mentions_with_warnings = sum(
        1 for m in mention_results if m["deterministic"]["warnings"]
    )
    mention_summary = {
        "total": len(mention_results),
        "avg_confidence": (
            sum(mention_confidences) / len(mention_confidences)
            if mention_confidences else 0.0
        ),
        "with_warnings": mentions_with_warnings,
    }

    # --- Briefs summary ---
    brief_verdicts = Counter(
        b["evaluation"]["verdict"] for b in brief_results
        if "evaluation" in b and "verdict" in b["evaluation"]
    )
    brief_tier2_all: dict[str, list[float]] = {}
    for b in brief_results:
        tier2 = b.get("evaluation", {}).get("tier2_scores", {})
        for criterion, data in tier2.items():
            if isinstance(data, dict) and "score" in data:
                brief_tier2_all.setdefault(criterion, []).append(data["score"])
    brief_avg_tier2 = {
        k: round(sum(v) / len(v), 2) for k, v in brief_tier2_all.items()
    }
    brief_summary = {
        "total": len(brief_results),
        "verdicts": dict(brief_verdicts),
        "avg_tier2": brief_avg_tier2,
    }

    # --- Reports summary ---
    report_verdicts = Counter(
        r["evaluation"]["verdict"] for r in report_results
        if "evaluation" in r and "verdict" in r["evaluation"]
    )
    report_tier2_all: dict[str, list[float]] = {}
    for r in report_results:
        tier2 = r.get("evaluation", {}).get("tier2_scores", {})
        for criterion, data in tier2.items():
            if isinstance(data, dict) and "score" in data:
                report_tier2_all.setdefault(criterion, []).append(data["score"])
    report_avg_tier2 = {
        k: round(sum(v) / len(v), 2) for k, v in report_tier2_all.items()
    }
    report_summary = {
        "total": len(report_results),
        "verdicts": dict(report_verdicts),
        "avg_tier2": report_avg_tier2,
    }

    return {
        "meta": {
            "label": label,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "evaluator_version": PROMPT_VERSION,
        },
        "summary": {
            "mentions": mention_summary,
            "briefs": brief_summary,
            "reports": report_summary,
        },
        "detail": {
            "mentions": mention_results,
            "briefs": brief_results,
            "reports": report_results,
        },
    }
