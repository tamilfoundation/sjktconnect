"""Tests for the urgency classifier: two-gate prompt + verification pass.

Covers:
- First-pass classifier on 1 positive + 6 negative article fixtures
- Second-pass verifier downgrading a false-positive first pass
- Verifier confirming a true-positive first pass
- Verifier failure (API error) leaves the first-pass verdict intact
"""

import json
from unittest.mock import MagicMock, patch

from django.test import TestCase

from newswatch.models import NewsArticle
from newswatch.services.news_analyser import (
    _verify_urgency,
    analyse_article,
)


def _mock_response(data):
    """Build a fake genai response whose .text is JSON-encoded data."""
    resp = MagicMock()
    resp.text = json.dumps(data)
    return resp


def _make_article(title, body):
    return NewsArticle.objects.create(
        url=f"https://example.com/{hash(title) & 0xffff}",
        title=title,
        source_name="Test Source",
        body_text=body,
        status=NewsArticle.EXTRACTED,
    )


NEGATIVE_FIXTURES = [
    {
        "label": "heat_policy_announcement",
        "title": (
            "Tutup Sekolah Jika Suhu Lebih 37 Selsius 3 Hari Berturut - KPM"
        ),
        "body": (
            "KUALA LUMPUR - Pengurusan sekolah dibenarkan menutup sekolah "
            "buat sementara waktu jika suhu melebihi 37 darjah Celsius "
            "selama tiga hari berturut-turut. Langkah itu sebahagian "
            "daripada garis panduan KPM sejak 2023."
        ),
    },
    {
        "label": "rebuild_announcement",
        "title": "SJK(T) Gopeng to be rebuilt under RM14.5M project",
        "body": (
            "SJK(T) Gopeng will undergo redevelopment under an RM14.5 "
            "million project to replace its 80-year-old dilapidated "
            "building. The project begins end of 2026."
        ),
    },
    {
        "label": "enrolment_trend",
        "title": "Tamil school enrolment dropping for 5th year",
        "body": (
            "Enrolment at SJK(T) schools nationwide has declined 3% "
            "annually for five consecutive years, according to MoE data."
        ),
    },
    {
        "label": "ministry_visit",
        "title": "Deputy Minister visits SJK(T) Kerajaan",
        "body": (
            "The Deputy Education Minister visited SJK(T) Kerajaan today "
            "and announced routine funding for annual repairs."
        ),
    },
    {
        "label": "award_controversy",
        "title": "Award controversy at Tamil school",
        "body": (
            "A dispute over a recent award given to a Tamil school has "
            "drawn public commentary on social media."
        ),
    },
    {
        "label": "general_policy",
        "title": "MoE announces general curriculum review",
        "body": (
            "The Ministry of Education is reviewing the primary school "
            "curriculum across all school types."
        ),
    },
]

POSITIVE_FIXTURE = {
    "label": "imminent_closure",
    "title": "SJK(T) Ladang Bikam will close on 1 June",
    "body": (
        "SJK(T) Ladang Bikam will officially close on 1 June 2026. "
        "Parents have until 15 May to file appeals with the state "
        "education department. Approximately 80 students will be "
        "reassigned to nearby schools."
    ),
}


