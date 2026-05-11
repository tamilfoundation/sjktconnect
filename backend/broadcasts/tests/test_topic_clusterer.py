"""Tests for Sprint 24 task #2 — topic_clusterer service."""

import json
from datetime import date
from unittest.mock import patch, Mock

from django.test import TestCase

from broadcasts.services.topic_clusterer import (
    cluster_news_articles,
    _materialise_clusters,
)


def _make_article(pk, title, source="BERNAMA", pub_date=None):
    """Build a duck-typed article-like object for clustering tests.

    The clusterer only reads pk, title, source_name, published_date —
    no DB row required.
    """
    article = Mock()
    article.pk = pk
    article.title = title
    article.source_name = source
    article.published_date = pub_date or date(2026, 4, 15)
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
