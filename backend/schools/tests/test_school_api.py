"""Tests for School, Constituency, DUN REST API endpoints and Search."""

from django.test import TestCase

from schools.models import Constituency, DUN, School


class SchoolAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.constituency = Constituency.objects.create(
            code="P140", name="Segamat", state="Johor",
            mp_name="Yuneswaran", mp_party="PH (PKR)",
        )
        cls.dun = DUN.objects.create(
            code="N01", name="Buloh Kasap", state="Johor",
            constituency=cls.constituency,
        )
        cls.school = School.objects.create(
            moe_code="JBD0050",
            name="SJK(T) LADANG BIKAM",
            short_name="SJK(T) Ladang Bikam",
            state="Johor",
            ppd="PPD Segamat",
            constituency=cls.constituency,
            dun=cls.dun,
            enrolment=120,
            teacher_count=8,
            skm_eligible=True,
        )
        School.objects.create(
            moe_code="AGD1234",
            name="SJK(T) LADANG SUNGAI",
            short_name="SJK(T) Ladang Sungai",
            state="Kedah",
            ppd="PPD Kulim",
            enrolment=50,
            teacher_count=4,
        )

    def test_school_list(self):
        resp = self.client.get("/api/v1/schools/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 2
        assert len(data["results"]) == 2

    def test_school_list_filter_state(self):
        resp = self.client.get("/api/v1/schools/?state=Johor")
        assert resp.status_code == 200
        assert resp.json()["count"] == 1
        assert resp.json()["results"][0]["moe_code"] == "JBD0050"

    def test_school_list_filter_ppd(self):
        resp = self.client.get("/api/v1/schools/?ppd=PPD Segamat")
        assert resp.status_code == 200
        assert resp.json()["count"] == 1

    def test_school_list_filter_constituency(self):
        resp = self.client.get("/api/v1/schools/?constituency=P140")
        assert resp.status_code == 200
        assert resp.json()["count"] == 1

    def test_school_list_filter_skm(self):
        resp = self.client.get("/api/v1/schools/?skm=true")
        assert resp.status_code == 200
        assert resp.json()["count"] == 1

    def test_school_list_filter_enrolment_range(self):
        resp = self.client.get("/api/v1/schools/?min_enrolment=100&max_enrolment=200")
        assert resp.status_code == 200
        assert resp.json()["count"] == 1
        assert resp.json()["results"][0]["moe_code"] == "JBD0050"

    def test_school_detail(self):
        resp = self.client.get("/api/v1/schools/JBD0050/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["moe_code"] == "JBD0050"
        assert data["constituency_code"] == "P140"
        assert data["dun_code"] == "N01"
        assert data["enrolment"] == 120

    def test_school_detail_not_found(self):
        resp = self.client.get("/api/v1/schools/ZZZZZ/")
        assert resp.status_code == 404

    def test_school_list_excludes_inactive(self):
        School.objects.create(
            moe_code="XXX0001",
            name="SJK(T) CLOSED",
            short_name="SJK(T) Closed",
            state="Johor",
            is_active=False,
        )
        resp = self.client.get("/api/v1/schools/")
        codes = [s["moe_code"] for s in resp.json()["results"]]
        assert "XXX0001" not in codes


class ConstituencyAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.c1 = Constituency.objects.create(
            code="P140", name="Segamat", state="Johor",
            mp_name="Yuneswaran", mp_party="PH (PKR)",
        )
        cls.c2 = Constituency.objects.create(
            code="P141", name="Sekijang", state="Johor",
            mp_name="Zaliha", mp_party="PH (PKR)",
        )
        School.objects.create(
            moe_code="JBD0050",
            name="SJK(T) LADANG BIKAM",
            short_name="SJK(T) Ladang Bikam",
            state="Johor",
            constituency=cls.c1,
            enrolment=120,
        )

    def test_constituency_list(self):
        resp = self.client.get("/api/v1/constituencies/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 2

    def test_constituency_list_has_school_count(self):
        resp = self.client.get("/api/v1/constituencies/")
        results = resp.json()["results"]
        p140 = next(r for r in results if r["code"] == "P140")
        assert p140["school_count"] == 1
        p141 = next(r for r in results if r["code"] == "P141")
        assert p141["school_count"] == 0

    def test_constituency_list_filter_state(self):
        Constituency.objects.create(code="P001", name="Langkawi", state="Kedah")
        resp = self.client.get("/api/v1/constituencies/?state=Johor")
        assert resp.json()["count"] == 2

    def test_constituency_detail(self):
        resp = self.client.get("/api/v1/constituencies/P140/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == "P140"
        assert data["mp_name"] == "Yuneswaran"
        assert len(data["schools"]) == 1

    def test_constituency_detail_not_found(self):
        resp = self.client.get("/api/v1/constituencies/P999/")
        assert resp.status_code == 404


class DUNAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.constituency = Constituency.objects.create(
            code="P140", name="Segamat", state="Johor",
        )
        cls.dun = DUN.objects.create(
            code="N01", name="Buloh Kasap", state="Johor",
            constituency=cls.constituency,
            adun_name="Zahari", adun_party="BN (UMNO)",
        )
        School.objects.create(
            moe_code="JBD0050",
            name="SJK(T) LADANG BIKAM",
            short_name="SJK(T) Ladang Bikam",
            state="Johor",
            dun=cls.dun,
            constituency=cls.constituency,
        )

    def test_dun_list(self):
        resp = self.client.get("/api/v1/duns/")
        assert resp.status_code == 200
        assert resp.json()["count"] == 1

    def test_dun_list_filter_state(self):
        c2 = Constituency.objects.create(code="P001", name="Langkawi", state="Kedah")
        DUN.objects.create(code="N01", name="Ayer Hangat", state="Kedah", constituency=c2)
        resp = self.client.get("/api/v1/duns/?state=Johor")
        assert resp.json()["count"] == 1

    def test_dun_list_filter_constituency(self):
        resp = self.client.get("/api/v1/duns/?constituency=P140")
        assert resp.json()["count"] == 1

    def test_dun_detail(self):
        resp = self.client.get(f"/api/v1/duns/{self.dun.pk}/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == "N01"
        assert data["constituency_code"] == "P140"
        assert data["adun_name"] == "Zahari"
        assert len(data["schools"]) == 1

    def test_dun_detail_not_found(self):
        resp = self.client.get("/api/v1/duns/99999/")
        assert resp.status_code == 404


class SearchAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.constituency = Constituency.objects.create(
            code="P140", name="Segamat", state="Johor",
            mp_name="Yuneswaran",
        )
        School.objects.create(
            moe_code="JBD0050",
            name="SJK(T) LADANG BIKAM",
            short_name="SJK(T) Ladang Bikam",
            state="Johor",
            constituency=cls.constituency,
        )

    def test_search_school_by_name(self):
        resp = self.client.get("/api/v1/search/?q=Bikam")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["schools"]) == 1
        assert data["schools"][0]["moe_code"] == "JBD0050"

    def test_search_school_by_code(self):
        resp = self.client.get("/api/v1/search/?q=JBD")
        assert resp.status_code == 200
        assert len(resp.json()["schools"]) == 1

    def test_search_constituency_by_name(self):
        resp = self.client.get("/api/v1/search/?q=Segamat")
        assert resp.status_code == 200
        assert len(resp.json()["constituencies"]) == 1

    def test_search_constituency_by_mp(self):
        resp = self.client.get("/api/v1/search/?q=Yuneswaran")
        assert resp.status_code == 200
        assert len(resp.json()["constituencies"]) == 1

    def test_search_too_short(self):
        resp = self.client.get("/api/v1/search/?q=a")
        assert resp.status_code == 400

    def test_search_no_results(self):
        resp = self.client.get("/api/v1/search/?q=zzzznonexistent")
        assert resp.status_code == 200
        assert len(resp.json()["schools"]) == 0
        assert len(resp.json()["constituencies"]) == 0

    def test_search_empty_query(self):
        resp = self.client.get("/api/v1/search/")
        assert resp.status_code == 400
