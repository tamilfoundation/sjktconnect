"""Tests for the source_tag audience filter + compose_welcome_broadcast."""

import pytest
from django.core.management import call_command

from broadcasts.models import Broadcast
from broadcasts.services.audience import get_filtered_subscribers
from subscribers.models import Subscriber


@pytest.mark.django_db
def test_source_tag_filter_targets_exact_active_batch():
    Subscriber.objects.create(email="a@example.com", is_active=True, source_tag="TF_PARENTS_2026")
    Subscriber.objects.create(email="b@example.com", is_active=True, source_tag="TF_ALUMNI")
    Subscriber.objects.create(email="c@example.com", is_active=False, source_tag="TF_PARENTS_2026")

    qs = get_filtered_subscribers({"source_tag": "TF_PARENTS_2026"})

    assert set(qs.values_list("email", flat=True)) == {"a@example.com"}


@pytest.mark.django_db
def test_compose_welcome_creates_draft_broadcast():
    Subscriber.objects.create(email="p1@example.com", name="P1", is_active=True, source_tag="TF_PARENTS_2026")
    Subscriber.objects.create(email="p2@example.com", name="P2", is_active=True, source_tag="TF_PARENTS_2026")

    call_command("compose_welcome_broadcast", source_tag="TF_PARENTS_2026")

    b = Broadcast.objects.get(kind=Broadcast.Kind.WELCOME)
    assert b.status == Broadcast.Status.DRAFT
    assert b.audience_filter == {"source_tag": "TF_PARENTS_2026"}
    assert b.recipient_count == 2
    assert "SJK(T) Connect" in b.html_content
    # null coverage dates → unique_broadcast_per_kind_coverage does NOT apply,
    # so a second segment can get its own WELCOME broadcast
    assert b.coverage_start_date is None and b.coverage_end_date is None


@pytest.mark.django_db
def test_two_segments_each_get_their_own_welcome():
    Subscriber.objects.create(email="p@example.com", is_active=True, source_tag="TF_PARENTS_2026")
    Subscriber.objects.create(email="a@example.com", is_active=True, source_tag="TF_ALUMNI_2026")

    call_command("compose_welcome_broadcast", source_tag="TF_PARENTS_2026")
    call_command("compose_welcome_broadcast", source_tag="TF_ALUMNI_2026")

    assert Broadcast.objects.filter(kind=Broadcast.Kind.WELCOME).count() == 2


@pytest.mark.django_db
def test_compose_welcome_dry_run_creates_nothing():
    Subscriber.objects.create(email="p1@example.com", is_active=True, source_tag="TF_PARENTS_2026")
    call_command("compose_welcome_broadcast", source_tag="TF_PARENTS_2026", dry_run=True)
    assert not Broadcast.objects.filter(kind=Broadcast.Kind.WELCOME).exists()
