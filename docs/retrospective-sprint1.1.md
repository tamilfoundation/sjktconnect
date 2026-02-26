# Sprint 1.1 Retrospective — WKT Boundary Import + GeoJSON API

**Date**: 2026-02-26
**Duration**: 1 session (same day as Sprint 0.6 close)
**Sprint goal**: Import constituency/DUN boundary polygons and serve as GeoJSON API

---

## What Was Built

1. **Boundary fields** — `boundary_wkt` TextField added to both Constituency and DUN models. DUN boundaries stored directly from CSV. Constituency boundaries computed by unioning their DUNs' polygons via `shapely.ops.unary_union`.

2. **Import command update** — `import_constituencies` now parses the WKT column from `Political Constituencies.csv` and stores it on each DUN. After all DUNs are created, it computes constituency boundaries automatically.

3. **GeoJSON API** — 4 DRF endpoints serving valid GeoJSON FeatureCollections. DUN list supports `?state=` and `?constituency=` filters. Individual detail endpoints return single Features.

4. **Dependencies** — `shapely>=2.0` (WKT parsing + GeoJSON conversion) and `djangorestframework>=3.15` (REST API foundation for Phase 1).

## What Went Well

- **Shapely over GeoDjango was the right call** — no GDAL/GEOS system libraries needed, works on Windows, no Docker changes, no PostGIS extension needed. The WKT→GeoJSON conversion is simple and fast.
- **Existing test infrastructure worked smoothly** — adding new test files followed established patterns. 19 new tests written alongside the code.
- **CSV data was already structured** — the WKT column had clean OGC POLYGON data. No parsing issues.
- **DRF adds value for Sprint 1.2** — adding it now as a foundation means Sprint 1.2 (full REST API) can focus on serializers and viewsets rather than setup.

## What Went Wrong

1. **Test CSV encoding mismatch** — The existing test helper created CSVs with `utf-8-sig` (adds BOM), but the import command reads with `cp1252`. The BOM corrupted the first column header "WKT" into "ï»¿WKT". Fixed by changing test encoding to `cp1252` to match the real file. This was invisible in Phase 0 because the WKT column was never read.

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| shapely + TextField over GeoDjango + PostGIS | Phase 1 only needs GeoJSON for map rendering. Spatial queries (point-in-polygon) not needed yet. Avoids GDAL on Windows + Docker bloat. Can upgrade later. |
| Compute constituency boundaries from DUNs | CSV has one WKT per DUN, not per constituency. Union via `unary_union` produces correct merged boundaries. |
| DRF APIViews over plain Django views | Establishes the REST API pattern for Sprint 1.2. Consistent response format, content negotiation, browsable API for debugging. |
| Filter DUNs by state and constituency | The map frontend will need to load boundaries per-state or per-constituency for performance — filtering at the API level avoids sending all 613 DUN polygons at once. |

## Numbers

| Metric | Value |
|--------|-------|
| Tests added | 19 (13 API, 6 helpers) |
| Tests total | 239 |
| Files created | 5 (api/__init__.py, views.py, urls.py, geojson.py, 2 test files) |
| Files modified | 5 (models.py, import_constituencies.py, requirements.txt, base.py settings, root urls.py, test_import_constituencies.py) |
| Migration | 1 (0002_add_boundary_wkt) |
| Dependencies added | 2 (shapely, djangorestframework) |
