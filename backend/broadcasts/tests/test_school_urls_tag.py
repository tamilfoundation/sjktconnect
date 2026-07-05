"""Tests for the `school_url` template tag.

Guards the coherence between the tag output and the frontend's
`schoolPath()` (frontend/lib/urls.ts). The Python side reuses
`schools.services.revalidation.build_school_slug` which already mirrors
the JS logic — these tests lock in that the URL shape is what the
frontend expects so emails don't 301 through the legacy path.
"""

from django.template import Context, Template
from django.test import TestCase

from schools.models import Constituency, School


class SchoolUrlTagTest(TestCase):
    def setUp(self):
        self.c = Constituency.objects.create(
            code="P140", name="Segamat", state="Johor",
        )
        self.school = School.objects.create(
            moe_code="JBD0050",
            name="Sekolah Jenis Kebangsaan (Tamil) Ladang Bikam",
            short_name="SJK(T) Ladang Bikam",
            state="Johor",
            city="Segamat",
            constituency=self.c,
        )

    def _render(self, template_body: str, ctx: dict) -> str:
        return Template("{% load school_urls %}" + template_body).render(Context(ctx))

    def test_url_matches_frontend_slug_shape(self):
        html = self._render("{% school_url school %}", {"school": self.school})
        # Expected shape: /<locale>/school/<name>-<city>-<moe-lc>
        self.assertEqual(
            html,
            "https://tamilschool.org/en/school/ladang-bikam-segamat-jbd0050",
        )

    def test_locale_override(self):
        html = self._render(
            "{% school_url school 'ta' %}", {"school": self.school},
        )
        self.assertIn("/ta/school/ladang-bikam-segamat-jbd0050", html)

    def test_missing_city_still_returns_valid_url(self):
        self.school.city = ""
        self.school.save()
        html = self._render("{% school_url school %}", {"school": self.school})
        # City part drops out, moe_code still present at the end.
        self.assertEqual(
            html,
            "https://tamilschool.org/en/school/ladang-bikam-jbd0050",
        )

    def test_sjkt_prefix_stripped(self):
        """SJK(T) prefix must be dropped from the name part."""
        html = self._render("{% school_url school %}", {"school": self.school})
        self.assertNotIn("sjk-t", html)
        self.assertNotIn("sjkt", html)

    def test_output_is_all_lowercase(self):
        html = self._render("{% school_url school %}", {"school": self.school})
        # Strip protocol so we only check the path.
        path = html.split("://", 1)[1]
        self.assertEqual(path, path.lower())
