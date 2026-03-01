# School Page Fix & Enrich — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix broken school photos, build the missing Parliament Watch endpoint, add placeholder sections (History, News Watch), and improve page layout.

**Architecture:** Backend-first — build the mentions API endpoint and update the image harvester, then update the frontend page and components. Existing page at `frontend/app/school/[moe_code]/page.tsx` is the base.

**Tech Stack:** Django REST Framework (backend), Next.js 14 App Router (frontend), Google Places/Maps APIs (images)

---

### Task 1: Build School Mentions API Endpoint — Test

**Files:**
- Create: `backend/parliament/tests/test_school_mentions_api.py`

**Step 1: Write the failing tests**

```python
"""Tests for school mentions API endpoint."""

from datetime import date
from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from hansard.models import HansardMention, HansardSitting, MentionedSchool
from schools.models import School


class SchoolMentionsAPITest(TestCase):
    """Tests for GET /api/v1/schools/<moe_code>/mentions/."""

    def setUp(self):
        self.client = APIClient()
        self.school = School.objects.create(
            moe_code="TEST001",
            name="SEKOLAH JENIS KEBANGSAAN (TAMIL) TEST",
            short_name="SJK(T) TEST",
            state="SELANGOR",
        )
        self.sitting = HansardSitting.objects.create(
            sitting_date=date(2024, 10, 15),
            pdf_url="https://example.com/hansard.pdf",
            pdf_filename="hansard.pdf",
            status=HansardSitting.Status.COMPLETED,
        )

    def test_returns_approved_mentions(self):
        mention = HansardMention.objects.create(
            sitting=self.sitting,
            verbatim_quote="SJK(T) Test was discussed",
            mp_name="YB Test",
            mp_constituency="P999 Test",
            mp_party="PKR",
            mention_type="QUESTION",
            significance=4,
            sentiment="POSITIVE",
            ai_summary="Discussion about Tamil school improvements.",
            review_status="APPROVED",
        )
        MentionedSchool.objects.create(
            mention=mention,
            school=self.school,
            confidence_score=Decimal("95.00"),
            matched_by=MentionedSchool.MatchMethod.EXACT,
        )

        resp = self.client.get(f"/api/v1/schools/{self.school.moe_code}/mentions/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 1)
        self.assertEqual(resp.data[0]["mp_name"], "YB Test")
        self.assertEqual(resp.data[0]["sitting_date"], "2024-10-15")
        self.assertEqual(resp.data[0]["significance"], 4)

    def test_excludes_pending_mentions(self):
        mention = HansardMention.objects.create(
            sitting=self.sitting,
            verbatim_quote="Pending mention",
            review_status="PENDING",
        )
        MentionedSchool.objects.create(
            mention=mention, school=self.school,
            confidence_score=Decimal("80.00"),
        )

        resp = self.client.get(f"/api/v1/schools/{self.school.moe_code}/mentions/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 0)

    def test_excludes_rejected_mentions(self):
        mention = HansardMention.objects.create(
            sitting=self.sitting,
            verbatim_quote="Rejected mention",
            review_status="REJECTED",
        )
        MentionedSchool.objects.create(
            mention=mention, school=self.school,
            confidence_score=Decimal("60.00"),
        )

        resp = self.client.get(f"/api/v1/schools/{self.school.moe_code}/mentions/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 0)

    def test_returns_empty_for_school_with_no_mentions(self):
        resp = self.client.get(f"/api/v1/schools/{self.school.moe_code}/mentions/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 0)

    def test_404_for_nonexistent_school(self):
        resp = self.client.get("/api/v1/schools/NOSUCH/mentions/")
        self.assertEqual(resp.status_code, 404)

    def test_ordered_by_sitting_date_descending(self):
        sitting2 = HansardSitting.objects.create(
            sitting_date=date(2024, 11, 20),
            pdf_url="https://example.com/h2.pdf",
            pdf_filename="h2.pdf",
            status=HansardSitting.Status.COMPLETED,
        )
        m1 = HansardMention.objects.create(
            sitting=self.sitting,
            verbatim_quote="Older",
            mp_name="YB First",
            review_status="APPROVED",
        )
        m2 = HansardMention.objects.create(
            sitting=sitting2,
            verbatim_quote="Newer",
            mp_name="YB Second",
            review_status="APPROVED",
        )
        MentionedSchool.objects.create(
            mention=m1, school=self.school, confidence_score=Decimal("90.00"),
        )
        MentionedSchool.objects.create(
            mention=m2, school=self.school, confidence_score=Decimal("90.00"),
        )

        resp = self.client.get(f"/api/v1/schools/{self.school.moe_code}/mentions/")
        self.assertEqual(resp.data[0]["mp_name"], "YB Second")
        self.assertEqual(resp.data[1]["mp_name"], "YB First")
```

