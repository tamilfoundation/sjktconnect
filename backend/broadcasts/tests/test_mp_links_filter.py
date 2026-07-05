"""Tests for the `linkify_mps` template filter.

Covers the analyst-prose pattern the user flagged 2026-07-05:
"engage with their local MPs, such as YB ... (P050 Jelutong) or
Datuk ... (P148 Ayer Hitam)" -- both parenthetical spans should
render as anchors to the constituency page.
"""

from django.template import Context, Template
from django.test import TestCase

from schools.models import Constituency


class LinkifyMPsFilterTest(TestCase):
    def setUp(self):
        self.jelutong = Constituency.objects.create(
            code="P050", name="Jelutong", state="Pulau Pinang",
        )
        self.ayer_hitam = Constituency.objects.create(
            code="P148", name="Ayer Hitam", state="Johor",
        )

    def _render(self, body: str, ctx: dict) -> str:
        return Template("{% load mp_links %}" + body).render(Context(ctx))

    def test_user_example_both_mps_linked(self):
        text = (
            "engage with their local MPs, such as YB Tuan Sanisvara "
            "Nethaji Rayer a/l Rajaji (P050 Jelutong) or Datuk Seri "
            "Ir. Dr. Wee Ka Siong (P148 Ayer Hitam), on constituency-"
            "specific school needs."
        )
        out = self._render("{{ t|linkify_mps }}", {"t": text})
        self.assertIn(
            '<a href="https://tamilschool.org/en/constituency/P050"',
            out,
        )
        self.assertIn("P050 Jelutong</a>", out)
        self.assertIn(
            '<a href="https://tamilschool.org/en/constituency/P148"',
            out,
        )
        self.assertIn("P148 Ayer Hitam</a>", out)
        # MP names stay plain-text -- we don't link them.
        self.assertIn("YB Tuan Sanisvara Nethaji Rayer a/l Rajaji", out)
        # Parens are preserved around the anchor.
        self.assertIn("Rajaji (<a", out)
        self.assertIn("Siong (<a", out)

    def test_unknown_code_stays_plain_text(self):
        # P999 doesn't exist -- must not become a broken link.
        text = "some MP (P999 Bogusville) speaking"
        out = self._render("{{ t|linkify_mps }}", {"t": text})
        self.assertNotIn("<a ", out)
        self.assertIn("(P999 Bogusville)", out)

    def test_locale_argument_routes_link(self):
        text = "the MP (P050 Jelutong)"
        out = self._render('{{ t|linkify_mps:"ta" }}', {"t": text})
        self.assertIn("/ta/constituency/P050", out)

    def test_empty_and_none_pass_through(self):
        self.assertEqual(self._render("{{ t|linkify_mps }}", {"t": ""}), "")
        self.assertEqual(self._render("{{ t|linkify_mps }}", {"t": None}), "None")

    def test_html_in_source_text_is_escaped(self):
        # If an analyst somehow produces raw HTML it must be escaped --
        # never render user/model-provided angle brackets verbatim.
        text = "<script>x</script> and (P050 Jelutong)"
        out = self._render("{{ t|linkify_mps }}", {"t": text})
        self.assertNotIn("<script>", out)
        self.assertIn("&lt;script&gt;", out)
        # The MP link is still injected.
        self.assertIn("/constituency/P050", out)

    def test_multiple_same_code_all_get_linked(self):
        text = "MP A (P050 Jelutong) and MP B again (P050 Jelutong)"
        out = self._render("{{ t|linkify_mps }}", {"t": text})
        self.assertEqual(out.count('href="https://tamilschool.org/en/constituency/P050"'), 2)
