"""Tests for outreach models (SchoolImage fields added in Sprint 8.2)."""

from django.test import TestCase

from outreach.models import SchoolImage
from schools.models import School


class SchoolImagePositionTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.school = School.objects.create(
            moe_code="JBD0050",
            name="SJK(T) LADANG BIKAM",
            short_name="SJK(T) Ladang Bikam",
            state="Johor",
            ppd="PPD Segamat",
        )

    def test_school_image_has_position_field(self):
        img = SchoolImage.objects.create(
            school=self.school,
            image_url="https://example.com/img.jpg",
            source="MANUAL",
            position=3,
        )
        self.assertEqual(img.position, 3)

    def test_school_image_ordering_by_position(self):
        SchoolImage.objects.create(
            school=self.school,
            image_url="https://example.com/b.jpg",
            source="MANUAL",
            position=2,
        )
        SchoolImage.objects.create(
            school=self.school,
            image_url="https://example.com/a.jpg",
            source="MANUAL",
            position=1,
        )
        images = list(SchoolImage.objects.filter(school=self.school))
        self.assertEqual(images[0].position, 1)
        self.assertEqual(images[1].position, 2)

    def test_school_image_default_position_is_zero(self):
        img = SchoolImage.objects.create(
            school=self.school,
            image_url="https://example.com/default.jpg",
            source="SATELLITE",
        )
        self.assertEqual(img.position, 0)

    def test_school_image_uploaded_by_nullable(self):
        img = SchoolImage.objects.create(
            school=self.school,
            image_url="https://example.com/no_uploader.jpg",
            source="MANUAL",
        )
        self.assertIsNone(img.uploaded_by)

    def test_community_source_choice(self):
        img = SchoolImage.objects.create(
            school=self.school,
            image_url="https://example.com/community.jpg",
            source="COMMUNITY",
        )
        self.assertEqual(img.source, "COMMUNITY")
        self.assertEqual(
            SchoolImage.Source(img.source).label, "Community Upload"
        )
