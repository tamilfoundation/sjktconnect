# Sprint 1.2 Retrospective — Django REST API for Schools + Constituencies

**Date**: 2026-02-26
**Duration**: ~30 minutes

## What Was Built

Full Django REST Framework API layer exposing all data models for the upcoming Next.js frontend:

- **School API** (list with 6 filters + detail by moe_code)
- **Constituency API** (list with school_count annotation + detail with nested schools and scorecard)
- **DUN API** (list with state/constituency filters + detail with nested schools)
- **MPScorecard API** (list with constituency/party filters + detail)
- **SittingBrief API** (published-only list + detail)
- **Search endpoint** (cross-entity: schools by name/code, constituencies by name/code/MP)
- **CORS** via django-cors-headers
- **Pagination** (50 items/page)

## What Went Well

1. **Clean build** — 37 tests written alongside code, all passed on first run. Zero regressions on full 276-test suite.
2. **Existing DRF setup** — Sprint 1.1 already added DRF and the `schools/api/` package. This sprint cleanly extended both.
3. **Serializer layering** — List serializers are compact (12 fields), detail serializers are rich (all fields + nested relations). Good for both map rendering and full profile pages.
4. **URL ordering caught early** — Recognised that `constituencies/<str:code>/` would capture `constituencies/geojson/` as a code. Placed literal paths before parameterised ones.

## What Went Wrong

1. **Pagination warning** — Constituency list with `.annotate()` lost the model's default ordering, triggering DRF's UnorderedObjectListWarning. Fixed by adding `.order_by("code")` after annotate.

## Design Decisions

1. **Separate list/detail serializers** — SchoolListSerializer (12 fields) vs SchoolDetailSerializer (30 fields). List is optimised for map pins and tables; detail for full profile pages.
2. **school_count annotation** — ConstituencyListSerializer includes a dynamic `school_count` via `Count("schools", filter=Q(is_active=True))` to avoid N+1 queries.
3. **Scorecard via SerializerMethodField** — Rather than a nested serializer, ConstituencyDetailSerializer manually picks 5 scorecard fields. Simpler, avoids circular imports, and the scorecard shape is unlikely to change.
4. **Search as a single endpoint** — Returns `{schools: [...], constituencies: [...]}` rather than separate search-per-entity endpoints. Matches the frontend's unified search box UX.
5. **Published-only briefs** — SittingBriefListView and DetailView both filter `is_published=True`. Unpublished briefs return 404 even if the pk exists.
6. **CORS via env var** — `CORS_ALLOWED_ORIGINS` defaults to `http://localhost:3000` for dev, overridable in production Cloud Run env.

## Numbers

| Metric | Value |
|--------|-------|
| Tests added | 37 |
| Tests total | 276 |
| Files created | 7 |
| Files modified | 4 |
| API endpoints added | 12 |
| Build time | ~30 min |
