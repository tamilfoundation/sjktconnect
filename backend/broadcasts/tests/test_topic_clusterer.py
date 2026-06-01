"""Tests for Sprint 24 task #2 + #10b — topic_clusterer service."""

import json
from datetime import date
from unittest.mock import patch, Mock

from django.test import TestCase

from broadcasts.services.topic_clusterer import (
    cluster_news_articles,
    rank_and_cap_clusters,
    _materialise_clusters,
    _pick_lead_article,
    _score_cluster,
    _sentiment_majority,
    _max_relevance,
)


def _make_article(pk, title, source="BERNAMA", pub_date=None,
                  relevance_score=None, sentiment="", url="https://example.com/"):
    """Build a duck-typed article-like object for clustering tests.

    Explicitly sets relevance_score + sentiment + url so the score
    computation in the clusterer doesn't see Mock's auto-generated
    truthy MagicMock attributes.
    """
    article = Mock()
    article.pk = pk
    article.title = title
    article.source_name = source
    article.published_date = pub_date or date(2026, 4, 15)
    article.relevance_score = relevance_score
    article.sentiment = sentiment
    article.url = url
    return article


@patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"})
class ClusterNewsArticlesTest(TestCase):
    def test_empty_input_returns_empty_list(self):
        self.assertEqual(cluster_news_articles([]), [])

    def test_single_article_skips_gemini(self):
        """One article = nothing to cluster; skip the Gemini call."""
        with patch("broadcasts.services.topic_clusterer.genai") as mock_genai:
            result = cluster_news_articles([_make_article(1, "Lone story")])
            mock_genai.Client.assert_not_called()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["headline"], "Other coverage")
        self.assertEqual(len(result[0]["articles"]), 1)

    def test_two_articles_skips_gemini(self):
        """Below the 3-article threshold, no Gemini call."""
        with patch("broadcasts.services.topic_clusterer.genai") as mock_genai:
            result = cluster_news_articles([
                _make_article(1, "A"),
                _make_article(2, "B"),
            ])
            mock_genai.Client.assert_not_called()
        self.assertEqual(len(result), 1)
        self.assertEqual(len(result[0]["articles"]), 2)

    @patch("broadcasts.services.topic_clusterer.genai")
    def test_clusters_articles_into_named_stories(self, mock_genai):
        articles = [
            _make_article(1, "Penang allocates RM2.42M to Tamil schools"),
            _make_article(2, "Penang state govt RM2.42M Tamil schools detail"),
            _make_article(3, "RM2.42M for SJK(T) in Penang"),
            _make_article(4, "SJK(T) Dengkil 65% complete"),
            _make_article(5, "SJK(T) Dengkil ahead of October deadline"),
        ]
        mock_response = Mock()
        mock_response.text = json.dumps({
            "clusters": [
                {
                    "headline": "Penang RM2.42M Tamil-school funding",
                    "story_summary": "Penang state allocates RM2.42M.",
                    "article_ids": [1, 2, 3],
                },
                {
                    "headline": "SJK(T) Dengkil redevelopment ahead of deadline",
                    "story_summary": "Project at 65.14%.",
                    "article_ids": [4, 5],
                },
            ],
            "unclustered_article_ids": [],
        })
        mock_genai.Client.return_value.models.generate_content.return_value = mock_response

        result = cluster_news_articles(articles)

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["headline"], "Penang RM2.42M Tamil-school funding")
        self.assertEqual(len(result[0]["articles"]), 3)
        self.assertEqual(result[1]["headline"], "SJK(T) Dengkil redevelopment ahead of deadline")
        self.assertEqual(len(result[1]["articles"]), 2)

    @patch("broadcasts.services.topic_clusterer.genai")
    def test_unclustered_articles_land_in_other_bucket(self, mock_genai):
        articles = [_make_article(i, f"Story {i}") for i in range(1, 6)]
        mock_response = Mock()
        mock_response.text = json.dumps({
            "clusters": [
                {
                    "headline": "Cluster A",
                    "story_summary": "",
                    "article_ids": [1, 2, 3],
                },
            ],
            "unclustered_article_ids": [4, 5],
        })
        mock_genai.Client.return_value.models.generate_content.return_value = mock_response

        result = cluster_news_articles(articles)

        self.assertEqual(len(result), 2)
        # The last cluster is always Other.
        self.assertEqual(result[-1]["headline"], "Other coverage")
        other_pks = {a.pk for a in result[-1]["articles"]}
        self.assertEqual(other_pks, {4, 5})

    @patch("broadcasts.services.topic_clusterer.genai")
    def test_gemini_failure_falls_back_to_other_bucket(self, mock_genai):
        articles = [_make_article(i, f"Story {i}") for i in range(1, 6)]
        mock_genai.Client.return_value.models.generate_content.side_effect = (
            RuntimeError("Gemini down")
        )

        result = cluster_news_articles(articles)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["headline"], "Other coverage")
        self.assertEqual(len(result[0]["articles"]), 5)

    @patch("broadcasts.services.topic_clusterer.genai")
    def test_invalid_json_falls_back_to_other_bucket(self, mock_genai):
        articles = [_make_article(i, f"Story {i}") for i in range(1, 6)]
        mock_response = Mock()
        mock_response.text = "not json"
        mock_genai.Client.return_value.models.generate_content.return_value = mock_response

        result = cluster_news_articles(articles)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["headline"], "Other coverage")
        self.assertEqual(len(result[0]["articles"]), 5)

    @patch("broadcasts.services.topic_clusterer.genai")
    def test_missing_clusters_key_falls_back_to_other_bucket(self, mock_genai):
        articles = [_make_article(i, f"Story {i}") for i in range(1, 6)]
        mock_response = Mock()
        mock_response.text = json.dumps({"not_clusters": []})
        mock_genai.Client.return_value.models.generate_content.return_value = mock_response

        result = cluster_news_articles(articles)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["headline"], "Other coverage")

    @patch("broadcasts.services.topic_clusterer.genai")
    def test_singleton_cluster_demoted_to_other(self, mock_genai):
        """Gemini sometimes returns a cluster with one article — demote it."""
        articles = [_make_article(i, f"Story {i}") for i in range(1, 6)]
        mock_response = Mock()
        mock_response.text = json.dumps({
            "clusters": [
                {"headline": "Cluster A", "story_summary": "",
                 "article_ids": [1, 2]},
                # Singleton — should NOT appear as its own cluster.
                {"headline": "Lonely article", "story_summary": "",
                 "article_ids": [3]},
            ],
            "unclustered_article_ids": [4, 5],
        })
        mock_genai.Client.return_value.models.generate_content.return_value = mock_response

        result = cluster_news_articles(articles)

        # Cluster A (2 articles) + Other (3 articles: 3, 4, 5).
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["headline"], "Cluster A")
        other_pks = {a.pk for a in result[-1]["articles"]}
        self.assertEqual(other_pks, {3, 4, 5})

    def test_no_api_key_falls_back_to_other_bucket(self):
        """When GEMINI_API_KEY is unset, skip Gemini and bucket everything."""
        with patch.dict("os.environ", {}, clear=True):
            articles = [_make_article(i, f"Story {i}") for i in range(1, 6)]
            result = cluster_news_articles(articles)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["headline"], "Other coverage")
        self.assertEqual(len(result[0]["articles"]), 5)

    @patch("broadcasts.services.topic_clusterer.genai")
    def test_duplicate_ids_across_clusters_are_resolved(self, mock_genai):
        """If Gemini lists the same id in two clusters, the first wins."""
        articles = [_make_article(i, f"Story {i}") for i in range(1, 6)]
        mock_response = Mock()
        mock_response.text = json.dumps({
            "clusters": [
                {"headline": "A", "story_summary": "",
                 "article_ids": [1, 2, 3]},
                # 3 is duplicated.
                {"headline": "B", "story_summary": "",
                 "article_ids": [3, 4, 5]},
            ],
            "unclustered_article_ids": [],
        })
        mock_genai.Client.return_value.models.generate_content.return_value = mock_response

        result = cluster_news_articles(articles)

        a_pks = {a.pk for a in result[0]["articles"]}
        self.assertEqual(a_pks, {1, 2, 3})
        b_pks = {a.pk for a in result[1]["articles"]}
        # 3 was already claimed by A; B keeps only the unseen ids.
        self.assertEqual(b_pks, {4, 5})

    @patch("broadcasts.services.topic_clusterer.genai")
    def test_unknown_id_silently_skipped(self, mock_genai):
        """Gemini hallucinating a non-existent id must not break the run."""
        articles = [_make_article(i, f"Story {i}") for i in range(1, 4)]
        mock_response = Mock()
        mock_response.text = json.dumps({
            "clusters": [
                {"headline": "A", "story_summary": "",
                 "article_ids": [1, 2, 999]},  # 999 doesn't exist
            ],
            "unclustered_article_ids": [3],
        })
        mock_genai.Client.return_value.models.generate_content.return_value = mock_response

        result = cluster_news_articles(articles)

        self.assertEqual(len(result), 2)
        self.assertEqual({a.pk for a in result[0]["articles"]}, {1, 2})
        self.assertEqual({a.pk for a in result[1]["articles"]}, {3})


