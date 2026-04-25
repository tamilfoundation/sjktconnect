"""Tests for the image harvester service and management command.

Sprint 13: harvester now downloads bytes and writes to image_file (not
image_url). Tests updated accordingly.
"""

from io import StringIO
from unittest.mock import patch, MagicMock

from django.core.management import call_command
from django.test import TestCase

from outreach.models import SchoolImage
from outreach.services.image_harvester import (
    harvest_images_for_school,
    harvest_places_image,
    harvest_places_images,
    harvest_satellite_image,
)
from schools.models import School


def _mock_byte_response(payload: bytes = b"\x89PNG\r\n\x1a\n" + b"x" * 100):
    """Build a fake requests.Response that yields the given bytes via iter_content."""
    resp = MagicMock()
    resp.status_code = 200
    resp.raise_for_status = lambda: None
    resp.iter_content = lambda chunk_size=64 * 1024: [payload]
    return resp


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

    @patch("outreach.services.image_harvester.requests.get")
    @patch.dict("os.environ", {"GOOGLE_MAPS_API_KEY": "test-key-123"})
    def test_satellite_image_created_with_gps(self, mock_get):
        mock_get.return_value = _mock_byte_response()
        img = harvest_satellite_image(self.school_with_gps)
        assert img is not None
        assert img.source == SchoolImage.Source.SATELLITE
        assert img.is_primary is True
        assert img.width == 640
        assert img.height == 400
        assert img.image_file  # bytes uploaded
        assert img.image_url == ""  # legacy field unset for new harvests
        assert img.attribution == "Google Maps"

    @patch("outreach.services.image_harvester.requests.get")
    @patch.dict("os.environ", {"GOOGLE_MAPS_API_KEY": "test-key-123"})
    def test_satellite_returns_none_without_gps(self, mock_get):
        img = harvest_satellite_image(self.school_no_gps)
        assert img is None
        mock_get.assert_not_called()

    @patch.dict("os.environ", {}, clear=True)
    def test_satellite_returns_none_without_api_key(self):
        img = harvest_satellite_image(self.school_with_gps)
        assert img is None

    @patch("outreach.services.image_harvester.requests.get")
    @patch.dict("os.environ", {"GOOGLE_MAPS_API_KEY": "test-key-123"})
    def test_satellite_replaces_existing(self, mock_get):
        """Two harvest calls produce one SATELLITE row (clean re-harvest)."""
        mock_get.return_value = _mock_byte_response()
        img1 = harvest_satellite_image(self.school_with_gps)
        img2 = harvest_satellite_image(self.school_with_gps)
        assert img1 is not None and img2 is not None
        # Different rows (delete + create), but only one SATELLITE per school
        assert SchoolImage.objects.filter(
            school=self.school_with_gps, source=SchoolImage.Source.SATELLITE,
        ).count() == 1

    @patch("outreach.services.image_harvester.requests.get")
    @patch.dict("os.environ", {"GOOGLE_MAPS_API_KEY": "test-key-123"})
    def test_satellite_not_primary_if_primary_exists(self, mock_get):
        # Create an existing primary image
        SchoolImage.objects.create(
            school=self.school_with_gps,
            image_url="https://example.com/photo.jpg",
            source=SchoolImage.Source.PLACES,
            is_primary=True,
        )
        mock_get.return_value = _mock_byte_response()
        img = harvest_satellite_image(self.school_with_gps)
        assert img is not None
        assert img.is_primary is False

    @patch("outreach.services.image_harvester.requests.get")
    @patch.dict("os.environ", {"GOOGLE_MAPS_API_KEY": "test-key-123"})
    def test_satellite_returns_none_on_download_failure(self, mock_get):
        import requests as r
        mock_get.side_effect = r.RequestException("boom")
        img = harvest_satellite_image(self.school_with_gps)
        assert img is None


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
    @patch("outreach.services.image_harvester.requests.post")
    @patch.dict("os.environ", {"GOOGLE_MAPS_API_KEY": "test-key-123"})
    def test_places_image_created_on_success(self, mock_post, mock_get):
        mock_post.return_value.status_code = 200
        mock_post.return_value.raise_for_status = lambda: None
        mock_post.return_value.json.return_value = {
            "places": [
                {
                    "id": "ChIJ123",
                    "displayName": {"text": "SJK(T) Ladang Bikam"},
                    "photos": [
                        {
                            "name": "places/ChIJ123/photos/PHOTO_REF_ABC",
                            "widthPx": 640,
                            "heightPx": 480,
                            "authorAttributions": [{"displayName": "Photo by Google"}],
                        }
                    ],
                }
            ]
        }
        mock_get.return_value = _mock_byte_response(b"\xff\xd8\xff\xe0" + b"x" * 100)

        img = harvest_places_image(self.school)
        assert img is not None
        assert img.source == SchoolImage.Source.PLACES
        assert img.is_primary is True
        assert img.image_file  # bytes uploaded
        assert img.image_url == ""
        assert img.photo_reference == "places/ChIJ123/photos/PHOTO_REF_ABC"
        assert img.attribution == "Photo by Google"

    @patch("outreach.services.image_harvester.requests.post")
    @patch.dict("os.environ", {"GOOGLE_MAPS_API_KEY": "test-key-123"})
    def test_places_returns_none_no_candidates(self, mock_post):
        mock_post.return_value.status_code = 200
        mock_post.return_value.raise_for_status = lambda: None
        mock_post.return_value.json.return_value = {"places": []}

        img = harvest_places_image(self.school)
        assert img is None

    @patch("outreach.services.image_harvester.requests.post")
    @patch.dict("os.environ", {"GOOGLE_MAPS_API_KEY": "test-key-123"})
    def test_places_returns_none_no_photos(self, mock_post):
        mock_post.return_value.status_code = 200
        mock_post.return_value.raise_for_status = lambda: None
        mock_post.return_value.json.return_value = {
            "places": [{"id": "ChIJ123", "displayName": {"text": "X"}, "photos": []}]
        }

        img = harvest_places_image(self.school)
        assert img is None

    @patch("outreach.services.image_harvester.requests.get")
    @patch("outreach.services.image_harvester.requests.post")
    @patch.dict("os.environ", {"GOOGLE_MAPS_API_KEY": "test-key-123"})
    def test_places_demotes_existing_primary(self, mock_post, mock_get):
        sat = SchoolImage.objects.create(
            school=self.school,
            image_url="https://maps.example.com/sat.jpg",
            source=SchoolImage.Source.SATELLITE,
            is_primary=True,
        )

        mock_post.return_value.status_code = 200
        mock_post.return_value.raise_for_status = lambda: None
        mock_post.return_value.json.return_value = {
            "places": [
                {
                    "id": "ChIJ123",
                    "photos": [
                        {
                            "name": "places/ChIJ123/photos/REF_XYZ",
                            "widthPx": 640,
                            "authorAttributions": [],
                        }
                    ],
                }
            ]
        }
        mock_get.return_value = _mock_byte_response()

        img = harvest_places_image(self.school)
        assert img is not None
        assert img.is_primary is True
        sat.refresh_from_db()
        assert sat.is_primary is False

    @patch.dict("os.environ", {}, clear=True)
    def test_places_returns_none_without_api_key(self):
        img = harvest_places_image(self.school)
        assert img is None

    @patch("outreach.services.image_harvester.requests.post")
    @patch.dict("os.environ", {"GOOGLE_MAPS_API_KEY": "test-key-123"})
    def test_places_handles_search_request_error(self, mock_post):
        import requests
        mock_post.side_effect = requests.RequestException("Connection error")
        img = harvest_places_image(self.school)
        assert img is None

    @patch("outreach.services.image_harvester.requests.get")
    @patch("outreach.services.image_harvester.requests.post")
    @patch.dict("os.environ", {"GOOGLE_MAPS_API_KEY": "test-key-123"})
    def test_places_skips_failed_byte_downloads(self, mock_post, mock_get):
        """If download_bytes fails for a photo, skip that photo not the whole batch."""
        mock_post.return_value.status_code = 200
        mock_post.return_value.raise_for_status = lambda: None
        mock_post.return_value.json.return_value = {
            "places": [
                {
                    "id": "ChIJ123",
                    "photos": [
                        {"name": "places/ChIJ123/photos/REF1", "widthPx": 640, "authorAttributions": []},
                        {"name": "places/ChIJ123/photos/REF2", "widthPx": 640, "authorAttributions": []},
                    ],
                }
            ]
        }

        # First download fails, second succeeds
        import requests as r
        mock_get.side_effect = [r.RequestException("dead"), _mock_byte_response()]

        results = harvest_places_images(self.school)
        assert len(results) == 1
        assert results[0].photo_reference == "places/ChIJ123/photos/REF2"