**Step 2: Run tests to verify they fail**

Run: `cd backend && python manage.py test parliament.tests.test_school_mentions_api -v 2`
Expected: FAIL — URL not found (404 on all requests)

---

### Task 2: Build School Mentions API Endpoint — Implementation

**Files:**
- Create: `backend/parliament/api/views.py` (add `SchoolMentionsView`)
- Modify: `backend/parliament/api/serializers.py` (add `SchoolMentionSerializer`)
- Modify: `backend/schools/api/urls.py` (add mentions route)

**Step 1: Add serializer**

In `backend/parliament/api/serializers.py`, add:

```python
class SchoolMentionSerializer(serializers.Serializer):
    """Read-only serializer for school mentions from Hansard."""

    sitting_date = serializers.DateField(source="sitting.sitting_date")
    mp_name = serializers.CharField()
    mp_constituency = serializers.CharField()
    mp_party = serializers.CharField()
    mention_type = serializers.CharField()
    significance = serializers.IntegerField()
    sentiment = serializers.CharField()
    ai_summary = serializers.CharField()
    verbatim_quote = serializers.CharField()
```

**Step 2: Add view**

In `backend/parliament/api/views.py`, add:

```python
from rest_framework import generics
from django.shortcuts import get_object_or_404

from hansard.models import HansardMention
from schools.models import School
from parliament.api.serializers import SchoolMentionSerializer


class SchoolMentionsView(generics.ListAPIView):
    """GET /api/v1/schools/<moe_code>/mentions/ — approved Hansard mentions for a school."""

    serializer_class = SchoolMentionSerializer
    authentication_classes = []
    permission_classes = []
    pagination_class = None

    def get_queryset(self):
        school = get_object_or_404(School, moe_code=self.kwargs["moe_code"])
        return (
            HansardMention.objects.filter(
                matched_schools__school=school,
                review_status="APPROVED",
            )
            .select_related("sitting")
            .order_by("-sitting__sitting_date")
        )
```

**Step 3: Add URL route**

In `backend/schools/api/urls.py`, add import and route BEFORE the `<str:moe_code>/` detail route:

```python
# Add to imports:
from parliament.api.views import SchoolMentionsView

# Add this line BEFORE the school-detail path:
path("schools/<str:moe_code>/mentions/", SchoolMentionsView.as_view(), name="school-mentions"),
```

**Step 4: Run tests to verify they pass**

Run: `cd backend && python manage.py test parliament.tests.test_school_mentions_api -v 2`
Expected: All 6 tests PASS

**Step 5: Run full backend test suite**

Run: `cd backend && python manage.py test --parallel -v 1`
Expected: All tests pass (426+)

**Step 6: Commit**

```bash
git add backend/parliament/tests/test_school_mentions_api.py backend/parliament/api/serializers.py backend/parliament/api/views.py backend/schools/api/urls.py
git commit -m "feat: add school mentions API endpoint (GET /schools/<moe_code>/mentions/)"
```

---

### Task 3: Update Image Harvester for Multiple Places Photos

**Files:**
- Modify: `backend/outreach/services/image_harvester.py`
- Create: `backend/outreach/tests/test_image_harvester.py`

**Step 1: Write tests for multi-photo harvesting**

