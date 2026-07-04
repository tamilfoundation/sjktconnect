"""API views for schools, constituencies, DUNs, and GeoJSON boundaries."""

import io
import logging
import os
import re

import qrcode
import requests as http_requests
from django.db.models import Count, Prefetch, Q, Sum
from django.http import HttpResponse
from django.utils import timezone

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

logger = logging.getLogger(__name__)

from accounts.permissions import IsProfileAuthenticated
from core.email_blocklist import is_blocked_email
from core.models import AuditLog
from schools.api.geojson import to_feature, to_feature_collection
from schools.services.revalidation import trigger_school_revalidate
from schools.api.serializers import (
    ConstituencyDetailSerializer,
    ConstituencyListSerializer,
    DUNDetailSerializer,
    DUNListSerializer,
    SchoolDetailSerializer,
    SchoolEditSerializer,
    SchoolLeaderAdminSerializer,
    SchoolListSerializer,
    SchoolMapSerializer,
)
from schools.models import Constituency, DUN, School, SchoolLeader, SchoolEnrolmentSnapshot
from outreach.models import SchoolImage


# --- School API ---

# Sprint 33 audit fix: reusable Prefetch objects that populate a filtered
# list on each School instance so serializers can read it without a per-row
# .filter().first() lookup. Without these the SchoolListSerializer.get_image_url
# path issues ~1 query per row on every 50-page list.
_primary_image_prefetch = Prefetch(
    "images",
    queryset=SchoolImage.objects.filter(is_primary=True),
    to_attr="_primary_images",
)
_all_images_prefetch = Prefetch(
    "images",
    queryset=SchoolImage.objects.order_by("-is_primary", "-created_at"),
    to_attr="_all_images_sorted",
)
_enrolment_snapshots_prefetch = Prefetch(
    "enrolment_snapshots",
    queryset=SchoolEnrolmentSnapshot.objects.order_by("snapshot_date"),
    to_attr="_ordered_snapshots",
)


class SchoolListView(ListAPIView):
    """List schools with optional filters.

    Filters: ?state=, ?ppd=, ?constituency=, ?skm=true, ?min_enrolment=, ?max_enrolment=
    """

    serializer_class = SchoolListSerializer

    def get_queryset(self):
        qs = School.objects.select_related("constituency", "dun").prefetch_related(_primary_image_prefetch).filter(is_active=True).defer("constituency__boundary_wkt", "dun__boundary_wkt")
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


class SchoolMapView(APIView):
    """Return all active schools with minimal fields for map display.

    Single non-paginated response (~50 KB vs ~550 KB from SchoolListView).
    """

    def get(self, request):
        schools = School.objects.filter(is_active=True).only(
            "moe_code", "short_name", "gps_lat", "gps_lng",
            "enrolment", "preschool_enrolment", "special_enrolment",
            "assistance_type", "location_type", "state",
        )
        return Response(SchoolMapSerializer(schools, many=True).data)


class SchoolDetailView(RetrieveAPIView):
    """Retrieve a single school by MOE code."""

    serializer_class = SchoolDetailSerializer
    queryset = School.objects.select_related("constituency", "dun").prefetch_related(
        "leaders",
        _primary_image_prefetch,
        _all_images_prefetch,
        _enrolment_snapshots_prefetch,
    ).defer("constituency__boundary_wkt", "dun__boundary_wkt")
    lookup_field = "moe_code"


