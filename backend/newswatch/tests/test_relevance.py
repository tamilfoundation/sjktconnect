"""Tests for Sprint 24 task #1a — news triage relevance fix.

Covers:
- DOMAIN_BLOCKLIST + is_blocklisted_url helper
- analyse_pending_articles short-circuits blocklisted URLs without Gemini
- reject_blocklisted writes the expected REJECTED state
- ANALYSIS_PROMPT carries the tightened relevance-scale wording
- Regression: the 4 known-bad April 2026 URLs all hit the blocklist
"""

from unittest.mock import patch, MagicMock
from django.test import TestCase

from newswatch.models import NewsArticle
from newswatch.services.news_analyser import (
    ANALYSIS_PROMPT,
    DOMAIN_BLOCKLIST,
    analyse_pending_articles,
    is_blocklisted_url,
    reject_blocklisted,
)


class IsBlocklistedUrlTest(TestCase):
    def test_edgeprop_blocklisted(self):
        self.assertTrue(is_blocklisted_url("https://www.edgeprop.my/listing/abc"))
        self.assertTrue(is_blocklisted_url("https://edgeprop.my/listing/abc"))
        self.assertTrue(is_blocklisted_url("http://edgeprop.my/"))

    def test_propertyguru_blocklisted(self):
        self.assertTrue(is_blocklisted_url("https://www.propertyguru.com.my/listing/123"))

    def test_iproperty_blocklisted(self):
        self.assertTrue(is_blocklisted_url("https://www.iproperty.com.my/x"))

    def test_mudah_blocklisted(self):
        self.assertTrue(is_blocklisted_url("https://www.mudah.my/listing/123"))

    def test_news_site_not_blocklisted(self):
        self.assertFalse(is_blocklisted_url("https://www.bernama.com/news/123"))
        self.assertFalse(is_blocklisted_url("https://themalaysiapress.com/article"))
        self.assertFalse(is_blocklisted_url("https://www.thestar.com.my/news"))

    def test_empty_url_not_blocklisted(self):
        self.assertFalse(is_blocklisted_url(""))
        self.assertFalse(is_blocklisted_url(None))

    def test_malformed_url_not_blocklisted(self):
        # Should not raise; just returns False.
        self.assertFalse(is_blocklisted_url("not a url"))
        self.assertFalse(is_blocklisted_url("///"))

    def test_subdomain_not_blocklisted(self):
        # Strict host match — adjacent subdomains don't auto-blocklist.
        # If a real classifieds subdomain emerges, add it explicitly.
        self.assertFalse(is_blocklisted_url("https://api.edgeprop.my/v1/foo"))

    def test_known_bad_april_2026_urls_all_blocklisted(self):
        """Regression: the 4 specific April 2026 URLs from the 2026-05-03
        audit (which leaked into the digest at relevance≥3) must all
        be auto-rejected by the blocklist.
        """
        known_bad = [
            "https://www.edgeprop.my/listing/rental/3947547/selangor/kapar_/industrial/factory-warehouse/kiip-kapar-etp-semi-d-cluster-factory",
            "https://www.edgeprop.my/listing/rental/3947470/johor/kulai/landed/terracehouse/kulai-ioi-piccolo-house-single-storey-terrace",
            "https://www.edgeprop.my/listing/rental/3947296/mirai-residences-for-rent-by-jane-ng",
            "https://www.edgeprop.my/listing/rental/3947295/somewhere",
        ]
        for url in known_bad:
            self.assertTrue(
                is_blocklisted_url(url),
                f"Expected {url} to be blocklisted but it wasn't"
            )


class DomainBlocklistTest(TestCase):
    def test_contents(self):
        """The blocklist matches the locked Sprint 24 decision."""
        self.assertEqual(
            DOMAIN_BLOCKLIST,
            frozenset({
                "edgeprop.my",
                "propertyguru.com.my",
                "iproperty.com.my",
                "mudah.my",
            }),
        )


class RejectBlocklistedTest(TestCase):
    def test_sets_rejected_state(self):
        article = NewsArticle.objects.create(
            url="https://www.edgeprop.my/listing/abc",
            title="Some property listing mentioning SJK(T)",
            body_text="A condo for rent near SJK(T) Bangsar.",
            status=NewsArticle.EXTRACTED,
        )

        reject_blocklisted(article)
        article.refresh_from_db()

        self.assertEqual(article.review_status, NewsArticle.REJECTED)
        self.assertEqual(article.status, NewsArticle.ANALYSED)
        self.assertEqual(article.relevance_score, 1)
        self.assertEqual(article.sentiment, "NEUTRAL")
        self.assertFalse(article.is_urgent)
        self.assertEqual(article.urgent_reason, "")
        self.assertIn("blocklist", article.ai_summary.lower())
        self.assertEqual(article.ai_raw_response, {"blocklisted_domain": True})
        self.assertEqual(article.mentioned_schools, [])


