from django.test import TestCase
from django.core.management import call_command
from io import StringIO


class TestCheckPipelineDrift(TestCase):
    def test_command_runs_without_error(self):
        out = StringIO()
        call_command("check_pipeline_drift", stdout=out)
        output = out.getvalue()
        assert "Pipeline Version:" in output

    def test_command_shows_all_components(self):
        out = StringIO()
        call_command("check_pipeline_drift", stdout=out)
        output = out.getvalue()
        assert "mention_analysis" in output
        assert "report_generation" in output