class MaterialiseClustersUnitTest(TestCase):
    """Direct unit tests for _materialise_clusters edge cases."""

    def test_empty_clusters_returns_all_in_other(self):
        articles = [_make_article(i, f"A{i}") for i in range(1, 4)]
        result = _materialise_clusters({"clusters": []}, articles)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["headline"], "Other coverage")
        self.assertEqual(len(result[0]["articles"]), 3)

    def test_clusters_with_no_real_articles_collapse_to_other(self):
        articles = [_make_article(i, f"A{i}") for i in range(1, 4)]
        data = {
            "clusters": [
                {"headline": "Ghost", "story_summary": "",
                 "article_ids": [999, 888]},
            ],
        }
        result = _materialise_clusters(data, articles)
        # The ghost cluster matches no real articles → drops out;
        # all 3 articles land in Other.
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["headline"], "Other coverage")
        self.assertEqual(len(result[0]["articles"]), 3)


class ClusterMetadataTest(TestCase):
    """Sprint 24 #10b — score, lead article, sentiment majority shape."""

    def test_real_cluster_carries_score_and_metadata(self):
        articles = [
            _make_article(1, "A", relevance_score=4, sentiment="POSITIVE"),
            _make_article(2, "B", relevance_score=5, sentiment="POSITIVE"),
        ]
        data = {"clusters": [{"headline": "X", "story_summary": "",
                              "article_ids": [1, 2]}]}
        result = _materialise_clusters(data, articles)
        c = result[0]
        self.assertEqual(c["article_count"], 2)
        self.assertEqual(c["max_relevance"], 5)
        self.assertEqual(c["sentiment_majority"], "POSITIVE")
        # 2*2 + 5 + 1 (POSITIVE bonus) = 10
        self.assertEqual(c["score"], 10)
        self.assertFalse(c["is_other"])
        self.assertIsNotNone(c["lead_article"])

    def test_other_bucket_is_marked_and_unscored(self):
        articles = [_make_article(i, f"A{i}") for i in range(1, 4)]
        result = _materialise_clusters({"clusters": []}, articles)
        c = result[0]
        self.assertTrue(c["is_other"])
        self.assertEqual(c["score"], 0)
        self.assertEqual(c["article_count"], 3)


