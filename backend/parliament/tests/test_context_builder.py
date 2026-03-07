"""Tests for context_builder service."""
from django.test import TestCase

from parliament.services.context_builder import (
    build_context,
    format_context_for_prompt,
    load_context_json,
)


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
