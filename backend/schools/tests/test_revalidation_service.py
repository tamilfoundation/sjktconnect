"""Tests for schools/services/revalidation.py (TD-21, 2026-06-26)."""

from unittest.mock import patch, MagicMock

import pytest

from schools.services.revalidation import (
    build_school_slug,
    trigger_school_revalidate,
)
from schools.models import School


@pytest.mark.django_db
class TestBuildSchoolSlug:
    """Mirror of frontend/lib/urls.ts::schoolPath. Drift here breaks
    revalidation — the route handler revalidates the slug the BACKEND
    computed, but the user lands on the slug the FRONTEND computed."""

    def test_with_short_name_and_city(self):
        slug = build_school_slug("PBD1088", "SJK(T) Subramaniya Barathee", "Gelugor")
        assert slug == "subramaniya-barathee-gelugor-pbd1088"

    def test_strips_sjkt_prefix_uppercase(self):
        slug = build_school_slug("JBD0050", "SJK(T) Ladang Bikam", "Segamat")
        assert slug == "ladang-bikam-segamat-jbd0050"

    def test_strips_sjkt_no_parens(self):
        slug = build_school_slug("ABC1234", "SJKT Foo Bar", "Town")
        assert slug == "foo-bar-town-abc1234"

    def test_with_missing_city(self):
        slug = build_school_slug("XYZ9999", "SJK(T) Alpha", None)
        assert slug == "alpha-xyz9999"

    def test_with_missing_name(self):
        slug = build_school_slug("XYZ9999", None, "Bandar")
        assert slug == "bandar-xyz9999"

    def test_collapses_runs_of_non_alnum(self):
        slug = build_school_slug("ABC1234", "Foo!!!  Bar___Baz", "City")
        assert slug == "foo-bar-baz-city-abc1234"

    def test_trims_leading_and_trailing_hyphens(self):
        slug = build_school_slug("ABC1234", "!Foo!", "!City!")
        assert slug == "foo-city-abc1234"

    def test_unicode_collapses_to_hyphens(self):
        # Tamil characters aren't [a-z0-9] → become a single hyphen.
        slug = build_school_slug("ABC1234", "சுப்பிரமணியம்", "Town")
        assert slug == "town-abc1234"


@pytest.mark.django_db
class TestTriggerSchoolRevalidate:
    """The trigger is a fire-and-forget POST; tests focus on the
    no-op path (env vars unset) and the happy path (env vars set,
    POST sent with correct headers + body)."""

    @pytest.fixture
    def school(self, db):
        return School.objects.create(
            moe_code="JBD0050",
            name="SJK(T) Ladang Bikam",
            short_name="SJK(T) Ladang Bikam",
            city="Segamat",
            state="Johor",
            is_active=True,
        )

    def test_noop_when_env_unset(self, school):
        # No env vars → no POST, no exception.
        with patch("schools.services.revalidation.requests.post") as mock_post:
            with patch.dict("os.environ", {}, clear=True):
                trigger_school_revalidate(school)
            mock_post.assert_not_called()

    def test_posts_with_token_and_slug(self, school):
        env = {
            "REVALIDATE_WEBHOOK_URL": "https://tamilschool.org/api/revalidate",
            "REVALIDATE_TOKEN": "secret123",
        }
        with patch("schools.services.revalidation.requests.post") as mock_post:
            mock_post.return_value = MagicMock(status_code=200, text="ok")
            with patch.dict("os.environ", env, clear=False):
                trigger_school_revalidate(school)
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert args[0] == "https://tamilschool.org/api/revalidate"
        assert kwargs["headers"]["X-Revalidate-Token"] == "secret123"
        body = kwargs["json"]
        assert body == {
            "type": "school",
            "key": "JBD0050",
            "slug": "ladang-bikam-segamat-jbd0050",
        }

    def test_swallows_network_errors(self, school):
        env = {
            "REVALIDATE_WEBHOOK_URL": "https://tamilschool.org/api/revalidate",
            "REVALIDATE_TOKEN": "secret123",
        }
        with patch("schools.services.revalidation.requests.post") as mock_post:
            mock_post.side_effect = ConnectionError("DNS failure")
            with patch.dict("os.environ", env, clear=False):
                # Must not raise — revalidate is fire-and-forget.
                trigger_school_revalidate(school)

    def test_logs_4xx_5xx_responses_without_raising(self, school):
        env = {
            "REVALIDATE_WEBHOOK_URL": "https://tamilschool.org/api/revalidate",
            "REVALIDATE_TOKEN": "secret123",
        }
        with patch("schools.services.revalidation.requests.post") as mock_post:
            mock_post.return_value = MagicMock(status_code=401, text="unauthorized")
            with patch.dict("os.environ", env, clear=False):
                trigger_school_revalidate(school)
        # No exception raised; logger.warning was called inside.