class UrgencyClassifierFirstPassTest(TestCase):
    """First-pass prompt should mark only genuine crises as urgent.

    These tests exercise the integration between analyse_article and
    _validate_response. The genai client is mocked to return whatever
    verdict the test wants — they verify the wiring, not Gemini's
    actual classification behaviour (that's an LLM eval, not a unit test).
    """

    def _mock_with_verdicts(self, first_pass, second_pass=None):
        """Return a mock genai client that replies to up to 2 calls."""
        client = MagicMock()
        responses = [_mock_response(first_pass)]
        if second_pass is not None:
            responses.append(_mock_response(second_pass))
        client.models.generate_content.side_effect = responses
        return client

    @patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"})
    @patch("newswatch.services.news_analyser.genai")
    def test_positive_fixture_stays_urgent_when_verifier_confirms(self, mock_genai):
        article = _make_article(POSITIVE_FIXTURE["title"], POSITIVE_FIXTURE["body"])
        mock_genai.Client.return_value = self._mock_with_verdicts(
            first_pass={
                "relevance_score": 5,
                "sentiment": "NEGATIVE",
                "summary": "SJK(T) Ladang Bikam closing 1 June; appeal deadline 15 May.",
                "mentioned_schools": [{"name": "SJK(T) Ladang Bikam", "moe_code": ""}],
                "is_urgent": True,
                "urgent_reason": "Named school closing in 30 days with appeal window.",
            },
            second_pass={"confirmed": True, "reason": "Imminent closure with action window."},
        )

        result = analyse_article(article)

        self.assertIsNotNone(result)
        self.assertTrue(result["is_urgent"])
        self.assertIn("appeal", result["urgent_reason"].lower())

    @patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"})
    @patch("newswatch.services.news_analyser.genai")
    def test_negative_fixtures_stay_not_urgent(self, mock_genai):
        """When first pass correctly returns is_urgent=False, no verification runs."""
        for fx in NEGATIVE_FIXTURES:
            with self.subTest(label=fx["label"]):
                article = _make_article(fx["title"], fx["body"])
                mock_genai.Client.return_value = self._mock_with_verdicts(
                    first_pass={
                        "relevance_score": 3,
                        "sentiment": "NEUTRAL",
                        "summary": f"Summary for {fx['label']}.",
                        "mentioned_schools": [],
                        "is_urgent": False,
                        "urgent_reason": "",
                    },
                )
                result = analyse_article(article)
                self.assertIsNotNone(result)
                self.assertFalse(result["is_urgent"])
                self.assertEqual(result["urgent_reason"], "")


class UrgencyVerificationTest(TestCase):
    """Second-pass verifier semantics."""

    def _article(self):
        return _make_article(
            "Heat closure policy permits HMs to shut schools when hot",
            "Policy reiteration from 2023; nothing new.",
        )

    def test_first_pass_true_verifier_false_downgrades(self):
        analysis = {
            "is_urgent": True,
            "urgent_reason": "Mentions school closure.",
            "summary": "Policy allows closure during heatwaves.",
            "raw_response": {},
        }
        client = MagicMock()
        client.models.generate_content.return_value = _mock_response({
            "confirmed": False,
            "reason": "Permissive guideline, not an emergency.",
        })

        result = _verify_urgency(client, self._article(), analysis)

        self.assertFalse(result["is_urgent"])
        self.assertEqual(result["urgent_reason"], "")
        self.assertIn("urgent_verification", result["raw_response"])
        self.assertFalse(result["raw_response"]["urgent_verification"]["confirmed"])

    def test_first_pass_true_verifier_true_preserves(self):
        analysis = {
            "is_urgent": True,
            "urgent_reason": "SJK(T) X closing in 30 days with appeal window.",
            "summary": "Confirmed closure of SJK(T) X.",
            "raw_response": {},
        }
        client = MagicMock()
        client.models.generate_content.return_value = _mock_response({
            "confirmed": True,
            "reason": "Named school, imminent closure, action window.",
        })

        result = _verify_urgency(client, self._article(), analysis)

        self.assertTrue(result["is_urgent"])
        self.assertNotEqual(result["urgent_reason"], "")
        self.assertTrue(result["raw_response"]["urgent_verification"]["confirmed"])

    def test_first_pass_false_skips_verification(self):
        analysis = {
            "is_urgent": False,
            "urgent_reason": "",
            "summary": "Routine news.",
            "raw_response": {},
        }
        client = MagicMock()

        result = _verify_urgency(client, self._article(), analysis)

        self.assertFalse(result["is_urgent"])
        client.models.generate_content.assert_not_called()
        self.assertNotIn("urgent_verification", result["raw_response"])

    def test_verifier_api_error_keeps_first_pass_verdict(self):
        analysis = {
            "is_urgent": True,
            "urgent_reason": "Initial flag.",
            "summary": "Some summary.",
            "raw_response": {},
        }
        client = MagicMock()
        client.models.generate_content.side_effect = RuntimeError("boom")

        result = _verify_urgency(client, self._article(), analysis)

        self.assertTrue(result["is_urgent"])
        self.assertEqual(result["urgent_reason"], "Initial flag.")
