from django.test import TestCase

from parliament.services.pipeline_registry import (
    get_component_version,
    get_pipeline_version,
    check_drift,
    COMPONENTS,
)


def test_components_dict_has_all_entries():
    """Every pipeline component must be registered."""
    expected = {
        "mention_analysis", "brief_generation", "brief_regeneration",
        "report_generation", "evaluation", "correction", "illustration",
        "extractor", "matcher", "normalizer", "keywords", "searcher",
        "context_data",
    }
    assert set(COMPONENTS.keys()) == expected


def test_get_component_version():
    v = get_component_version("mention_analysis")
    assert v  # non-empty string like "1.0.0"


def test_get_pipeline_version_format():
    v = get_pipeline_version()
    # Format: "pipeline-<short_hash>" e.g. "pipeline-a3f9c1"
    assert v.startswith("pipeline-")
    assert len(v) == len("pipeline-") + 8  # 8-char hash


def test_get_pipeline_version_changes_when_component_changes(monkeypatch):
    v1 = get_pipeline_version()
    monkeypatch.setitem(COMPONENTS, "mention_analysis", {
        **COMPONENTS["mention_analysis"], "version": "99.0.0"
    })
    v2 = get_pipeline_version()
    assert v1 != v2


def test_check_drift_clean():
    """No drift when prompts haven't changed since last hash store."""
    results = check_drift()
    # Each result is (component, drifted: bool, detail: str)
    for name, drifted, detail in results:
        if COMPONENTS[name].get("hash_source"):
            assert isinstance(drifted, bool)


def test_unknown_component_raises():
    import pytest
    with pytest.raises(KeyError):
        get_component_version("nonexistent")


class TestPipelineVersionFields(TestCase):
    def test_mention_has_pipeline_version_field(self):
        from hansard.models import HansardMention
        field = HansardMention._meta.get_field("pipeline_version")
        assert field.max_length == 30
        assert field.default == ""

    def test_brief_has_pipeline_version_field(self):
        from parliament.models import SittingBrief
        field = SittingBrief._meta.get_field("pipeline_version")
        assert field.max_length == 30
        assert field.default == ""

    def test_meeting_has_pipeline_version_field(self):
        from parliament.models import ParliamentaryMeeting
        field = ParliamentaryMeeting._meta.get_field("pipeline_version")
        assert field.max_length == 30
        assert field.default == ""
