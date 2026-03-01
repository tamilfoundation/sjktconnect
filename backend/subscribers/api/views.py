from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from subscribers.services.subscriber_service import (
    get_preferences,
    subscribe,
    unsubscribe,
    update_preferences,
)

from .serializers import (
    PreferenceUpdateSerializer,
    SubscribeSerializer,
    SubscriberSerializer,
)


class SubscribeView(APIView):
    """
    POST /api/v1/subscribers/subscribe/

    Create a new subscriber with all preferences enabled by default.
    Idempotent — duplicate email returns 200, not 400.
    Reactivates previously unsubscribed users.
    """

    authentication_classes = []
    permission_classes = []

    def post(self, request):
        serializer = SubscribeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        subscriber, created = subscribe(
            email=serializer.validated_data["email"],
            name=serializer.validated_data.get("name", ""),
            organisation=serializer.validated_data.get("organisation", ""),
        )

        response_serializer = SubscriberSerializer(subscriber)
        http_status = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return Response(response_serializer.data, status=http_status)


class UnsubscribeView(APIView):
    """
    GET /api/v1/subscribers/unsubscribe/<token>/

    One-click unsubscribe via token from email footer.
    Idempotent — already unsubscribed returns 200.
    """

    authentication_classes = []
    permission_classes = []

    def get(self, request, token):
        subscriber = unsubscribe(token)
        if subscriber is None:
            return Response(
                {"detail": "Invalid unsubscribe link."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(
            {"detail": "You have been unsubscribed.", "email": subscriber.email},
            status=status.HTTP_200_OK,
        )


class PreferencesView(APIView):
    """
    GET /api/v1/subscribers/preferences/<token>/
    PUT /api/v1/subscribers/preferences/<token>/

    View or update subscription category preferences.
    """

    authentication_classes = []
    permission_classes = []

    def get(self, request, token):
        subscriber, preferences = get_preferences(token)
        if subscriber is None:
            return Response(
                {"detail": "Invalid preferences link."},
                status=status.HTTP_404_NOT_FOUND,
            )

        response_serializer = SubscriberSerializer(subscriber)
        return Response(response_serializer.data)

    def put(self, request, token):
        serializer = PreferenceUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        preference_dict = serializer.to_preference_dict()
        if not preference_dict:
            return Response(
                {"detail": "No preferences provided."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        subscriber, preferences = update_preferences(token, preference_dict)
        if subscriber is None:
            return Response(
                {"detail": "Invalid preferences link."},
                status=status.HTTP_404_NOT_FOUND,
            )

        response_serializer = SubscriberSerializer(subscriber)
        return Response(response_serializer.data)
