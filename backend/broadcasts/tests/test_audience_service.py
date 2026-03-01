"""Tests for audience filtering service."""

import pytest

from broadcasts.services.audience import get_filtered_subscribers
from schools.models import Constituency, School
from subscribers.models import Subscriber, SubscriptionPreference


@pytest.fixture
def constituency(db):
    return Constituency.objects.create(
        code="P140", name="Segamat", state="JOHOR"
    )


@pytest.fixture
def school_johor(db, constituency):
    return School.objects.create(
        moe_code="JBD0050",
        name="SJK(T) Ladang Bikam",
        short_name="SJK(T) Ladang Bikam",
        state="JOHOR",
        ppd="PPD Segamat",
        constituency=constituency,
        email="jbd0050@moe.edu.my",
        enrolment=120,
        skm_eligible=False,
    )


@pytest.fixture
def school_perak(db):
    return School.objects.create(
        moe_code="ABD0010",
        name="SJK(T) Perak School",
        short_name="SJK(T) Perak School",
        state="PERAK",
        ppd="PPD Ipoh",
        email="abd0010@moe.edu.my",
        enrolment=300,
        skm_eligible=True,
    )


@pytest.fixture
def active_subscriber(db):
    return Subscriber.objects.create(
        email="community@example.com", name="Community Leader", is_active=True
    )


@pytest.fixture
def school_subscriber(db, school_johor):
    """Subscriber whose email matches a school email."""
    return Subscriber.objects.create(
        email="jbd0050@moe.edu.my", name="School Contact", is_active=True
    )


@pytest.fixture
def perak_school_subscriber(db, school_perak):
    """Subscriber whose email matches the Perak school."""
    return Subscriber.objects.create(
        email="abd0010@moe.edu.my", name="Perak Contact", is_active=True
    )


@pytest.fixture
def inactive_subscriber(db):
    return Subscriber.objects.create(
        email="gone@example.com", name="Gone User", is_active=False
    )


@pytest.mark.django_db
class TestGetFilteredSubscribers:
    def test_returns_all_active_no_filter(self, active_subscriber, school_subscriber):
        """No filter returns all active subscribers."""
        result = get_filtered_subscribers({})
        assert result.count() == 2

    def test_excludes_inactive(self, active_subscriber, inactive_subscriber):
        """Inactive subscribers are excluded."""
        result = get_filtered_subscribers({})
        assert result.count() == 1
        assert result.first().email == "community@example.com"

    def test_filter_by_category(self, active_subscriber, school_subscriber):
        """Filter by subscription category preference."""
        SubscriptionPreference.objects.create(
            subscriber=active_subscriber,
            category=SubscriptionPreference.PARLIAMENT_WATCH,
            is_enabled=True,
        )
        SubscriptionPreference.objects.create(
            subscriber=school_subscriber,
            category=SubscriptionPreference.PARLIAMENT_WATCH,
            is_enabled=False,  # Disabled
        )
        result = get_filtered_subscribers({"category": "PARLIAMENT_WATCH"})
        assert result.count() == 1
        assert result.first().email == "community@example.com"

    def test_filter_by_state(self, school_subscriber, perak_school_subscriber, school_johor, school_perak):
        """Filter by state returns subscribers matching school emails in that state."""
        result = get_filtered_subscribers({"state": "JOHOR"})
        assert result.count() == 1
        assert result.first().email == "jbd0050@moe.edu.my"

    def test_filter_by_constituency(
        self, school_subscriber, constituency, school_johor
    ):
        """Filter by constituency code."""
        result = get_filtered_subscribers({"constituency": "P140"})
        assert result.count() == 1
        assert result.first().email == "jbd0050@moe.edu.my"

    def test_filter_by_ppd(self, school_subscriber, school_johor):
        """Filter by PPD district."""
        result = get_filtered_subscribers({"ppd": "PPD Segamat"})
        assert result.count() == 1
        assert result.first().email == "jbd0050@moe.edu.my"

    def test_filter_by_skm(self, school_subscriber, perak_school_subscriber, school_johor, school_perak):
        """Filter by SKM eligibility."""
        result = get_filtered_subscribers({"skm": True})
        assert result.count() == 1
        assert result.first().email == "abd0010@moe.edu.my"

    def test_filter_by_skm_string(self, perak_school_subscriber, school_perak):
        """SKM filter accepts string 'true'."""
        result = get_filtered_subscribers({"skm": "true"})
        assert result.count() == 1

    def test_filter_by_min_enrolment(
        self, school_subscriber, perak_school_subscriber, school_johor, school_perak
    ):
        """Filter by minimum enrolment."""
        result = get_filtered_subscribers({"min_enrolment": 200})
        assert result.count() == 1
        assert result.first().email == "abd0010@moe.edu.my"

    def test_filter_by_max_enrolment(
        self, school_subscriber, perak_school_subscriber, school_johor, school_perak
    ):
        """Filter by maximum enrolment."""
        result = get_filtered_subscribers({"max_enrolment": 150})
        assert result.count() == 1
        assert result.first().email == "jbd0050@moe.edu.my"

    def test_filter_by_enrolment_range(
        self, school_subscriber, perak_school_subscriber, school_johor, school_perak
    ):
        """Filter by enrolment range."""
        result = get_filtered_subscribers(
            {"min_enrolment": 100, "max_enrolment": 200}
        )
        assert result.count() == 1
        assert result.first().email == "jbd0050@moe.edu.my"

    def test_combined_filters(
        self, school_subscriber, perak_school_subscriber, school_johor, school_perak
    ):
        """Multiple filters are combined (AND logic)."""
        result = get_filtered_subscribers(
            {"state": "JOHOR", "max_enrolment": 200}
        )
        assert result.count() == 1
        assert result.first().email == "jbd0050@moe.edu.my"

    def test_empty_result_no_match(self, active_subscriber, school_subscriber):
        """Returns empty queryset when no subscribers match."""
        result = get_filtered_subscribers({"state": "SABAH"})
        assert result.count() == 0

    def test_distinct_results(self, school_subscriber, school_johor):
        """Results are distinct even with multiple filter paths."""
        # Add two preferences for the same subscriber
        SubscriptionPreference.objects.create(
            subscriber=school_subscriber,
            category=SubscriptionPreference.PARLIAMENT_WATCH,
            is_enabled=True,
        )
        SubscriptionPreference.objects.create(
            subscriber=school_subscriber,
            category=SubscriptionPreference.NEWS_WATCH,
            is_enabled=True,
        )
        # Filter by state (matches school email) — should still be 1 result
        result = get_filtered_subscribers({"state": "JOHOR"})
        assert result.count() == 1

    def test_empty_filter_dict_same_as_no_filter(
        self, active_subscriber, school_subscriber
    ):
        """Empty dict returns all active subscribers."""
        result = get_filtered_subscribers({})
        assert result.count() == 2