```python
"""Tests for image harvester service."""

from unittest.mock import patch, MagicMock

from django.test import TestCase

from outreach.models import SchoolImage
from outreach.services.image_harvester import (
    harvest_places_images,
    harvest_images_for_school,
)
from schools.models import School


class HarvestPlacesImagesTest(TestCase):
    def setUp(self):
        self.school = School.objects.create(
            moe_code="TEST001",
            name="SJK(T) TEST",
            short_name="SJK(T) TEST",
            state="SELANGOR",
            gps_lat="3.1234",
            gps_lng="101.5678",
        )

    @patch("outreach.services.image_harvester._get_api_key", return_value="fake-key")
    @patch("outreach.services.image_harvester.requests.get")
    def test_harvests_up_to_3_photos(self, mock_get, mock_key):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "candidates": [{
                "photos": [
                    {"photo_reference": "ref1", "html_attributions": ["attr1"]},
                    {"photo_reference": "ref2", "html_attributions": ["attr2"]},
                    {"photo_reference": "ref3", "html_attributions": ["attr3"]},
                    {"photo_reference": "ref4", "html_attributions": ["attr4"]},
                ],
            }]
        }
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        images = harvest_places_images(self.school, max_photos=3)
        self.assertEqual(len(images), 3)
        self.assertTrue(images[0].is_primary)
        self.assertFalse(images[1].is_primary)
        self.assertFalse(images[2].is_primary)

    @patch("outreach.services.image_harvester._get_api_key", return_value="fake-key")
    @patch("outreach.services.image_harvester.requests.get")
    def test_clears_old_places_images_before_harvest(self, mock_get, mock_key):
        SchoolImage.objects.create(
            school=self.school,
            source=SchoolImage.Source.PLACES,
            image_url="https://old.com/photo",
            is_primary=True,
        )

        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "candidates": [{"photos": [
                {"photo_reference": "new_ref", "html_attributions": []},
            ]}]
        }
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        images = harvest_places_images(self.school, max_photos=3)
        self.assertEqual(SchoolImage.objects.filter(school=self.school, source="PLACES").count(), 1)
        self.assertEqual(images[0].photo_reference, "new_ref")
```

**Step 2: Run tests to verify they fail**

Run: `cd backend && python manage.py test outreach.tests.test_image_harvester -v 2`
Expected: FAIL — `harvest_places_images` not found

**Step 3: Implement updated harvester**

In `backend/outreach/services/image_harvester.py`, rename `harvest_places_image` to `harvest_places_images` and update to:
- Accept `max_photos: int = 3` parameter
- Delete existing Places images before re-creating
- Loop through `photos[:max_photos]`, first one becomes primary
- Update `harvest_images_for_school` to call `harvest_places_images` (returns list)

**Step 4: Run tests to verify they pass**

Run: `cd backend && python manage.py test outreach.tests.test_image_harvester -v 2`
Expected: PASS

**Step 5: Run full test suite**

Run: `cd backend && python manage.py test --parallel -v 1`
Expected: All tests pass

**Step 6: Commit**

```bash
git add backend/outreach/services/image_harvester.py backend/outreach/tests/test_image_harvester.py
git commit -m "feat: harvest up to 3 Places photos per school"
```

---

### Task 4: Update School Detail Serializer to Return All Images

**Files:**
- Modify: `backend/schools/api/serializers.py`
- Add test to existing school API tests

**Step 1: Write test**

Add to existing school detail API tests:

```python
def test_school_detail_returns_images_list(self):
    """School detail includes all images, not just primary."""
    from outreach.models import SchoolImage

    SchoolImage.objects.create(
        school=self.school,
        source="PLACES",
        image_url="https://example.com/photo1.jpg",
        is_primary=True,
    )
    SchoolImage.objects.create(
        school=self.school,
        source="PLACES",
        image_url="https://example.com/photo2.jpg",
        is_primary=False,
    )

    resp = self.client.get(f"/api/v1/schools/{self.school.moe_code}/")
    self.assertEqual(len(resp.data["images"]), 2)
    self.assertEqual(resp.data["images"][0]["image_url"], "https://example.com/photo1.jpg")
    self.assertTrue(resp.data["images"][0]["is_primary"])
```

**Step 2: Add SchoolImageSerializer and images field to SchoolDetailSerializer**

In `backend/schools/api/serializers.py`:

```python
class SchoolImageSerializer(serializers.Serializer):
    image_url = serializers.URLField()
    source = serializers.CharField()
    is_primary = serializers.BooleanField()
    attribution = serializers.CharField()
```

In `SchoolDetailSerializer`, add `images = serializers.SerializerMethodField()` and:

```python
def get_images(self, obj):
    images = obj.images.order_by("-is_primary", "-created_at")
    return SchoolImageSerializer(images, many=True).data
```

Keep existing `image_url` field for backwards compatibility.

**Step 3: Run tests and commit**

Run: `cd backend && python manage.py test --parallel -v 1`

```bash
git add backend/schools/api/serializers.py backend/schools/tests/
git commit -m "feat: return all school images in detail endpoint"
```

---

### Task 5: Update Frontend Types and API Client

**Files:**
- Modify: `frontend/lib/types.ts`

**Step 1: Add SchoolImageType and update SchoolDetail**

In `frontend/lib/types.ts`:

```typescript
export interface SchoolImageData {
  image_url: string;
  source: "SATELLITE" | "PLACES" | "STREET_VIEW" | "MANUAL";
  is_primary: boolean;
  attribution: string;
}
```

