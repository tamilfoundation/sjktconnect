"""Brevo webhook endpoint for delivery event tracking."""

import hmac
import logging
import os

from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from broadcasts.services.webhook import process_brevo_event

logger = logging.getLogger(__name__)


class BrevoWebhookView(APIView):
    """
    Receive Brevo transactional webhook events.

    POST /api/v1/webhooks/brevo/

    Brevo sends JSON payloads for delivery events: delivered, opened,
    click, hard_bounce, soft_bounce, spam, unsubscribed.

    Authentication: Bearer token via BREVO_WEBHOOK_SECRET. Audit 2026-07-01
    switched from HMAC to Bearer — Brevo's outbound-webhook UI only exposes
    "No authentication / Basic / Token" and does not sign the payload.
    Requests without a matching Bearer token return 403.
    """

    permission_classes = [AllowAny]
    authentication_classes = []  # No DRF auth — token checked manually below

    def post(self, request):
        webhook_secret = os.environ.get("BREVO_WEBHOOK_SECRET", "")
        if webhook_secret:
            auth = request.headers.get("Authorization", "")
            if not auth.startswith("Bearer "):
                logger.warning("Brevo webhook: missing Bearer authorization")
                return Response(status=status.HTTP_403_FORBIDDEN)

            supplied = auth[len("Bearer "):].strip()
            if not hmac.compare_digest(supplied, webhook_secret):
                logger.warning("Brevo webhook: invalid Bearer token")
                return Response(status=status.HTTP_403_FORBIDDEN)

        # Brevo may send a single event or a list
        data = request.data
        events = data if isinstance(data, list) else [data]

        processed = 0
        for event in events:
            if process_brevo_event(event):
                processed += 1

        return Response(
            {"processed": processed},
            status=status.HTTP_200_OK,
        )
