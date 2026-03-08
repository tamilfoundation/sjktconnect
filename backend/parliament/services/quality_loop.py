"""Unified quality loop — evaluate/correct/re-evaluate for any content type.

Replaces inline loops in generate_meeting_reports.py and brief_generator.py
with a single reusable function.
"""

import logging

from parliament.services.evaluator import EvaluationResult

logger = logging.getLogger(__name__)


def run_quality_loop(
    content: str,
    evaluate_fn,
    correct_fn=None,
    max_attempts: int = 3,
    log_entry_fn=None,
) -> tuple[str, str]:
    """Run an evaluate/correct loop on content.

    Args:
        content: The current text (HTML or markdown).
        evaluate_fn: callable(content) -> EvaluationResult
        correct_fn: callable(content, eval_result) -> str | None
            If None, only evaluates once (no correction possible).
        max_attempts: Maximum evaluation attempts before circuit breaker.
        log_entry_fn: callable(attempt_number, eval_result) -> None
            Called after each evaluation for logging.

    Returns:
        (final_content, quality_flag) where quality_flag is
        "GREEN", "AMBER", or "RED".
    """
    attempt = 1
    current = content
    quality_flag = "AMBER"  # default if we somehow exit without setting

    while attempt <= max_attempts:
        eval_result = evaluate_fn(current)

        # Map verdict to quality flag
        if eval_result.verdict == "PASS":
            quality_flag = "GREEN"
        elif eval_result.verdict == "REJECT":
            quality_flag = "RED"
        else:
            quality_flag = "AMBER"

        # Log this attempt
        if log_entry_fn:
            log_entry_fn(attempt, eval_result)

        # PASS — done
        if eval_result.verdict == "PASS":
            return current, "GREEN"

        # No corrector — can't improve, return as-is
        if correct_fn is None:
            return current, quality_flag

        # Circuit breaker
        if attempt >= max_attempts:
            logger.warning(
                "Quality loop circuit breaker after %d attempts — %s",
                attempt, quality_flag,
            )
            return current, quality_flag

        # Attempt correction
        corrected = correct_fn(current, eval_result)
        if corrected is None:
            # Correction failed — stop loop
            return current, quality_flag

        current = corrected
        attempt += 1

    return current, quality_flag
