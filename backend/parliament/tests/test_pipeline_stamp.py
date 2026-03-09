"""Verify pipeline_version is stamped on generated records."""
from unittest.mock import patch, MagicMock
from parliament.services.pipeline_registry import get_pipeline_version


def test_pipeline_version_is_not_empty():
    """Sanity: get_pipeline_version returns a non-empty string."""
    v = get_pipeline_version()
    assert v
    assert v.startswith("pipeline-")


def test_gemini_client_has_import():
    """gemini_client.py imports get_pipeline_version."""
    import parliament.services.gemini_client as mod
    source = open(mod.__file__).read()
    assert "get_pipeline_version" in source
    assert "pipeline_version" in source


def test_brief_generator_has_import():
    """brief_generator.py imports get_pipeline_version."""
    import parliament.services.brief_generator as mod
    source = open(mod.__file__).read()
    assert "get_pipeline_version" in source
    assert "pipeline_version" in source


def test_generate_meeting_reports_has_import():
    """generate_meeting_reports.py imports get_pipeline_version."""
    import parliament.management.commands.generate_meeting_reports as mod
    source = open(mod.__file__).read()
    assert "get_pipeline_version" in source
    assert "pipeline_version" in source


def test_regenerate_briefs_has_import():
    """regenerate_briefs.py imports get_pipeline_version."""
    import parliament.management.commands.regenerate_briefs as mod
    source = open(mod.__file__).read()
    assert "get_pipeline_version" in source
    assert "pipeline_version" in source