Add to `SchoolDetail`: `images: SchoolImageData[];`

**Step 2: Commit**

```bash
git add frontend/lib/types.ts
git commit -m "feat: add SchoolImageData type to frontend"
```

---

### Task 6: Redesign School Page Layout + New Sections

**Files:**
- Modify: `frontend/app/school/[moe_code]/page.tsx`
- Modify: `frontend/components/SchoolImage.tsx` (photo gallery with fallback)
- Create: `frontend/components/SchoolHistory.tsx` (placeholder CTA)
- Create: `frontend/components/NewsWatchSection.tsx` (placeholder)

**Step 1: Create SchoolHistory placeholder**

```tsx
// frontend/components/SchoolHistory.tsx
export default function SchoolHistory() {
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6">
      <h2 className="text-lg font-semibold text-gray-800 mb-3">
        History &amp; Story
      </h2>
      <p className="text-sm text-gray-500 mb-4">
        Every Tamil school has a story worth telling. Help us preserve it.
      </p>
      <p className="text-sm text-gray-600">
        If you have information about this school&rsquo;s history &mdash;
        founding year, key milestones, notable alumni &mdash; we&rsquo;d
        love to hear from you.
      </p>
      <a
        href="mailto:info@tamilfoundation.org?subject=School%20History%20Contribution"
        className="inline-block mt-4 text-sm font-medium text-primary-600 hover:text-primary-800"
      >
        Contact us to contribute &rarr;
      </a>
    </div>
  );
}
```

**Step 2: Create NewsWatchSection placeholder**

```tsx
// frontend/components/NewsWatchSection.tsx
export default function NewsWatchSection() {
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6">
      <h2 className="text-lg font-semibold text-gray-800 mb-3">
        News Watch
      </h2>
      <p className="text-sm text-gray-400 italic">
        No news articles yet. News monitoring is coming soon.
      </p>
    </div>
  );
}
```

**Step 3: Update SchoolImage.tsx as photo gallery with fallback chain**

Replace with gallery component that:
- Shows primary photo as hero (or first photo)
- Shows thumbnails below for additional photos
- Shows placeholder when no photos exist
- Handles attribution text safely (render as text, not HTML)

**Step 4: Update school page layout**

New order in `page.tsx`:
1. Breadcrumb
2. Photo gallery (hero)
3. School name + Tamil name (`name_tamil`) + subtitle
4. Two-column: (Profile + Map + Parliament Watch + News Watch + History) | (Sidebar)
5. Claim banner (bottom, smaller)

**Step 5: Commit**

```bash
git add frontend/components/ frontend/app/school/
git commit -m "feat: redesign school page — gallery, history CTA, news watch, layout"
```

---

### Task 7: Re-harvest School Images with New API Key

**This task requires the GOOGLE_MAPS_API_KEY env var on Cloud Run.**

**Step 1: Update backend Cloud Run env var** (manual — GCP Console)

**Step 2: Run re-harvest**

```bash
# Dry run first
python manage.py harvest_school_images --source places --dry-run --limit 5

# Small test batch
python manage.py harvest_school_images --source places --limit 5

# Full harvest if test passes
python manage.py harvest_school_images --source places

# Satellite fallback
python manage.py harvest_school_images --source satellite
```

Note: Makes Google Places API calls — run in batches.

---

### Task 8: Deploy and Verify

**Step 1: Deploy backend**

```bash
gcloud run deploy sjktconnect-api --source . --region asia-southeast1
```

**Step 2: Deploy frontend**

```bash
gcloud run deploy sjktconnect-web --source . --region asia-southeast1 --allow-unauthenticated
```

**Step 3: Verify on live site**

- `tamilschool.org/school/ABD7048` — photos display
- Parliament Watch section shows mentions (if any approved)
- History section shows CTA
- News Watch section shows placeholder
- Claim button at bottom

**Step 4: Final commit and push**

```bash
cd backend && python manage.py test --parallel -v 1
git push
```

---

## Summary

| Task | What | Files |
|------|------|-------|
| 1 | Mentions API tests | 1 new |
| 2 | Mentions API implementation | 3 modified |
| 3 | Multi-photo harvester | 1 modified, 1 new |
| 4 | Images in school detail serializer | 2 modified |
| 5 | Frontend types update | 1 modified |
| 6 | Page layout redesign + new components | 2 modified, 2 new |
| 7 | Re-harvest images | Management command (no code) |
| 8 | Deploy and verify | Deployment |

**Total: ~10 files touched, 2 new test files, 2 new components, 2 deploys**
