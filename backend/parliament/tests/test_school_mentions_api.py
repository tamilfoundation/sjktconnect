"""Tests for school and constituency mentions API endpoints."""

import datetime

from django.test import TestCase

from hansard.models import HansardMention, HansardSitting, MentionedSchool
from schools.models import Constituency, School


class SchoolMentionsAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.school = School.objects.create(
            moe_code="JBD0050",
            name="SJK(T) Ladang Bikam",
            short_name="SJK(T) Ladang Bikam",
            state="Johor",
        )
        cls.sitting = HansardSitting.objects.create(
            sitting_date=datetime.date(2026, 2, 26),
            pdf_url="https://example.com/DR-26022026.pdf",
            pdf_filename="DR-26022026.pdf",
            status="COMPLETED",
        )
        cls.approved_mention = HansardMention.objects.create(
            sitting=cls.sitting,
            verbatim_quote="SJK(T) Ladang Bikam needs repairs.",
            mp_name="Yuneswaran",
            mp_constituency="Segamat",
            mp_party="PH (PKR)",
            mention_type="QUESTION",
            significance=4,
            sentiment="NEGATIVE",
            ai_summary="MP raised school infrastructure issue.",
            review_status="APPROVED",
        )
        MentionedSchool.objects.create(
            mention=cls.approved_mention,
            school=cls.school,
            confidence_score=100,
            matched_by="EXACT",
        )

    def test_returns_approved_mentions(self):
        resp = self.client.get("/api/v1/schools/JBD0050/mentions/")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        mention = data[0]
        assert mention["sitting_date"] == "2026-02-26"
        assert mention["mp_name"] == "Yuneswaran"
        assert mention["mp_constituency"] == "Segamat"
        assert mention["mp_party"] == "PH (PKR)"
        assert mention["mention_type"] == "QUESTION"
        assert mention["significance"] == 4
        assert mention["sentiment"] == "NEGATIVE"
        assert mention["ai_summary"] == "MP raised school infrastructure issue."
        assert mention["verbatim_quote"] == "SJK(T) Ladang Bikam needs repairs."

    def test_includes_pending_mentions(self):
        pending = HansardMention.objects.create(
            sitting=self.sitting,
            verbatim_quote="Pending mention.",
            review_status="PENDING",
        )
        MentionedSchool.objects.create(
            mention=pending, school=self.school,
            confidence_score=80, matched_by="TRIGRAM",
        )
        resp = self.client.get("/api/v1/schools/JBD0050/mentions/")
        quotes = [m["verbatim_quote"] for m in resp.json()]
        assert "Pending mention." in quotes

    def test_excludes_rejected_mentions(self):
        rejected = HansardMention.objects.create(
            sitting=self.sitting,
            verbatim_quote="Rejected mention.",
            review_status="REJECTED",
        )
        MentionedSchool.objects.create(
            mention=rejected, school=self.school,
            confidence_score=90, matched_by="EXACT",
        )
        resp = self.client.get("/api/v1/schools/JBD0050/mentions/")
        quotes = [m["verbatim_quote"] for m in resp.json()]
        assert "Rejected mention." not in quotes

    def test_returns_empty_for_school_with_no_mentions(self):
        School.objects.create(
            moe_code="JBD9999",
            name="SJK(T) No Mentions",
            short_name="SJK(T) No Mentions",
            state="Johor",
        )
        resp = self.client.get("/api/v1/schools/JBD9999/mentions/")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_404_for_nonexistent_school(self):
        resp = self.client.get("/api/v1/schools/XXXXXX/mentions/")
        assert resp.status_code == 404

    def test_ordered_by_sitting_date_descending(self):
        older_sitting = HansardSitting.objects.create(
            sitting_date=datetime.date(2026, 1, 15),
            pdf_url="https://example.com/DR-15012026.pdf",
            pdf_filename="DR-15012026.pdf",
            status="COMPLETED",
        )
        older_mention = HansardMention.objects.create(
            sitting=older_sitting,
            verbatim_quote="Older mention.",
            review_status="APPROVED",
        )
        MentionedSchool.objects.create(
            mention=older_mention, school=self.school,
            confidence_score=100, matched_by="EXACT",
        )
        resp = self.client.get("/api/v1/schools/JBD0050/mentions/")
        data = resp.json()
        assert len(data) == 2
        assert data[0]["sitting_date"] == "2026-02-26"
        assert data[1]["sitting_date"] == "2026-01-15"


class ConstituencyMentionsAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.constituency = Constituency.objects.create(
            code="P150",
            name="Segamat",
            state="Johor",
        )
        cls.sitting = HansardSitting.objects.create(
            sitting_date=datetime.date(2026, 2, 26),
            pdf_url="https://example.com/DR-26022026.pdf",
            pdf_filename="DR-26022026.pdf",
            status="COMPLETED",
        )
        cls.mention = HansardMention.objects.create(
            sitting=cls.sitting,
            verbatim_quote="Tamil schools in Segamat.",
            mp_name="Yuneswaran",
            mp_constituency="Segamat",
            mp_party="PH (PKR)",
            mention_type="QUESTION",
            significance=4,
            sentiment="NEGATIVE",
            ai_summary="MP raised school infrastructure issue.",
            review_status="PENDING",
        )

    def test_returns_mentions_for_constituency(self):
        resp = self.client.get("/api/v1/constituencies/P150/mentions/")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["mp_name"] == "Yuneswaran"
        assert data[0]["ai_summary"] == "MP raised school infrastructure issue."

    def test_excludes_rejected(self):
        HansardMention.objects.create(
            sitting=self.sitting,
            verbatim_quote="Rejected.",
            mp_name="Other MP",
            mp_constituency="Segamat",
            review_status="REJECTED",
        )
        resp = self.client.get("/api/v1/constituencies/P150/mentions/")
        names = [m["mp_name"] for m in resp.json()]
        assert "Other MP" not in names

    def test_excludes_empty_mp_name(self):
        HansardMention.objects.create(
            sitting=self.sitting,
            verbatim_quote="No MP identified.",
            mp_name="",
            mp_constituency="Segamat",
            review_status="PENDING",
        )
        resp = self.client.get("/api/v1/constituencies/P150/mentions/")
        assert len(resp.json()) == 1

    def test_404_for_nonexistent_constituency(self):
        resp = self.client.get("/api/v1/constituencies/P999/mentions/")
        assert resp.status_code == 404

    def test_empty_for_no_mentions(self):
        Constituency.objects.create(code="P001", name="No Mentions", state="KL")
        resp = self.client.get("/api/v1/constituencies/P001/mentions/")
        assert resp.status_code == 200
        assert resp.json() == []
