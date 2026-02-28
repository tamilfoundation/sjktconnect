"""Tests for the image harvester service and management command."""

from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase, override_settings

from outreach.models import SchoolImage
from outreach.services.image_harvester import (
    harvest_images_for_school,
    harvest_places_image,
    harvest_satellite_image,
)
from schools.models import School


class HarvestSatelliteImageTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.school_with_gps = School.objects.create(
            moe_code="JBD0050",
            name="SJK(T) LADANG BIKAM",
            short_name="SJK(T) Ladang Bikam",
            state="Johor",
            ppd="PPD Segamat",
            gps_lat="2.4500000",
            gps_lng="102.8100000",
        )
        cls.school_no_gps = School.objects.create(
            moe_code="AGD1234",
            name="SJK(T) LADANG SUNGAI",
            short_name="SJK(T) Ladang Sungai",
            state="Kedah",
            ppd="PPD Kulim",
        )

    @patch.dict("os.environ", {"GOOGLE_MAPS_API_KEY": "test-key-123"})
    def test_satellite_image_created_with_gps(self):
        img = harvest_satellite_image(self.school_with_gps)
        assert img is not None
        assert img.source == SchoolImage.Source.SATELLITE
        assert img.is_primary is True
        assert img.width == 640
        assert img.height == 400
        assert "center=2.4500000,102.8100000" in img.image_url
        assert "maptype=satellite" in img.image_url
        assert "test-key-123" in img.image_url
        assert img.attribution == "Google Maps"

    @patch.dict("os.environ", {"GOOGLE_MAPS_API_KEY": "test-key-123"})
    def test_satellite_returns_none_without_gps(self):
        img = harvest_satellite_image(self.school_no_gps)
        assert img is None

    @patch.dict("os.environ", {}, clear=True)
    def test_satellite_returns_none_without_api_key(self):
        img = harvest_satellite_image(self.school_with_gps)
        assert img is None

    @patch.dict("os.environ", {"GOOGLE_MAPS_API_KEY": "test-key-123"})
    def test_satellite_update_or_create_is_idempotent(self):
        img1 = harvest_satellite_image(self.school_with_gps)
        img2 = harvest_satellite_image(self.school_with_gps)
        assert img1.pk == img2.pk
        assert SchoolImage.objects.filter(school=self.school_with_gps).count() == 1

    @patch.dict("os.environ", {"GOOGLE_MAPS_API_KEY": "test-key-123"})
    def test_satellite_not_primary_if_primary_exists(self):
        # Create an existing primary image
        SchoolImage.objects.create(
            school=self.school_with_gps,
            image_url="https://example.com/photo.jpg",
            source=SchoolImage.Source.PLACES,
            is_primary=True,
        )
        img = harvest_satellite_image(self.school_with_gps)
        assert img is not None
        assert img.is_primary is False


class HarvestPlacesImageTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.school = School.objects.create(
            moe_code="JBD0050",
            name="SJK(T) LADANG BIKAM",
            short_name="SJK(T) Ladang Bikam",
            state="Johor",
            ppd="PPD Segamat",
            gps_lat="2.4500000",
            gps_lng="102.8100000",
        )

    @patch("outreach.services.image_harvester.requests.get")
    @patch.dict("os.environ", {"GOOGLE_MAPS_API_KEY": "test-key-123"})
    def test_places_image_created_on_success(self, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.raise_for_status = lambda: None
        mock_get.return_value.json.return_value = {
            "candidates": [
                {
                    "name": "SJK(T) Ladang Bikam",
                    "place_id": "ChIJ123",
                    "photos": [
                        {
                            "photo_reference": "PHOTO_REF_ABC",
                            "html_attributions": ["Photo by Google"],
                        }
                    ],
                }
            ]
        }

        img = harvest_places_image(self.school)
        assert img is not None
        assert img.source == SchoolImage.Source.PLACES
        assert img.is_primary is True
        assert "PHOTO_REF_ABC" in img.image_url
        assert img.photo_reference == "PHOTO_REF_ABC"
        assert img.attribution == "Photo by Google"

    @patch("outreach.services.image_harvester.requests.get")
    @patch.dict("os.environ", {"GOOGLE_MAPS_API_KEY": "test-key-123"})
    def test_places_returns_none_no_candidates(self, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.raise_for_status = lambda: None
        mock_get.return_value.json.return_value = {"candidates": []}

        img = harvest_places_image(self.school)
        assert img is None

    @patch("outreach.services.image_harvester.requests.get")
    @patch.dict("os.environ", {"GOOGLE_MAPS_API_KEY": "test-key-123"})
    def test_places_returns_none_no_photos(self, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.raise_for_status = lambda: None
        mock_get.return_value.json.return_value = {
            "candidates": [{"name": "SJK(T) Ladang Bikam", "photos": []}]
        }

        img = harvest_places_image(self.school)
        assert img is None

    @patch("outreach.services.image_harvester.requests.get")
    @patch.dict("os.environ", {"GOOGLE_MAPS_API_KEY": "test-key-123"})
    def test_places_demotes_existing_primary(self, mock_get):
        # Create an existing primary satellite image
        sat = SchoolImage.objects.create(
            school=self.school,
            image_url="https://maps.example.com/sat.jpg",
            source=SchoolImage.Source.SATELLITE,
            is_primary=True,
        )

        mock_get.return_value.status_code = 200
        mock_get.return_value.raise_for_status = lambda: None
        mock_get.return_value.json.return_value = {
            "candidates": [
                {
                    "name": "SJK(T) Ladang Bikam",
                    "photos": [{"photo_reference": "REF_XYZ", "html_attributions": []}],
                }
            ]
        }

        img = harvest_places_image(self.school)
        assert img is not None
        assert img.is_primary is True
        sat.refresh_from_db()
        assert sat.is_primary is False

    @patch.dict("os.environ", {}, clear=True)
    def test_places_returns_none_without_api_key(self):
        img = harvest_places_image(self.school)
        assert img is None

    @patch("outreach.services.image_harvester.requests.get")
    @patch.dict("os.environ", {"GOOGLE_MAPS_API_KEY": "test-key-123"})
    def test_places_handles_request_error(self, mock_get):
        import requests

        mock_get.side_effect = requests.RequestException("Connection error")
        img = harvest_places_image(self.school)
        assert img is None


class HarvestImagesForSchoolTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.school = School.objects.create(
            moe_code="JBD0050",
            name="SJK(T) LADANG BIKAM",
            short_name="SJK(T) Ladang Bikam",
            state="Johor",
            ppd="PPD Segamat",
            gps_lat="2.4500000",
            gps_lng="102.8100000",
        )

    @patch("outreach.services.image_harvester.requests.get")
    @patch.dict("os.environ", {"GOOGLE_MAPS_API_KEY": "test-key-123"})
    def test_both_sources_by_default(self, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.raise_for_status = lambda: None
        mock_get.return_value.json.return_value = {
            "candidates": [
                {
                    "name": "Test",
                    "photos": [{"photo_reference": "REF", "html_attributions": []}],
                }
            ]
        }

        results = harvest_images_for_school(self.school)
        assert len(results) == 2
        sources = {r.source for r in results}
        assert SchoolImage.Source.SATELLITE in sources
        assert SchoolImage.Source.PLACES in sources

    @patch.dict("os.environ", {"GOOGLE_MAPS_API_KEY": "test-key-123"})
    def test_satellite_only_source(self):
        results = harvest_images_for_school(self.school, sources=["satellite"])
        assert len(results) == 1
        assert results[0].source == SchoolImage.Source.SATELLITE


class HarvestSchoolImagesCommandTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.school1 = School.objects.create(
            moe_code="JBD0050",
            name="SJK(T) LADANG BIKAM",
            short_name="SJK(T) Ladang Bikam",
            state="Johor",
            ppd="PPD Segamat",
            gps_lat="2.4500000",
            gps_lng="102.8100000",
        )
        cls.school2 = School.objects.create(
            moe_code="AGD1234",
            name="SJK(T) LADANG SUNGAI",
            short_name="SJK(T) Ladang Sungai",
            state="Kedah",
            ppd="PPD Kulim",
            gps_lat="5.3600000",
            gps_lng="100.5500000",
        )

    def test_dry_run_no_images_created(self):
        out = StringIO()
        call_command("harvest_school_images", "--dry-run", stdout=out)
        assert SchoolImage.objects.count() == 0
        output = out.getvalue()
        assert "JBD0050" in output
        assert "Dry run complete" in output

    def test_dry_run_with_state_filter(self):
        out = StringIO()
        call_command("harvest_school_images", "--dry-run", "--state", "Johor", stdout=out)
        output = out.getvalue()
        assert "JBD0050" in output
        assert "AGD1234" not in output

    def test_dry_run_with_limit(self):
        out = StringIO()
        call_command("harvest_school_images", "--dry-run", "--limit", "1", stdout=out)
        output = out.getvalue()
        assert "Schools to process: 1" in output

    @patch.dict("os.environ", {"GOOGLE_MAPS_API_KEY": "test-key-123"})
    def test_harvest_satellite_creates_images(self):
        out = StringIO()
        call_command(
            "harvest_school_images", "--source", "satellite", "--limit", "2",
            stdout=out,
        )
        assert SchoolImage.objects.count() == 2
        assert "Done. 2 images created/updated" in out.getvalue()

    @patch.dict("os.environ", {"GOOGLE_MAPS_API_KEY": "test-key-123"})
    def test_harvest_with_state_filter(self):
        out = StringIO()
        call_command(
            "harvest_school_images", "--source", "satellite", "--state", "Johor",
            stdout=out,
        )
        assert SchoolImage.objects.filter(school__state="Johor").count() == 1
        assert SchoolImage.objects.filter(school__state="Kedah").count() == 0
