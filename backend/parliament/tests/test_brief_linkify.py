"""Tests for hyperlinking mentioned schools inside a sitting brief."""

from datetime import date

import pytest

from hansard.models import HansardMention, HansardSitting, MentionedSchool
from parliament.services.brief_linkify import linkify_schools
from schools.models import School


def _setup():
    school = School.objects.create(
        moe_code="BBD8469",
        name="Sekolah Jenis Kebangsaan (Tamil) Ldg Seafield",
        short_name="SJK(T) Ldg Seafield",
        city="Subang Jaya", state="SELANGOR",
    )
    sitting = HansardSitting.objects.create(
        sitting_date=date(2026, 6, 22), status=HansardSitting.Status.COMPLETED,
        pdf_url="https://x/x.pdf", pdf_filename="x.pdf",
    )
    m = HansardMention.objects.create(sitting=sitting, verbatim_quote="q")
    MentionedSchool.objects.create(
        mention=m, school=school, matched_text="sjkt ladang seafield",
        confidence_score=100, matched_by=MentionedSchool.MatchMethod.EXACT,
    )
    return sitting


@pytest.mark.django_db
def test_linkify_wraps_mentioned_school_with_canonical_url():
    sitting = _setup()
    html = "<p>The Minister mentioned SJK(T) Ladang Seafield during the debate.</p>"
    out = linkify_schools(html, sitting)
    assert '<a href="https://tamilschool.org/en/school/' in out
    assert "bbd8469" in out.lower()
    # The whole "SJK(T) Ladang Seafield" span is linked, HTML stays balanced
    assert "SJK(T) Ladang Seafield</a>" in out
    assert out.count("<a ") == out.count("</a>")


@pytest.mark.django_db
def test_linkify_matches_ldg_ladang_variant():
    sitting = _setup()
    # brief uses the abbreviated "Ldg" form
    out = linkify_schools("<p>Funding for SJK(T) Ldg Seafield was raised.</p>", sitting)
    assert "bbd8469" in out.lower()


@pytest.mark.django_db
def test_linkify_is_idempotent():
    sitting = _setup()
    once = linkify_schools("<p>SJK(T) Ladang Seafield</p>", sitting)
    twice = linkify_schools(once, sitting)
    assert once == twice  # already-linked HTML is returned unchanged
    assert once.count("<a ") == 1


@pytest.mark.django_db
def test_linkify_noop_when_no_matched_schools():
    sitting = HansardSitting.objects.create(
        sitting_date=date(2026, 6, 23), status=HansardSitting.Status.COMPLETED,
        pdf_url="https://x/x.pdf", pdf_filename="x.pdf",
    )
    html = "<p>No schools were named.</p>"
    assert linkify_schools(html, sitting) == html
