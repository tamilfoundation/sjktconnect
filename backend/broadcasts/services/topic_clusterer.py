"""Sprint 24 task #2 — Gemini topic clustering for monthly digest.

Groups N approved news articles into stories so a 46-article month reads
as a small set of "X happened" headlines rather than 46 disconnected
snippets.

One Gemini call per digest at compose time (~$0.001/month). Fail-open per
the news_digest.py pattern: on Gemini failure, malformed JSON, or missing
required keys, return all articles in a single "Other" bucket so the
compose pipeline never breaks because of clustering.

Wired into compose_monthly_blast between aggregator and template render.
The output shape is consumed by monthly_blast_v2.html (Sprint 24 task #4).
"""

import json
import logging
import os

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

# Sprint 24 task #2 — keep the prompt focused on a single output shape.
# We deliberately use per-cluster article_ids (not per-article cluster_id)
# because the template needs cluster headlines as primary section headers.
CLUSTER_PROMPT = """\
You are grouping {n_articles} news articles about Malaysian Tamil schools \
(SJK(T)) into topic clusters for a monthly digest email.

Each article is tagged with an integer id. Group articles that cover the \
SAME underlying story or development. A cluster needs at least 2 articles; \
singletons stay unclustered.

Aim for 3-6 clusters total. Be aggressive about grouping: 8 articles about \
a single school's RM4M redevelopment IS one story, not eight. Different \
schools or different funding announcements ARE separate stories even when \
the dollar figures look similar.

--- ARTICLES ---
{articles_block}
--- END ---

Return ONLY valid JSON with this exact shape (no markdown fences, no extra text):

{{
  "clusters": [
    {{
      "headline": "Short punchy line, max 80 chars, written in British English",
      "story_summary": "1-2 sentences explaining the underlying story",
      "article_ids": [12, 47, 88]
    }}
  ],
  "unclustered_article_ids": [99, 100]
}}

Rules:
- Every article id MUST appear EXACTLY ONCE across all clusters + unclustered_article_ids.
- Cluster headlines must be specific (name the school, the figure, the place) \
not generic ("School news this month").
- If you cannot find any meaningful clusters, return empty "clusters" and \
list all article ids in "unclustered_article_ids".
"""


def _format_articles(articles) -> str:
    """Render articles into id-tagged lines for the prompt."""
    lines = []
    for article in articles:
        title = (article.title or "").strip().replace("\n", " ")
        pub_date = (
            article.published_date.strftime("%d %b %Y")
            if article.published_date else "?"
        )
        source = (article.source_name or "?").strip()
        lines.append(f"[id={article.pk}] {title} ({source}, {pub_date})")
    return "\n".join(lines)


def _other_bucket(articles):
    """Build the fail-open / un-clustered fallback shape.

    Single 'Other' cluster containing all the input articles, with empty
    story_summary so the template can hide the summary line.
    """
    return [{
        "headline": "Other coverage" if articles else "",
        "story_summary": "",
        "articles": list(articles),
    }]


def cluster_news_articles(articles):
    """Cluster a list of NewsArticle instances into topic groups.

    Args:
        articles: iterable of NewsArticle (with at least pk, title,
            published_date, source_name populated).

    Returns:
        list of cluster dicts, each shaped:
            {
                "headline": str,
                "story_summary": str,
                "articles": [NewsArticle, ...],
            }
        The last cluster is always titled "Other coverage" (or the only
        cluster on the fail-open path) and contains any singletons or
        unclustered articles.

    Behaviour:
        - Empty input → returns [].
        - Single article → returns one cluster with that article (no
          Gemini call; clustering one item is meaningless).
        - API failure / malformed JSON / missing key → all articles in
          a single Other bucket. Never raises to the caller.
    """
    article_list = list(articles)

    if not article_list:
        return []

    # Skip Gemini for trivially small inputs — clustering 1-2 items
    # adds no value and wastes a request.
    if len(article_list) < 3:
        return _other_bucket(article_list)

    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        logger.warning(
            "GEMINI_API_KEY not set — skipping topic clustering, "
            "returning all %d articles in Other bucket",
            len(article_list),
        )
        return _other_bucket(article_list)

    prompt = CLUSTER_PROMPT.format(
        n_articles=len(article_list),
        articles_block=_format_articles(article_list),
    )

    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.2,
            ),
        )
        raw = response.text.strip()
    except Exception:
        logger.exception(
            "Gemini call failed during topic clustering — "
            "falling back to Other bucket"
        )
        return _other_bucket(article_list)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        logger.error(
            "Topic clusterer received invalid JSON from Gemini: %s",
            raw[:200],
        )
        return _other_bucket(article_list)

    if "clusters" not in data:
        logger.error(
            "Topic clusterer response missing 'clusters' key: %s",
            list(data.keys()),
        )
        return _other_bucket(article_list)

    return _materialise_clusters(data, article_list)


def _materialise_clusters(data, article_list):
    """Convert Gemini's id-based response into article-object clusters.

    Validates and de-duplicates:
    - Each article id must reference a real article from the input.
    - An article appears in at most one cluster.
    - Singletons (clusters with <2 articles) get demoted to the Other
      bucket regardless of what Gemini said.
    - Any article Gemini failed to mention ends up in the Other bucket.
    """
    by_id = {a.pk: a for a in article_list}
    seen_ids = set()
    clusters = []

    for raw_cluster in data.get("clusters", []) or []:
        ids = raw_cluster.get("article_ids", []) or []
        cluster_articles = []
        for aid in ids:
            if not isinstance(aid, int):
                continue
            if aid in seen_ids:
                continue
            article = by_id.get(aid)
            if article is None:
                continue
            cluster_articles.append(article)
            seen_ids.add(aid)
        if len(cluster_articles) < 2:
            # Demote singleton — Gemini sometimes labels lone articles
            # as a "cluster"; keep these in the Other bucket so the
            # primary cluster section only shows real story groupings.
            for article in cluster_articles:
                seen_ids.discard(article.pk)
            continue
        clusters.append({
            "headline": str(raw_cluster.get("headline", "")).strip() or "Untitled story",
            "story_summary": str(raw_cluster.get("story_summary", "")).strip(),
            "articles": cluster_articles,
        })

    # Everything Gemini didn't cluster (or that we demoted) goes here.
    other_articles = [a for a in article_list if a.pk not in seen_ids]
    if other_articles:
        clusters.append({
            "headline": "Other coverage",
            "story_summary": "",
            "articles": other_articles,
        })

    return clusters