class ScoreFormulaTest(TestCase):
    def test_dengkil_example(self):
        # 4 articles, max relevance 5, majority positive → 4*2 + 5 + 1 = 14
        self.assertEqual(_score_cluster(4, 5, "POSITIVE"), 14)

    def test_single_negative_high_relevance_competes(self):
        # 1 article, relevance 5, negative → 1*2 + 5 + 2 = 9
        self.assertEqual(_score_cluster(1, 5, "NEGATIVE"), 9)

    def test_neutral_gets_no_bonus(self):
        self.assertEqual(_score_cluster(3, 4, "NEUTRAL"), 10)

    def test_unknown_sentiment_treated_as_neutral(self):
        self.assertEqual(_score_cluster(2, 3, ""), 7)


class SentimentMajorityTest(TestCase):
    def test_unanimous_positive(self):
        articles = [_make_article(i, "x", sentiment="POSITIVE") for i in range(1, 4)]
        self.assertEqual(_sentiment_majority(articles), "POSITIVE")

    def test_negative_wins_tie_against_positive(self):
        # Severity bias: a single concerning article isn't diluted.
        articles = [
            _make_article(1, "x", sentiment="POSITIVE"),
            _make_article(2, "x", sentiment="NEGATIVE"),
        ]
        self.assertEqual(_sentiment_majority(articles), "NEGATIVE")

    def test_empty_or_blank_falls_back_to_neutral(self):
        articles = [_make_article(1, "x", sentiment="")]
        self.assertEqual(_sentiment_majority(articles), "NEUTRAL")


class MaxRelevanceTest(TestCase):
    def test_returns_highest_score(self):
        articles = [
            _make_article(1, "x", relevance_score=3),
            _make_article(2, "x", relevance_score=5),
            _make_article(3, "x", relevance_score=4),
        ]
        self.assertEqual(_max_relevance(articles), 5)

    def test_handles_none_and_missing(self):
        articles = [
            _make_article(1, "x", relevance_score=None),
            _make_article(2, "x", relevance_score=4),
        ]
        self.assertEqual(_max_relevance(articles), 4)

    def test_empty_list_returns_zero(self):
        self.assertEqual(_max_relevance([]), 0)