class HarvestPlacesImagesTest(TestCase):
    """Tests for the new harvest_places_images (plural) function."""

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
    @patch("outreach.services.image_harvester.requests.post")
    @patch.dict("os.environ", {"GOOGLE_MAPS_API_KEY": "fake-key"})
    def test_harvests_up_to_3_photos(self, mock_post, mock_get):
        mock_post.return_value.status_code = 200
        mock_post.return_value.raise_for_status = lambda: None
        mock_post.return_value.json.return_value = {
            "places": [
                {
                    "id": "ChIJ123",
                    "photos": [
                        {"name": f"places/ChIJ123/photos/REF_{i}", "widthPx": 640, "authorAttributions": []}
                        for i in range(4)
                    ],
                }
            ]
        }
        mock_get.return_value = _mock_byte_response()

        results = harvest_places_images(self.school)
        assert len(results) == 3
        assert results[0].is_primary is True
        assert results[1].is_primary is False
        assert results[2].is_primary is False

    @patch("outreach.services.image_harvester.requests.get")
    @patch("outreach.services.image_harvester.requests.post")
    @patch.dict("os.environ", {"GOOGLE_MAPS_API_KEY": "fake-key"})
    def test_clears_old_places_images_before_harvest(self, mock_post, mock_get):
        SchoolImage.objects.create(
            school=self.school,
            image_url="https://old.example.com/photo.jpg",
            source=SchoolImage.Source.PLACES,
            is_primary=True,
            photo_reference="OLD_REF",
        )

        mock_post.return_value.status_code = 200
        mock_post.return_value.raise_for_status = lambda: None
        mock_post.return_value.json.return_value = {
            "places": [
                {
                    "id": "ChIJ123",
                    "photos": [
                        {"name": "places/ChIJ123/photos/NEW_REF", "widthPx": 640, "authorAttributions": []}
                    ],
                }
            ]
        }
        mock_get.return_value = _mock_byte_response()

        results = harvest_places_images(self.school)
        assert len(results) == 1
        assert results[0].photo_reference == "places/ChIJ123/photos/NEW_REF"
        assert not SchoolImage.objects.filter(photo_reference="OLD_REF").exists()

    @patch("outreach.services.image_harvester._get_api_key", return_value="")
    def test_returns_empty_when_no_api_key(self, _mock_key):
        results = harvest_places_images(self.school)
        assert results == []

    @patch("outreach.services.image_harvester.requests.post")
    @patch.dict("os.environ", {"GOOGLE_MAPS_API_KEY": "fake-key"})
    def test_returns_empty_when_no_candidates(self, mock_post):
        mock_post.return_value.status_code = 200
        mock_post.return_value.raise_for_status = lambda: None
        mock_post.return_value.json.return_value = {"places": []}

        results = harvest_places_images(self.school)
        assert results == []


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
    @patch("outreach.services.image_harvester.requests.post")
    @patch.dict("os.environ", {"GOOGLE_MAPS_API_KEY": "test-key-123"})
    def test_both_sources_by_default(self, mock_post, mock_get):
        mock_post.return_value.status_code = 200
        mock_post.return_value.raise_for_status = lambda: None
        mock_post.return_value.json.return_value = {
            "places": [
                {
                    "id": "ChIJ123",
                    "photos": [{"name": "places/ChIJ123/photos/REF", "widthPx": 640, "authorAttributions": []}],
                }
            ]
        }
        mock_get.return_value = _mock_byte_response()

        results = harvest_images_for_school(self.school)
        assert len(results) == 2
        sources = {r.source for r in results}
        assert SchoolImage.Source.SATELLITE in sources
        assert SchoolImage.Source.PLACES in sources

    @patch("outreach.services.image_harvester.requests.get")
    @patch.dict("os.environ", {"GOOGLE_MAPS_API_KEY": "test-key-123"})
    def test_satellite_only_source(self, mock_get):
        mock_get.return_value = _mock_byte_response()
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

    @patch("outreach.services.image_harvester.requests.get")
    @patch.dict("os.environ", {"GOOGLE_MAPS_API_KEY": "test-key-123"})
    def test_harvest_satellite_creates_images(self, mock_get):
        mock_get.return_value = _mock_byte_response()
        out = StringIO()
        call_command(
            "harvest_school_images", "--source", "satellite", "--limit", "2",
            stdout=out,
        )
        assert SchoolImage.objects.count() == 2
        assert "Done. 2 images created/updated" in out.getvalue()

    @patch("outreach.services.image_harvester.requests.get")
    @patch.dict("os.environ", {"GOOGLE_MAPS_API_KEY": "test-key-123"})
    def test_harvest_with_state_filter(self, mock_get):
        mock_get.return_value = _mock_byte_response()
        out = StringIO()
        call_command(
            "harvest_school_images", "--source", "satellite", "--state", "Johor",
            stdout=out,
        )
        assert SchoolImage.objects.filter(school__state="Johor").count() == 1
        assert SchoolImage.objects.filter(school__state="Kedah").count() == 0
