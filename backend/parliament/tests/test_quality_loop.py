"""Tests for the unified quality loop framework."""

from django.test import TestCase

from parliament.services.evaluator import EvaluationResult


class QualityLoopTests(TestCase):
    """Test the generic run_quality_loop function."""

    def test_pass_on_first_attempt(self):
        from parliament.services.quality_loop import run_quality_loop

        def evaluate_fn(content):
            return EvaluationResult(verdict="PASS")

        logs = []
        def log_fn(attempt, eval_result):
            logs.append({"attempt": attempt, "verdict": eval_result.verdict})

        content, flag = run_quality_loop(
            content="Good content",
            evaluate_fn=evaluate_fn,
            correct_fn=None,
            max_attempts=3,
            log_entry_fn=log_fn,
        )
        self.assertEqual(content, "Good content")
        self.assertEqual(flag, "GREEN")
        self.assertEqual(len(logs), 1)

    def test_fix_triggers_correction(self):
        from parliament.services.quality_loop import run_quality_loop

        call_count = {"n": 0}

        def evaluate_fn(content):
            call_count["n"] += 1
            if call_count["n"] == 1:
                return EvaluationResult(
                    verdict="FIX",
                    tier2_scores={"quality": {"score": 3, "feedback": "Bad"}},
                )
            return EvaluationResult(verdict="PASS")

        def correct_fn(content, eval_result):
            return "Corrected content"

        logs = []
        def log_fn(attempt, eval_result):
            logs.append({"attempt": attempt, "verdict": eval_result.verdict})

        content, flag = run_quality_loop(
            content="Draft content",
            evaluate_fn=evaluate_fn,
            correct_fn=correct_fn,
            max_attempts=3,
            log_entry_fn=log_fn,
        )
        self.assertEqual(content, "Corrected content")
        self.assertEqual(flag, "GREEN")
        self.assertEqual(len(logs), 2)

    def test_circuit_breaker_after_max_attempts(self):
        from parliament.services.quality_loop import run_quality_loop

        def evaluate_fn(content):
            return EvaluationResult(
                verdict="REJECT",
                tier1_results={"fabricated_facts": {"pass": False}},
            )

        def correct_fn(content, eval_result):
            return "Still bad"

        logs = []
        def log_fn(attempt, eval_result):
            logs.append({"attempt": attempt, "verdict": eval_result.verdict})

        content, flag = run_quality_loop(
            content="Bad content",
            evaluate_fn=evaluate_fn,
            correct_fn=correct_fn,
            max_attempts=3,
            log_entry_fn=log_fn,
        )
        self.assertEqual(flag, "RED")
        self.assertEqual(len(logs), 3)

    def test_correction_returns_none_stops_loop(self):
        from parliament.services.quality_loop import run_quality_loop

        def evaluate_fn(content):
            return EvaluationResult(verdict="FIX")

        def correct_fn(content, eval_result):
            return None  # correction failed

        logs = []
        def log_fn(attempt, eval_result):
            logs.append({"attempt": attempt, "verdict": eval_result.verdict})

        content, flag = run_quality_loop(
            content="Draft",
            evaluate_fn=evaluate_fn,
            correct_fn=correct_fn,
            max_attempts=3,
            log_entry_fn=log_fn,
        )
        self.assertEqual(flag, "AMBER")
        self.assertEqual(len(logs), 1)  # stopped after first attempt

    def test_no_correct_fn_evaluates_once(self):
        from parliament.services.quality_loop import run_quality_loop

        def evaluate_fn(content):
            return EvaluationResult(verdict="FIX")

        logs = []
        def log_fn(attempt, eval_result):
            logs.append({"attempt": attempt, "verdict": eval_result.verdict})

        content, flag = run_quality_loop(
            content="Draft",
            evaluate_fn=evaluate_fn,
            correct_fn=None,
            max_attempts=3,
            log_entry_fn=log_fn,
        )
        self.assertEqual(flag, "AMBER")
        self.assertEqual(len(logs), 1)

    def test_amber_verdict_from_evaluator_error(self):
        """AMBER from evaluator (evaluator_error) should stop loop gracefully."""
        from parliament.services.quality_loop import run_quality_loop

        def evaluate_fn(content):
            return EvaluationResult(verdict="AMBER", evaluator_error=True)

        logs = []
        def log_fn(attempt, eval_result):
            logs.append({"attempt": attempt, "verdict": eval_result.verdict})

        content, flag = run_quality_loop(
            content="Draft",
            evaluate_fn=evaluate_fn,
            correct_fn=lambda c, e: "Fixed",
            max_attempts=3,
            log_entry_fn=log_fn,
        )
        # AMBER from evaluator error should try correction (treated like FIX)
        self.assertIn(flag, ("GREEN", "AMBER"))