class PickLeadArticleTest(TestCase):
    def test_highest_relevance_wins(self):
        articles = [
            _make_article(1, "low", relevance_score=2),
            _make_article(2, "high", relevance_score=5),
            _make_article(3, "mid", relevance_score=3),
        ]
        lead = _pick_lead_article(articles)
        self.assertEqual(lead.pk, 2)

    def test_tie_break_on_earliest_published_date(self):
        articles = [
            _make_article(1, "late", relevance_score=5,
                          pub_date=date(2026, 4, 20)),
            _make_article(2, "early", relevance_score=5,
                          pub_date=date(2026, 4, 5)),
        ]
        lead = _pick_lead_article(articles)
        self.assertEqual(lead.pk, 2)

    def test_tie_break_on_pk_when_dates_match(self):
        articles = [
            _make_article(7, "x", relevance_score=5,
                          pub_date=date(2026, 4, 5)),
            _make_article(3, "x", relevance_score=5,
                          pub_date=date(2026, 4, 5)),
        ]
        lead = _pick_lead_article(articles)
        self.assertEqual(lead.pk, 3)


class RankAndCapClustersTest(TestCase):
    """Sprint 24 #10b — rank_and_cap_clusters compose-step helper."""

    def _cluster(self, headline, score, count, is_other=False):
        return {
            "headline": headline,
            "story_summary": "",
            "articles": [],
            "article_count": count,
            "lead_article": None,
            "max_relevance": 3,
            "sentiment_majority": "NEUTRAL",
            "score": score,
            "is_other": is_other,
        }

    def test_sorts_by_score_desc(self):
        clusters = [
            self._cluster("low", score=5, count=2),
            self._cluster("high", score=14, count=4),
            self._cluster("mid", score=9, count=1),
        ]
        top, remainder = rank_and_cap_clusters(clusters, top_n=10)
        self.assertEqual([c["headline"] for c in top], ["high", "mid", "low"])
        self.assertEqual(remainder, 0)

    def test_caps_at_top_n_and_counts_dropped_articles(self):
        clusters = [self._cluster(f"c{i}", score=20 - i, count=3)
                    for i in range(12)]
        top, remainder = rank_and_cap_clusters(clusters, top_n=10)
        self.assertEqual(len(top), 10)
        # 2 dropped clusters × 3 articles each = 6.
        self.assertEqual(remainder, 6)

    def test_other_bucket_excluded_from_cards_added_to_remainder(self):
        clusters = [
            self._cluster("real", score=10, count=3),
            self._cluster("Other coverage", score=0, count=5, is_other=True),
        ]
        top, remainder = rank_and_cap_clusters(clusters, top_n=10)
        self.assertEqual(len(top), 1)
        self.assertEqual(top[0]["headline"], "real")
        self.assertEqual(remainder, 5)

    def test_remainder_combines_dropped_and_other(self):
        clusters = [self._cluster(f"c{i}", score=20 - i, count=2)
                    for i in range(11)]
        clusters.append(self._cluster("Other coverage", score=0, count=4,
                                       is_other=True))
        top, remainder = rank_and_cap_clusters(clusters, top_n=10)
        self.assertEqual(len(top), 10)
        # 1 dropped real cluster × 2 + Other (4) = 6.
        self.assertEqual(remainder, 6)

    def test_empty_input(self):
        top, remainder = rank_and_cap_clusters([], top_n=10)
        self.assertEqual(top, [])
        self.assertEqual(remainder, 0)

    def test_under_top_n_returns_all_real_clusters(self):
        clusters = [
            self._cluster("a", score=10, count=2),
            self._cluster("b", score=8, count=2),
        ]
        top, remainder = rank_and_cap_clusters(clusters, top_n=10)
        self.assertEqual(len(top), 2)
        self.assertEqual(remainder, 0)

    def test_stable_tiebreak_on_equal_scores(self):
        # Same score: tie-break by article_count DESC, then max_relevance
        # DESC, then headline alpha. Deterministic across runs.
        clusters = [
            self._cluster("alpha", score=10, count=2),
            self._cluster("bravo", score=10, count=3),
            self._cluster("charlie", score=10, count=3),
        ]
        top, _ = rank_and_cap_clusters(clusters, top_n=10)
        # bravo + charlie (count=3) come before alpha (count=2);
        # within the count=3 pair, alpha-order on headline → bravo first.
        self.assertEqual([c["headline"] for c in top],
                         ["bravo", "charlie", "alpha"])
