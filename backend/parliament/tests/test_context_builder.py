"""Tests for context_builder service."""
import json
from datetime import date
from unittest.mock import patch

from django.test import TestCase

from parliament.models import MP
from parliament.services.context_builder import (
    CONTEXT_JSON_PATH,
    build_context,
    format_context_for_prompt,
    load_context_json,
)
from schools.models import Constituency


class LoadContextJsonTest(TestCase):
    def test_loads_valid_json(self):
        """load_context_json returns a dict with version key."""
        ctx = load_context_json()
        self.assertIsInstance(ctx, dict)
        self.assertEqual(ctx["version"], "2.0")

    def test_has_required_sections(self):
        """Context JSON has all required top-level keys."""
        ctx = load_context_json()
        for key in ("cabinet", "glossary", "taxonomy", "national_baseline",
                     "national_education_plan", "domain"):
            self.assertIn(key, ctx, f"Missing key: {key}")


class BuildContextTest(TestCase):
    def test_returns_dict_with_static_and_runtime(self):
        """build_context merges static JSON with runtime data."""
        ctx = build_context()
        self.assertIn("cabinet", ctx)
        self.assertIn("school_names", ctx)
        self.assertIn("mp_portfolios", ctx)

    def test_school_names_is_list(self):
        """Runtime school names should be a list."""
        ctx = build_context()
        self.assertIsInstance(ctx["school_names"], list)

    def test_mp_portfolios_is_list(self):
        """Runtime MP portfolios should be a list."""
        ctx = build_context()
        self.assertIsInstance(ctx["mp_portfolios"], list)


class FormatContextForPromptTest(TestCase):
    def test_includes_cabinet_reference(self):
        """Formatted output includes cabinet reference section."""
        ctx = load_context_json()
        ctx["school_names"] = []
        ctx["mp_portfolios"] = []
        text = format_context_for_prompt(ctx)
        self.assertIn("CABINET REFERENCE", text)
        self.assertIn("Fadhlina", text)

    def test_includes_glossary(self):
        """Formatted output includes glossary section."""
        ctx = load_context_json()
        ctx["school_names"] = []
        ctx["mp_portfolios"] = []
        text = format_context_for_prompt(ctx)
        self.assertIn("GLOSSARY", text)
        self.assertIn("SJK(T)", text)

    def test_includes_taxonomy(self):
        """Formatted output includes taxonomy definitions."""
        ctx = load_context_json()
        ctx["school_names"] = []
        ctx["mp_portfolios"] = []
        text = format_context_for_prompt(ctx)
        self.assertIn("TAXONOMY DEFINITIONS", text)
        self.assertIn("General Rhetoric", text)

    def test_includes_national_baseline(self):
        """Formatted output includes national baseline stats."""
        ctx = load_context_json()
        ctx["school_names"] = []
        ctx["mp_portfolios"] = []
        text = format_context_for_prompt(ctx)
        self.assertIn("NATIONAL BASELINE", text)
        self.assertIn("528", text)

    def test_includes_rpm(self):
        """Formatted output includes RPM reference."""
        ctx = load_context_json()
        ctx["school_names"] = []
        ctx["mp_portfolios"] = []
        text = format_context_for_prompt(ctx)
        self.assertIn("NATIONAL EDUCATION PLAN", text)
        self.assertIn("RPM", text)


class MPPortfolioTest(TestCase):
    def test_mp_portfolio_field_exists(self):
        """MP model has a portfolio CharField."""
        field = MP._meta.get_field("portfolio")
        self.assertEqual(field.__class__.__name__, "CharField")

    def test_portfolio_default_blank(self):
        """Portfolio defaults to empty string."""
        field = MP._meta.get_field("portfolio")
        self.assertEqual(field.default, "")

    def test_build_context_includes_portfolio(self):
        """build_context returns MPs with portfolio data."""
        c = Constituency.objects.create(
            code="P999", name="Test", state="Test",
        )
        MP.objects.create(
            constituency=c,
            name="Test Minister",
            portfolio="Minister of Education",
        )
        ctx = build_context()
        portfolios = ctx["mp_portfolios"]
        self.assertEqual(len(portfolios), 1)
        self.assertEqual(portfolios[0]["portfolio"], "Minister of Education")


class ContextStalenessTests(TestCase):
    """Test staleness detection for context JSON."""

    def test_recent_context_no_warning(self):
        """Context updated recently should not produce a warning."""
        with patch("parliament.services.context_builder.logger") as mock_logger:
            build_context()
            # Should not have any warning calls about staleness
            warning_calls = [
                c for c in mock_logger.warning.call_args_list
                if "stale" in str(c).lower()
            ]
            self.assertEqual(len(warning_calls), 0)

    def test_stale_context_logs_warning(self):
        """Context older than 180 days should log a warning."""
        original = CONTEXT_JSON_PATH.read_text()
        try:
            data = json.loads(original)
            data["last_updated"] = "2025-01-01"
            CONTEXT_JSON_PATH.write_text(json.dumps(data))

            with patch("parliament.services.context_builder.logger") as mock_logger:
                build_context()
                warning_calls = [
                    c for c in mock_logger.warning.call_args_list
                    if "stale" in str(c).lower()
                ]
                self.assertGreaterEqual(len(warning_calls), 1)
        finally:
            CONTEXT_JSON_PATH.write_text(original)

    def test_missing_last_updated_no_crash(self):
        """Context without last_updated field should not crash."""
        original = CONTEXT_JSON_PATH.read_text()
        try:
            data = json.loads(original)
            data.pop("last_updated", None)
            CONTEXT_JSON_PATH.write_text(json.dumps(data))

            # Should not raise
            ctx = build_context()
            self.assertIn("cabinet", ctx)
        finally:
            CONTEXT_JSON_PATH.write_text(original)