class AnalysePendingArticlesBlocklistTest(TestCase):
    @patch("newswatch.services.news_analyser.analyse_article")
    def test_blocklisted_article_skipped_without_gemini_call(self, mock_analyse):
        """Blocklisted URLs must NOT reach analyse_article (saves tokens
        and prevents leakage via auto-approve-at-≥3).
        """
        NewsArticle.objects.create(
            url="https://www.edgeprop.my/listing/abc",
            title="Real-estate ad near SJK(T)",
            body_text="A condo for rent near SJK(T) Bangsar.",
            status=NewsArticle.EXTRACTED,
        )

        result = analyse_pending_articles(batch_size=10)

        mock_analyse.assert_not_called()
        self.assertEqual(result["blocklisted"], 1)
        self.assertEqual(result["analysed"], 0)

        article = NewsArticle.objects.get(url="https://www.edgeprop.my/listing/abc")
        self.assertEqual(article.review_status, NewsArticle.REJECTED)
        self.assertEqual(article.status, NewsArticle.ANALYSED)

    @patch("newswatch.services.news_analyser.apply_analysis")
    @patch("newswatch.services.news_analyser.analyse_article")
    def test_non_blocklisted_article_still_calls_gemini(
        self, mock_analyse, mock_apply,
    ):
        """Non-blocklisted articles take the normal Gemini path."""
        mock_analyse.return_value = {"relevance_score": 4, "is_urgent": False}

        NewsArticle.objects.create(
            url="https://themalaysiapress.com/sjkt-kulai-besar-rm4m",
            title="RM4 million for SJK(T) Kulai Besar",
            body_text="A 2-page story about the redevelopment of a Tamil school.",
            status=NewsArticle.EXTRACTED,
        )

        result = analyse_pending_articles(batch_size=10)

        mock_analyse.assert_called_once()
        mock_apply.assert_called_once()
        self.assertEqual(result["analysed"], 1)
        self.assertEqual(result["blocklisted"], 0)

    @patch("newswatch.services.news_analyser.analyse_article")
    def test_mixed_batch_routes_each_correctly(self, mock_analyse):
        """A batch with both blocklisted and non-blocklisted articles
        routes each through the correct path.
        """
        mock_analyse.return_value = {"relevance_score": 4, "is_urgent": False}

        NewsArticle.objects.create(
            url="https://www.edgeprop.my/listing/aaa",
            title="Listing A",
            body_text="amenity bullet mentions SJKT.",
            status=NewsArticle.EXTRACTED,
        )
        NewsArticle.objects.create(
            url="https://www.bernama.com/article-b",
            title="Real Tamil school news",
            body_text="A genuine story.",
            status=NewsArticle.EXTRACTED,
        )
        NewsArticle.objects.create(
            url="https://www.propertyguru.com.my/listing/ccc",
            title="Listing C",
            body_text="another property listing.",
            status=NewsArticle.EXTRACTED,
        )

        # apply_analysis is the real one; mock it too to avoid DB writes
        # via the analyse path (we only want to count routing decisions).
        with patch(
            "newswatch.services.news_analyser.apply_analysis"
        ) as mock_apply:
            result = analyse_pending_articles(batch_size=10)

        self.assertEqual(result["blocklisted"], 2)
        self.assertEqual(result["analysed"], 1)
        self.assertEqual(mock_analyse.call_count, 1)
        self.assertEqual(mock_apply.call_count, 1)


class AnalysisPromptStrictRelevanceScaleTest(TestCase):
    """Sprint 24 #1a: the relevance-score guidance must explicitly teach
    Gemini that amenity-bullet or location-landmark mentions are score 1,
    not 3. Without this, real-estate listings score ≥3 and reach
    subscribers via the auto-approve path.
    """

    def test_amenity_disclaimer_present(self):
        self.assertIn("amenity bullet", ANALYSIS_PROMPT)

    def test_subject_matter_emphasis_present(self):
        self.assertIn("SUBJECT MATTER", ANALYSIS_PROMPT)

    def test_real_estate_example_present(self):
        # The prompt must call out the failure mode that bit us.
        self.assertIn("real-estate listing", ANALYSIS_PROMPT)

    def test_err_toward_lower_score_present(self):
        self.assertIn("lower score", ANALYSIS_PROMPT)
