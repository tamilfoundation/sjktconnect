"""API views for schools, constituencies, DUNs, and GeoJSON boundaries."""

from django.db.models import Count, Q, Sum
from django.utils import timezone

from rest_framework import status
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsMagicLinkAuthenticated
from core.models import AuditLog
from schools.api.geojson import to_feature, to_feature_collection
from schools.api.serializers import (
    ConstituencyDetailSerializer,
    ConstituencyListSerializer,
    DUNDetailSerializer,
    DUNListSerializer,
    SchoolDetailSerializer,
    SchoolEditSerializer,
    SchoolListSerializer,
)
from schools.models import Constituency, DUN, School


# --- School API ---


class SchoolListView(ListAPIView):
    """List schools with optional filters.

    Filters: ?state=, ?ppd=, ?constituency=, ?skm=true, ?min_enrolment=, ?max_enrolment=
    """

    serializer_class = SchoolListSerializer

    def get_queryset(self):
        qs = School.objects.select_related("constituency").filter(is_active=True)
        state = self.request.query_params.get("state")
        ppd = self.request.query_params.get("ppd")
        constituency = self.request.query_params.get("constituency")
        skm = self.request.query_params.get("skm")
        min_enrolment = self.request.query_params.get("min_enrolment")
        max_enrolment = self.request.query_params.get("max_enrolment")

        if state:
            qs = qs.filter(state__iexact=state)
        if ppd:
            qs = qs.filter(ppd__iexact=ppd)
        if constituency:
            qs = qs.filter(constituency__code=constituency)
        if skm and skm.lower() == "true":
            qs = qs.filter(skm_eligible=True)
        if min_enrolment:
            qs = qs.filter(enrolment__gte=int(min_enrolment))
        if max_enrolment:
            qs = qs.filter(enrolment__lte=int(max_enrolment))
        return qs


class SchoolDetailView(RetrieveAPIView):
    """Retrieve a single school by MOE code."""

    serializer_class = SchoolDetailSerializer
    queryset = School.objects.select_related("constituency", "dun").prefetch_related("leaders")
    lookup_field = "moe_code"