class SchoolEditView(APIView):
    """GET/PUT /api/v1/schools/{moe_code}/edit/

    Requires Google OAuth session. The signed-in user must be either the
    school's admin (profile.admin_school == this school) or a SUPERADMIN.
    GET returns editable fields. PUT updates and logs to AuditLog.
    """

    permission_classes = [IsProfileAuthenticated]

    def _get_school(self, moe_code, request):
        """Get school and verify the profile is authorised for it."""
        try:
            school = School.objects.get(moe_code=moe_code, is_active=True)
        except School.DoesNotExist:
            return None, Response(
                {"error": "School not found."}, status=status.HTTP_404_NOT_FOUND
            )

        profile = request.user_profile
        is_superadmin = profile.role == "SUPERADMIN"
        is_school_admin = profile.admin_school_id == school.pk
        if not (is_superadmin or is_school_admin):
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

        profile = request.user_profile
        contact_email = profile.user.email

        old_values = SchoolEditSerializer(school).data
        # Sprint 28 follow-up: pass context so SchoolEditSerializer.update
        # can read request.session for the SUPERADMIN check that gates
        # gps_lat/gps_lng writes. Without context the override always
        # sees request=None and silently strips GPS edits (owner-
        # reported 2026-06-26: SUPERADMIN GPS edit didn't persist).
        serializer = SchoolEditSerializer(
            school, data=request.data, partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        school = serializer.save()

        # Log to AuditLog
        new_values = SchoolEditSerializer(school).data
        changed = {
            k: {"old": old_values[k], "new": new_values[k]}
            for k in new_values
            if old_values.get(k) != new_values[k]
        }
        AuditLog.objects.create(
            action="update",
            target_type="School",
            target_id=moe_code,
            detail={"changed_fields": changed, "contact": contact_email},
            ip_address=request.META.get("REMOTE_ADDR"),
        )

        # TD-21: server-side ISR revalidation. Replaces the previous
        # unauthenticated client-side trigger. No-ops if env vars unset.
        trigger_school_revalidate(school)

        return Response(SchoolEditSerializer(school).data)


# SchoolConfirmView removed Sprint 19 (2026-04-28). MOE data is the source
# of truth — there's nothing for school admins to "confirm". Future
# additions go through the Suggestion workflow (community/api/views.py).


# --- School Leader CRUD (Sprint 20) ---


def _can_edit_school_leaders(profile, school_pk: str) -> bool:
    """Permission gate for the leader CRUD endpoints.

    SUPERADMIN may edit any school's leaders. Other roles can edit
    only their own bound school. MODERATOR has no special privilege
    here — leadership is a school-internal concern, not platform
    moderation. Same shape as community._is_photo_approver.
    """
    if not profile:
        return False
    if profile.role == "SUPERADMIN":
        return True
    return bool(profile.admin_school_id and profile.admin_school_id == school_pk)


def _resolve_school_or_404(moe_code: str):
    """Fetch a School by moe_code or raise 404. Active-only; leaders for
    deactivated schools are out of scope."""
    try:
        return School.objects.get(moe_code=moe_code, is_active=True)
    except School.DoesNotExist:
        return None


@api_view(["POST"])
@permission_classes([IsProfileAuthenticated])
def school_leader_create_view(request, moe_code):
    """Create a new SchoolLeader for a school.

    POST /api/v1/schools/<moe_code>/leaders/
    Body: { "role": "headmaster", "name": "...", "phone": "...", "email": "..." }
    """
    school = _resolve_school_or_404(moe_code)
    if school is None:
        return Response({"detail": "School not found."}, status=status.HTTP_404_NOT_FOUND)

    if not _can_edit_school_leaders(request.user_profile, school.pk):
        return Response(
            {"detail": "Only SUPERADMIN or this school's bound admin can edit leaders."},
            status=status.HTTP_403_FORBIDDEN,
        )

    serializer = SchoolLeaderAdminSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    # Enforce one active leader per role per school. The DB constraint
    # would catch this too, but a friendly 409 beats a generic 500.
    role = serializer.validated_data.get("role")
    if SchoolLeader.objects.filter(school=school, role=role, is_active=True).exists():
        return Response(
            {
                "detail": f"This school already has an active {role}. "
                          "Update or remove the existing record first.",
                "code": "role_taken",
            },
            status=status.HTTP_409_CONFLICT,
        )

    leader = serializer.save(school=school)
    trigger_school_revalidate(school)  # TD-21
    return Response(
        SchoolLeaderAdminSerializer(leader).data,
        status=status.HTTP_201_CREATED,
    )


@api_view(["PATCH", "DELETE"])
@permission_classes([IsProfileAuthenticated])
def school_leader_detail_view(request, moe_code, leader_id):
    """Update or soft-delete a SchoolLeader.

    PATCH /api/v1/schools/<moe_code>/leaders/<leader_id>/  — name/phone/email
    DELETE /api/v1/schools/<moe_code>/leaders/<leader_id>/ — soft-delete (is_active=False)
    """
    school = _resolve_school_or_404(moe_code)
    if school is None:
        return Response({"detail": "School not found."}, status=status.HTTP_404_NOT_FOUND)

    if not _can_edit_school_leaders(request.user_profile, school.pk):
        return Response(
            {"detail": "Only SUPERADMIN or this school's bound admin can edit leaders."},
            status=status.HTTP_403_FORBIDDEN,
        )

    try:
        leader = SchoolLeader.objects.get(pk=leader_id, school=school, is_active=True)
    except SchoolLeader.DoesNotExist:
        return Response({"detail": "Leader not found."}, status=status.HTTP_404_NOT_FOUND)

    if request.method == "DELETE":
        leader.is_active = False
        leader.save(update_fields=["is_active", "updated_at"])
        trigger_school_revalidate(school)  # TD-21
        return Response(status=status.HTTP_204_NO_CONTENT)

    # PATCH
    serializer = SchoolLeaderAdminSerializer(leader, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    leader = serializer.save()
    trigger_school_revalidate(school)  # TD-21
    return Response(SchoolLeaderAdminSerializer(leader).data)


# --- Constituency API ---


class ConstituencyListView(ListAPIView):
    """List constituencies with optional state filter.

    Filters: ?state=
    """

    serializer_class = ConstituencyListSerializer

    def get_queryset(self):
        qs = Constituency.objects.defer("boundary_wkt").annotate(
            school_count=Count("schools", filter=Q(schools__is_active=True))
        ).order_by("code")
        state = self.request.query_params.get("state")
        if state:
            qs = qs.filter(state__iexact=state)
        return qs


class ConstituencyDetailView(RetrieveAPIView):
    """Retrieve a single constituency with nested schools and scorecard."""

    serializer_class = ConstituencyDetailSerializer
    queryset = Constituency.objects.defer("boundary_wkt").prefetch_related(
        Prefetch(
            "schools",
            queryset=School.objects.prefetch_related(_primary_image_prefetch),
        ),
        "scorecards",
    )
    lookup_field = "code"


# --- DUN API ---


class DUNListView(ListAPIView):
    """List DUNs with optional filters.

    Filters: ?state=, ?constituency=
    """

    serializer_class = DUNListSerializer

    def get_queryset(self):
        qs = DUN.objects.select_related("constituency").defer("boundary_wkt", "constituency__boundary_wkt")
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
    queryset = DUN.objects.select_related("constituency").prefetch_related(
        Prefetch(
            "schools",
            queryset=School.objects.prefetch_related(_primary_image_prefetch),
        ),
    ).defer("boundary_wkt", "constituency__boundary_wkt")


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

        # Normalise query: "SJKT" -> also search "SJK(T)" and vice versa
        q_normalised = re.sub(r"[()]", "", q)  # strip parentheses
        school_q = (
            Q(name__icontains=q) | Q(short_name__icontains=q) | Q(moe_code__icontains=q)
        )
        if q_normalised != q:
            school_q |= Q(name__icontains=q_normalised) | Q(short_name__icontains=q_normalised)
        elif "sjkt" in q.lower():
            # "SJKT" should also match "SJK(T)"
            q_with_parens = q.lower().replace("sjkt", "SJK(T)")
            school_q |= Q(name__icontains=q_with_parens) | Q(short_name__icontains=q_with_parens)

        schools = School.objects.filter(
            school_q, is_active=True,
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


@api_view(["GET"])
@permission_classes([AllowAny])
def duitnow_qr(request, moe_code):
    """Generate a DuitNow QR code PNG for a school's bank account."""
    try:
        school = School.objects.get(moe_code=moe_code)
    except School.DoesNotExist:
        return HttpResponse(status=404)

    if not school.bank_account_number:
        return HttpResponse(status=404)

    # DuitNow QR payload: account number + bank name
    qr_data = (
        f"Bank: {school.bank_name}\n"
        f"Account: {school.bank_account_number}\n"
        f"Name: {school.bank_account_name}"
    )

    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(qr_data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    return HttpResponse(buf.getvalue(), content_type="image/png")


class ContactThrottle(AnonRateThrottle):
    rate = "3/hour"


class ContactFormView(APIView):
    """Accept contact form submissions and send via Brevo."""

    throttle_classes = [ContactThrottle]

    BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"

    def post(self, request):
        # Honeypot: bots fill hidden fields, humans don't
        if request.data.get("website", "").strip():
            # Silently accept to not tip off the bot
            return Response({"status": "sent"})

        name = (request.data.get("name") or "").strip()
        email = (request.data.get("email") or "").strip()
        subject = (request.data.get("subject") or "").strip()
        message = (request.data.get("message") or "").strip()

        if not all([name, email, subject, message]):
            return Response(
                {"error": "All fields are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Sprint 22: bot-spam — silently swallow blocked-domain submissions
        # so the bot doesn't learn what we filter on. Same shape as honeypot.
        if is_blocked_email(email):
            logger.info("Contact form blocked: disposable/example domain %s", email)
            return Response({"status": "sent"})

        api_key = os.environ.get("BREVO_API_KEY")
        if not api_key:
            logger.info(
                "BREVO_API_KEY not set — logging contact form instead of sending.\n"
                "From: %s <%s>\nSubject: %s\nMessage: %s",
                name, email, subject, message,
            )
            return Response({"status": "sent"})

        try:
            resp = http_requests.post(
                self.BREVO_API_URL,
                headers={
                    "api-key": api_key,
                    "Content-Type": "application/json",
                },
                json={
                    "sender": {"name": "SJK(T) Connect", "email": "noreply@tamilschool.org"},
                    "to": [{"email": "info@tamilfoundation.org", "name": "Tamil Foundation"}],
                    "replyTo": {"email": email, "name": name},
                    "subject": f"[Contact] {subject}",
                    "htmlContent": (
                        f"<p><strong>From:</strong> {name} ({email})</p>"
                        f"<p><strong>Subject:</strong> {subject}</p>"
                        f"<hr><p>{message}</p>"
                    ),
                },
                timeout=10,
            )
            resp.raise_for_status()
        except Exception:
            logger.exception("Failed to send contact email via Brevo")
            return Response(
                {"error": "Failed to send message."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response({"status": "sent"})
