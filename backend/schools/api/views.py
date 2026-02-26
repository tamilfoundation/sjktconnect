"""GeoJSON API views for constituency and DUN boundaries."""

from rest_framework.response import Response
from rest_framework.views import APIView

from schools.api.geojson import to_feature, to_feature_collection
from schools.models import Constituency, DUN


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
