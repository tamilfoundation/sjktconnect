"""Learner service — analyses quality logs and detects recurring patterns.

Runs after every report cycle. Produces pattern flags for upstream improvement.
"""

import logging
from collections import defaultdict

from parliament.models import QualityLog

logger = logging.getLogger(__name__)

RECURRING_THRESHOLD = 3
LOW_SCORE_THRESHOLD = 6


def detect_patterns() -> list[dict]:
    """Analyse quality logs for recurring failure patterns.

    Returns list of pattern flags, each with:
    - criterion: the failing criterion name
    - count: number of reports where it failed
    - avg_score: average score across those reports
    - recommendation: suggested fix
    """
    report_logs = (
        QualityLog.objects.filter(content_type="report")
        .order_by("meeting_id", "-attempt_number")
    )

    # Deduplicate: keep only the final attempt per meeting
    seen_meetings = set()
    final_logs = []
    for log in report_logs:
        if log.meeting_id and log.meeting_id not in seen_meetings:
            seen_meetings.add(log.meeting_id)
            final_logs.append(log)

    # Count low scores per criterion
    criterion_scores = defaultdict(list)
    for log in final_logs:
        for criterion, data in log.tier2_scores.items():
            score = data.get("score")
            if score is not None:
                criterion_scores[criterion].append(score)

    flags = []
    for criterion, scores in criterion_scores.items():
        low_scores = [s for s in scores if s < LOW_SCORE_THRESHOLD]
        if len(low_scores) >= RECURRING_THRESHOLD:
            avg = sum(low_scores) / len(low_scores)
            flags.append({
                "criterion": criterion,
                "count": len(low_scores),
                "avg_score": round(avg, 1),
                "recommendation": f"Criterion '{criterion}' scored below "
                    f"{LOW_SCORE_THRESHOLD} in {len(low_scores)} reports "
                    f"(avg {avg:.1f}). Review prompt or add targeted instructions.",
            })

    if flags:
        logger.warning(
            "Learner detected %d recurring pattern(s): %s",
            len(flags),
            ", ".join(f["criterion"] for f in flags),
        )

    return flags


def log_quality_summary(meeting) -> dict:
    """Return a quality summary for a meeting's report generation cycle."""
    logs = QualityLog.objects.filter(
        content_type="report", meeting=meeting,
    ).order_by("attempt_number")

    if not logs.exists():
        return {"total_attempts": 0, "final_verdict": "N/A"}

    final_log = logs.last()
    return {
        "total_attempts": logs.count(),
        "final_verdict": final_log.verdict,
        "final_flag": final_log.quality_flag,
        "attempts": [
            {
                "attempt": log.attempt_number,
                "verdict": log.verdict,
                "corrections": log.corrections_applied,
            }
            for log in logs
        ],
    }
