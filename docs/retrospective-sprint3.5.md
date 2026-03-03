# Sprint 3.5 Retrospective — Tamil Translation Review + Deployment

**Date**: 2026-03-03
**Duration**: ~1 session (split across gcloud auth fix)

## What Was Built

1. **Tamil translation audit**: Reviewed all ~162 strings in `ta.json` against 85+ grammar rules. Found and fixed 9 issues:
   - 7 vallinam doubling violations (CAT3 rules)
   - 1 terminology inconsistency (நுண்ணறிவு → புலனாய்வு)
   - 1 terminology improvement (AI → செய்யறிவு, சந்தா → இணை)
   - 1 redundancy removal (செய்யறிவு இயங்கு → செய்யறிவு)

2. **Backend deployment**: Revision 00016-vlb with all Sprint 3.3-3.4 changes. Updated 3 Cloud Run jobs.

3. **Frontend deployment**: Revision 00013-ff8. Required @swc/helpers dependency fix first.

## What Went Well

- **Tamil expert review**: User caught two issues the automated audit missed — செய்யறிவு as better Tamil for "AI", and இணை instead of சந்தா for "subscribe". Domain expertise matters.
- **Backend deploy was smooth**: Single attempt, health check passed immediately.
- **Cloud Run jobs updated**: All 3 jobs pointed to latest image in one go.

## What Went Wrong

- **gcloud CLI broken**: Python 3.11 was uninstalled, gcloud still pointed to it. Required `CLOUDSDK_PYTHON` env var fix + `setx` for persistence. Cost ~15 minutes of back-and-forth.
- **Frontend build failed first attempt**: `@swc/helpers` version mismatch — `next-intl@4.8.3` brought in `@swc/core@1.15.18` requiring `>=0.5.17`, but lock file had `0.5.5`. Fixed with explicit `npm install @swc/helpers@latest`.
- **Plan had wrong API URL**: Plan referenced `/api/v1/schools/national-stats/` but actual URL is `/api/v1/stats/national/`.

## Design Decisions

- **செய்யறிவு over AI**: Tamil has a proper word for artificial intelligence (செயற்கை + அறிவு = செய்யறிவு). Using it instead of the English abbreviation is more natural and professional.
- **இணையுங்கள் over சந்தா செலுத்துங்கள்**: "Join" is better than "pay subscription" for a free newsletter — சந்தா implies financial payment.
- **புலனாய்வு standardised**: Chose புலனாய்வு (investigation/intelligence) over நுண்ணறிவு (insight) consistently across the site.

## Numbers

- Tamil fixes: 9 (7 grammar + 2 terminology)
- Backend revision: 00016-vlb
- Frontend revision: 00013-ff8
- Tests: 747 (532 backend + 215 frontend) — unchanged
- Deploy attempts: backend 1, frontend 2 (dependency fix)
