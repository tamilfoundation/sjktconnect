"""Tests for schools app models."""

from django.test import TestCase

from core.models import AuditLog
from schools.models import Constituency, DUN, School


class ConstituencyModelTest(TestCase):
    def test_create_constituency(self):
        c = Constituency.objects.create(code="P140", name="Segamat", state="Johor")
        assert c.pk == "P140"
        assert str(c) == "P140 Segamat"

    def test_constituency_ordering(self):
        Constituency.objects.create(code="P140", name="Segamat", state="Johor")
        Constituency.objects.create(code="P001", name="Padang Besar", state="Perlis")
        codes = list(Constituency.objects.values_list("code", flat=True))
        assert codes == ["P001", "P140"]


class DUNModelTest(TestCase):
    def setUp(self):
        self.constituency = Constituency.objects.create(
            code="P140", name="Segamat", state="Johor"
        )

    def test_create_dun(self):
        d = DUN.objects.create(
            code="N01", name="Buloh Kasap",
            constituency=self.constituency, state="Johor",
        )
        assert d.pk is not None
        assert d.code == "N01"
        assert str(d) == "N01 Buloh Kasap"
        assert d.constituency == self.constituency

    def test_dun_cascade_on_constituency_delete(self):
        DUN.objects.create(
            code="N01", name="Buloh Kasap",
            constituency=self.constituency, state="Johor",
        )
        self.constituency.delete()
        assert DUN.objects.count() == 0


class SchoolModelTest(TestCase):
    def setUp(self):
        self.constituency = Constituency.objects.create(
            code="P140", name="Segamat", state="Johor"
        )
        self.dun = DUN.objects.create(
            code="N01", name="Buloh Kasap",
            constituency=self.constituency, state="Johor",
        )

    def test_create_school(self):
        s = School.objects.create(
            moe_code="JBD0050",
            name="SEKOLAH JENIS KEBANGSAAN (TAMIL) LADANG BIKAM",
            short_name="SJK(T) LADANG BIKAM",
            state="Johor",
            constituency=self.constituency,
            dun=self.dun,
            enrolment=120,
            teacher_count=8,
        )
        assert s.pk == "JBD0050"
        assert str(s) == "JBD0050 SJK(T) LADANG BIKAM"
        assert s.is_active is True
        assert s.gps_verified is False

    def test_school_constituency_set_null_on_delete(self):
        s = School.objects.create(
            moe_code="JBD0050",
            name="Test School",
            short_name="SJK(T) Test",
            state="Johor",
            constituency=self.constituency,
        )
        self.constituency.delete()
        s.refresh_from_db()
        assert s.constituency is None

    def test_school_ordering(self):
        School.objects.create(moe_code="ZZZ0001", name="Z School", short_name="SJK(T) Z", state="Johor")
        School.objects.create(moe_code="AAA0001", name="A School", short_name="SJK(T) A", state="Johor")
        codes = list(School.objects.values_list("moe_code", flat=True))
        assert codes == ["AAA0001", "ZZZ0001"]


class AuditLogModelTest(TestCase):
    def test_create_audit_log(self):
        log = AuditLog.objects.create(
            action="create",
            target_type="School",
            target_id="JBD0050",
            detail={"action": "create"},
        )
        assert log.pk is not None
        assert "create" in str(log)
        assert log.user is None

    def test_audit_log_ordering(self):
        AuditLog.objects.create(action="create", target_type="School", target_id="A")
        AuditLog.objects.create(action="update", target_type="School", target_id="B")
        logs = list(AuditLog.objects.values_list("target_id", flat=True))
        # Most recent first
        assert logs == ["B", "A"]
