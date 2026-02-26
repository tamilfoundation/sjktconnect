"""Tests for GeoJSON API endpoints (Sprint 1.1)."""

from django.test import TestCase

from schools.models import Constituency, DUN


SAMPLE_WKT = "POLYGON ((102.89 2.68, 102.79 2.80, 102.71 2.82, 102.89 2.68))"
SAMPLE_WKT_2 = "POLYGON ((103.00 3.00, 103.10 3.10, 103.20 3.00, 103.00 3.00))"


class ConstituencyGeoJSONListTest(TestCase):
    def setUp(self):
        self.c1 = Constituency.objects.create(
            code="P140", name="Segamat", state="Johor",
            mp_name="Yuneswaran", mp_party="PH (PKR)",
            boundary_wkt=SAMPLE_WKT,
        )
        self.c2 = Constituency.objects.create(
            code="P141", name="Sekijang", state="Johor",
            mp_name="Zaliha", mp_party="PH (PKR)",
            boundary_wkt=SAMPLE_WKT_2,
        )
        # One constituency without boundary
        self.c3 = Constituency.objects.create(
            code="P142", name="Labis", state="Johor",
        )

    def test_returns_feature_collection(self):
        resp = self.client.get("/api/v1/constituencies/geojson/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["type"] == "FeatureCollection"
        assert len(data["features"]) == 2  # c3 has no boundary

    def test_feature_structure(self):
        resp = self.client.get("/api/v1/constituencies/geojson/")
        feature = resp.json()["features"][0]
        assert feature["type"] == "Feature"
        assert feature["geometry"]["type"] == "Polygon"
        assert "coordinates" in feature["geometry"]
        props = feature["properties"]
        assert "code" in props
        assert "name" in props
        assert "state" in props
        assert "mp_name" in props

    def test_excludes_constituencies_without_boundary(self):
        resp = self.client.get("/api/v1/constituencies/geojson/")
        codes = [f["properties"]["code"] for f in resp.json()["features"]]
        assert "P142" not in codes


class ConstituencyGeoJSONDetailTest(TestCase):
    def setUp(self):
        self.c = Constituency.objects.create(
            code="P140", name="Segamat", state="Johor",
            mp_name="Yuneswaran", mp_party="PH (PKR)",
            mp_coalition="PH", indian_population=6142,
            boundary_wkt=SAMPLE_WKT,
        )

    def test_returns_feature(self):
        resp = self.client.get("/api/v1/constituencies/P140/geojson/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["type"] == "Feature"
        assert data["geometry"]["type"] == "Polygon"
        assert data["properties"]["code"] == "P140"
        assert data["properties"]["indian_population"] == 6142

    def test_404_for_missing_constituency(self):
        resp = self.client.get("/api/v1/constituencies/P999/geojson/")
        assert resp.status_code == 404

    def test_404_for_no_boundary(self):
        Constituency.objects.create(code="P141", name="Sekijang", state="Johor")
        resp = self.client.get("/api/v1/constituencies/P141/geojson/")
        assert resp.status_code == 404


class DUNGeoJSONListTest(TestCase):
    def setUp(self):
        self.c = Constituency.objects.create(
            code="P140", name="Segamat", state="Johor",
        )
        self.d1 = DUN.objects.create(
            code="N01", name="Buloh Kasap", state="Johor",
            constituency=self.c, adun_name="Zahari", adun_party="BN (UMNO)",
            boundary_wkt=SAMPLE_WKT,
        )
        self.d2 = DUN.objects.create(
            code="N02", name="Jementah", state="Johor",
            constituency=self.c, adun_name="Ng Kor Sim", adun_party="PH (DAP)",
            boundary_wkt=SAMPLE_WKT_2,
        )
        # DUN without boundary
        self.d3 = DUN.objects.create(
            code="N03", name="Pemanis", state="Johor",
            constituency=self.c,
        )

    def test_returns_feature_collection(self):
        resp = self.client.get("/api/v1/duns/geojson/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["type"] == "FeatureCollection"
        assert len(data["features"]) == 2  # d3 has no boundary

    def test_filter_by_state(self):
        c2 = Constituency.objects.create(code="P001", name="Padang Besar", state="Perlis")
        DUN.objects.create(
            code="N01", name="Titi Tinggi", state="Perlis",
            constituency=c2, boundary_wkt=SAMPLE_WKT,
        )
        resp = self.client.get("/api/v1/duns/geojson/?state=Johor")
        data = resp.json()
        assert len(data["features"]) == 2  # Only Johor DUNs

    def test_filter_by_constituency(self):
        c2 = Constituency.objects.create(code="P141", name="Sekijang", state="Johor")
        DUN.objects.create(
            code="N03", name="Pemanis", state="Johor",
            constituency=c2, boundary_wkt=SAMPLE_WKT,
        )
        resp = self.client.get("/api/v1/duns/geojson/?constituency=P140")
        data = resp.json()
        assert len(data["features"]) == 2  # Only P140's DUNs

    def test_feature_has_constituency_info(self):
        resp = self.client.get("/api/v1/duns/geojson/")
        feature = resp.json()["features"][0]
        props = feature["properties"]
        assert "constituency_code" in props
        assert "constituency_name" in props


class DUNGeoJSONDetailTest(TestCase):
    def setUp(self):
        self.c = Constituency.objects.create(
            code="P140", name="Segamat", state="Johor",
        )
        self.d = DUN.objects.create(
            code="N01", name="Buloh Kasap", state="Johor",
            constituency=self.c, adun_name="Zahari", adun_party="BN (UMNO)",
            indian_population=2615,
            boundary_wkt=SAMPLE_WKT,
        )

    def test_returns_feature(self):
        resp = self.client.get(f"/api/v1/duns/{self.d.pk}/geojson/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["type"] == "Feature"
        assert data["properties"]["code"] == "N01"
        assert data["properties"]["indian_population"] == 2615

    def test_404_for_missing_dun(self):
        resp = self.client.get("/api/v1/duns/99999/geojson/")
        assert resp.status_code == 404

    def test_404_for_no_boundary(self):
        d2 = DUN.objects.create(
            code="N02", name="Jementah", state="Johor",
            constituency=self.c,
        )
        resp = self.client.get(f"/api/v1/duns/{d2.pk}/geojson/")
        assert resp.status_code == 404