class SchoolEditView(APIView):
    """GET/PUT /api/v1/schools/{moe_code}/edit/

    Requires Magic Link session. Rep must be associated with this school.
    GET returns editable fields. PUT updates and logs to AuditLog.
    """

    permission_classes = [IsMagicLinkAuthenticated]

    def _get_school(self, moe_code, request):
        """Get school and verify the rep is associated with it."""
        try:
            school = School.objects.get(moe_code=moe_code, is_active=True)
        except School.DoesNotExist:
            return None, Response(
                {"error": "School not found."}, status=status.HTTP_404_NOT_FOUND
            )

        if request.school_moe_code != moe_code:
            return None, Response(
                {"error": "You can only edit your own school."},
                status=status.HTTP_403_FORBIDDEN,
            )

        return school, None

    def get(self, request, moe_code):
        school, error = self._get_school(moe_code, request)
        if error:
            return error
        serializer = SchoolEditSerializer(school)
        return Response(serializer.data)

    def put(self, request, moe_code):
        school, error = self._get_school(moe_code, request)
        if error:
            return error

        old_values = SchoolEditSerializer(school).data
        serializer = SchoolEditSerializer(school, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        # Save with verification timestamp
        school = serializer.save(
            last_verified=timezone.now(),
            verified_by=request.school_contact.email,
        )

        # Log to AuditLog
        new_values = SchoolEditSerializer(school).data
        changed = {
            k: {"old": old_values[k], "new": new_values[k]}
            for k in new_values
            if old_values.get(k) != new_values[k]
            and k not in ("last_verified", "verified_by")
        }
        AuditLog.objects.create(
            action="update",
            target_type="School",
            target_id=moe_code,
            detail={"changed_fields": changed, "contact": request.school_contact.email},
            ip_address=request.META.get("REMOTE_ADDR"),
        )

        return Response(SchoolEditSerializer(school).data)


class SchoolConfirmView(APIView):
    """POST /api/v1/schools/{moe_code}/confirm/

    Quick 2-click confirmation: updates last_verified without editing fields.
    Requires Magic Link session for this school.
    """

    permission_classes = [IsMagicLinkAuthenticated]

    def post(self, request, moe_code):
        try:
            school = School.objects.get(moe_code=moe_code, is_active=True)
        except School.DoesNotExist:
            return Response(
                {"error": "School not found."}, status=status.HTTP_404_NOT_FOUND
            )

        if request.school_moe_code != moe_code:
            return Response(
                {"error": "You can only confirm your own school."},
                status=status.HTTP_403_FORBIDDEN,
            )

        now = timezone.now()
        school.last_verified = now
        school.verified_by = request.school_contact.email
        school.save(update_fields=["last_verified", "verified_by", "updated_at"])

        AuditLog.objects.create(
            action="confirm",
            target_type="School",
            target_id=moe_code,
            detail={"contact": request.school_contact.email},
            ip_address=request.META.get("REMOTE_ADDR"),
        )

        return Response({
            "message": "School data confirmed.",
            "last_verified": now.isoformat(),
            "verified_by": request.school_contact.email,
        })


# --- Constituency API ---


class ConstituencyListView(ListAPIView):
    """List constituencies with optional state filter.

    Filters: ?state=
    """

    serializer_class = ConstituencyListSerializer

    def get_queryset(self):
        qs = Constituency.objects.annotate(
            school_count=Count("schools", filter=Q(schools__is_active=True))
        ).order_by("code")
        state = self.request.query_params.get("state")
        if state:
            qs = qs.filter(state__iexact=state)
        return qs


class ConstituencyDetailView(RetrieveAPIView):
    """Retrieve a single constituency with nested schools and scorecard."""

    serializer_class = ConstituencyDetailSerializer
    queryset = Constituency.objects.prefetch_related(
        "schools", "scorecards",
    )
    lookup_field = "code"


# --- DUN API ---


class DUNListView(ListAPIView):
    """List DUNs with optional filters.

    Filters: ?state=, ?constituency=
    """

    serializer_class = DUNListSerializer

    def get_queryset(self):
        qs = DUN.objects.select_related("constituency")
        state = self.request.query_params.get("state")
        constituency = self.request.query_params.get("constituency")
        if state:
            qs = qs.filter(state__iexact=state)
        if constituency:
            qs = qs.filter(constituency__code=constituency)
        return qs


class DUNDetailView(RetrieveAPIView):
    """Retrieve a single DUN with nested schools."""

    serializer_class = DUNDetailSerializer
    queryset = DUN.objects.select_related("constituency").prefetch_related("schools")


# --- Search API ---


class SearchView(APIView):
    """Search across schools, constituencies, and MPs.

    Query: ?q=<search term>
    Returns up to 10 results per category.
    """

    def get(self, request):
        q = request.query_params.get("q", "").strip()
        if len(q) < 2:
            return Response({"error": "Query must be at least 2 characters"}, status=400)

        schools = School.objects.filter(
            Q(name__icontains=q) | Q(short_name__icontains=q) | Q(moe_code__icontains=q),
            is_active=True,
        ).select_related("constituency")[:10]

        constituencies = Constituency.objects.filter(
            Q(name__icontains=q) | Q(code__icontains=q) | Q(mp_name__icontains=q)
        )[:10]

        return Response({
            "schools": SchoolListSerializer(schools, many=True).data,
            "constituencies": ConstituencyListSerializer(
                constituencies.annotate(
                    school_count=Count("schools", filter=Q(schools__is_active=True))
                ),
                many=True,
            ).data,
        })


class NationalStatsView(APIView):
    """Return aggregate statistics for all active Tamil schools."""

    def get(self, request):
        schools = School.objects.filter(is_active=True)
        stats = schools.aggregate(
            total_schools=Count("moe_code"),
            total_students=Sum("enrolment"),
            total_teachers=Sum("teacher_count"),
            total_preschool=Sum("preschool_enrolment"),
            total_special_needs=Sum("special_enrolment"),
            states=Count("state", distinct=True),
            schools_under_30_students=Count(
                "moe_code", filter=Q(enrolment__lt=30)
            ),
        )
        stats["total_students"] = stats["total_students"] or 0
        stats["total_teachers"] = stats["total_teachers"] or 0
        stats["total_preschool"] = stats["total_preschool"] or 0
        stats["total_special_needs"] = stats["total_special_needs"] or 0
        stats["constituencies_with_schools"] = (
            schools.values("constituency__code")
            .exclude(constituency__isnull=True)
            .distinct()
            .count()
        )
        return Response(stats)


class ConstituencyGeoJSONView(APIView):
    """Return all constituency boundaries as a GeoJSON FeatureCollection."""

    def get(self, request):
        constituencies = Constituency.objects.exclude(boundary_wkt="").only(
            "code", "name", "state", "mp_name", "mp_party", "boundary_wkt",
        )
        features = []
        for c in constituencies:
            feature = to_feature(
                c.boundary_wkt,
                {
                    "code": c.code,
                    "name": c.name,
                    "state": c.state,
                    "mp_name": c.mp_name,
                    "mp_party": c.mp_party,
                },
            )
            if feature:
                features.append(feature)
        return Response(to_feature_collection(features))


class ConstituencyGeoJSONDetailView(APIView):
    """Return a single constituency boundary as GeoJSON."""

    def get(self, request, code):
        try:
            c = Constituency.objects.get(code=code)
        except Constituency.DoesNotExist:
            return Response({"error": "Constituency not found"}, status=404)

        if not c.boundary_wkt:
            return Response({"error": "No boundary data available"}, status=404)

        feature = to_feature(
            c.boundary_wkt,
            {
                "code": c.code,
                "name": c.name,
                "state": c.state,
                "mp_name": c.mp_name,
                "mp_party": c.mp_party,
                "mp_coalition": c.mp_coalition,
                "indian_population": c.indian_population,
                "indian_percentage": float(c.indian_percentage) if c.indian_percentage else None,
            },
        )
        if not feature:
            return Response({"error": "Invalid boundary data"}, status=500)
        return Response(feature)


class DUNGeoJSONView(APIView):
    """Return all DUN boundaries as a GeoJSON FeatureCollection."""

    def get(self, request):
        state = request.query_params.get("state")
        constituency = request.query_params.get("constituency")

        qs = DUN.objects.exclude(boundary_wkt="").select_related("constituency").only(
            "id", "code", "name", "state", "constituency__code",
            "constituency__name", "adun_name", "adun_party", "boundary_wkt",
        )
        if state:
            qs = qs.filter(state__iexact=state)
        if constituency:
            qs = qs.filter(constituency__code=constituency)

        features = []
        for d in qs:
            feature = to_feature(
                d.boundary_wkt,
                {
                    "id": d.id,
                    "code": d.code,
                    "name": d.name,
                    "state": d.state,
                    "constituency_code": d.constituency.code,
                    "constituency_name": d.constituency.name,
                    "adun_name": d.adun_name,
                    "adun_party": d.adun_party,
                },
            )
            if feature:
                features.append(feature)
        return Response(to_feature_collection(features))


class DUNGeoJSONDetailView(APIView):
    """Return a single DUN boundary as GeoJSON."""

    def get(self, request, pk):
        try:
            d = DUN.objects.select_related("constituency").get(pk=pk)
        except DUN.DoesNotExist:
            return Response({"error": "DUN not found"}, status=404)

        if not d.boundary_wkt:
            return Response({"error": "No boundary data available"}, status=404)

        feature = to_feature(
            d.boundary_wkt,
            {
                "id": d.id,
                "code": d.code,
                "name": d.name,
                "state": d.state,
                "constituency_code": d.constituency.code,
                "constituency_name": d.constituency.name,
                "adun_name": d.adun_name,
                "adun_party": d.adun_party,
                "indian_population": d.indian_population,
                "indian_percentage": float(d.indian_percentage) if d.indian_percentage else None,
            },
        )
        if not feature:
            return Response({"error": "Invalid boundary data"}, status=500)
        return Response(feature)
