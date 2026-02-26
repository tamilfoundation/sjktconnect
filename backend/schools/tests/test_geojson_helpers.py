"""Tests for GeoJSON helper functions (Sprint 1.1)."""

from django.test import TestCase

from schools.api.geojson import to_feature, to_feature_collection


SAMPLE_WKT = "POLYGON ((102.89 2.68, 102.79 2.80, 102.71 2.82, 102.89 2.68))"


class ToFeatureTest(TestCase):
    def test_valid_polygon(self):
        feature = to_feature(SAMPLE_WKT, {"code": "P140", "name": "Segamat"})
        assert feature is not None
        assert feature["type"] == "Feature"
        assert feature["geometry"]["type"] == "Polygon"
        assert len(feature["geometry"]["coordinates"]) > 0
        assert feature["properties"]["code"] == "P140"

    def test_multipolygon_wkt(self):
        wkt = "MULTIPOLYGON (((0 0, 1 0, 1 1, 0 0)), ((2 2, 3 2, 3 3, 2 2)))"
        feature = to_feature(wkt, {"code": "P001"})
        assert feature is not None
        assert feature["geometry"]["type"] == "MultiPolygon"

    def test_invalid_wkt_returns_none(self):
        feature = to_feature("NOT VALID WKT", {"code": "P001"})
        assert feature is None

    def test_empty_string_returns_none(self):
        feature = to_feature("", {"code": "P001"})
        assert feature is None


class ToFeatureCollectionTest(TestCase):
    def test_wraps_features(self):
        features = [
            {"type": "Feature", "geometry": {}, "properties": {}},
            {"type": "Feature", "geometry": {}, "properties": {}},
        ]
        fc = to_feature_collection(features)
        assert fc["type"] == "FeatureCollection"
        assert len(fc["features"]) == 2

    def test_empty_list(self):
        fc = to_feature_collection([])
        assert fc["type"] == "FeatureCollection"
        assert len(fc["features"]) == 0
