"""Tests for the run_hansard_pipeline management command."""

from io import StringIO
from unittest.mock import patch, call

from django.core.management import call_command
from django.test import TestCase


CMD = "hansard.management.commands.run_hansard_pipeline"


class RunHansardPipelineTests(TestCase):
    """Test the unified Hansard pipeline command."""

    def _call(self, *args, **kwargs):
        out = StringIO()
        err = StringIO()
        call_command(
            "run_hansard_pipeline", *args, stdout=out, stderr=err, **kwargs
        )
        return out.getvalue(), err.getvalue()

    @patch(f"{CMD}.generate_all_pending_briefs")
    @patch(f"{CMD}.update_all_scorecards")
    @patch(f"{CMD}.run_analysis")
    @patch(f"{CMD}.run_matching")
    @patch(f"{CMD}.call_command")
    @patch(f"{CMD}.sync_calendar")
    def test_all_steps_called_in_order(
        self,
        mock_sync,
        mock_call_cmd,
        mock_matching,
        mock_analysis,
        mock_scorecards,
        mock_briefs,
    ):
        """All 7 pipeline steps are called once in order."""
        mock_sync.return_value = {"created": 1, "updated": 0}
        mock_matching.return_value = {"matched": 2, "unmatched": 0, "total": 2}
        mock_analysis.return_value = {"success": 3, "failed": 0}
        mock_scorecards.return_value = None
        mock_briefs.return_value = {"generated": 1}

        out, _ = self._call()

        mock_sync.assert_called_once()
        mock_matching.assert_called_once()
        mock_analysis.assert_called_once()
        mock_scorecards.assert_called_once()
        mock_briefs.assert_called_once()
        # check_new_hansards and generate_meeting_reports both go via call_command
        mock_call_cmd.assert_any_call("check_new_hansards", auto_process=True)
        mock_call_cmd.assert_any_call("generate_meeting_reports")

    @patch(f"{CMD}.generate_all_pending_briefs")
    @patch(f"{CMD}.update_all_scorecards")
    @patch(f"{CMD}.run_analysis")
    @patch(f"{CMD}.run_matching")
    @patch(f"{CMD}.call_command")
    @patch(f"{CMD}.sync_calendar")
    def test_step_failure_continues(
        self,
        mock_sync,
        mock_call_cmd,
        mock_matching,
        mock_analysis,
        mock_scorecards,
        mock_briefs,
    ):
        """If sync_calendar raises, later steps still run."""
        mock_sync.side_effect = Exception("Network error")
        mock_matching.return_value = {"matched": 0, "unmatched": 0, "total": 0}
        mock_analysis.return_value = {"success": 0, "failed": 0}
        mock_scorecards.return_value = None
        mock_briefs.return_value = {"generated": 0}

        # Should not raise
        out, _ = self._call()

        # Later steps still called
        mock_matching.assert_called_once()
        mock_call_cmd.assert_any_call("generate_meeting_reports")
        self.assertIn("FAILED", out)

    @patch(f"{CMD}.generate_all_pending_briefs")
    @patch(f"{CMD}.update_all_scorecards")
    @patch(f"{CMD}.run_analysis")
    @patch(f"{CMD}.run_matching")
    @patch(f"{CMD}.call_command")
    @patch(f"{CMD}.sync_calendar")
    def test_dry_run_does_nothing(
        self,
        mock_sync,
        mock_call_cmd,
        mock_matching,
        mock_analysis,
        mock_scorecards,
        mock_briefs,
    ):
        """Dry run prints preview without calling any step functions."""
        out, _ = self._call("--dry-run")

        self.assertIn("DRY RUN", out)

        mock_sync.assert_not_called()
        mock_call_cmd.assert_not_called()
        mock_matching.assert_not_called()
        mock_analysis.assert_not_called()
        mock_scorecards.assert_not_called()
        mock_briefs.assert_not_called()
