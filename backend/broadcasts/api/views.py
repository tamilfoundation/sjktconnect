"""Brevo webhook endpoint for delivery event tracking."""

import hashlib
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

    Authentication: optional HMAC signature via BREVO_WEBHOOK_SECRET.
    If the secret is set, requests without a valid signature are rejected.
    """

    permission_classes = [AllowAny]
    authentication_classes = []  # No auth — Brevo can't send tokens

    def post(self, request):
        # Verify HMAC signature if secret is configured
        webhook_secret = os.environ.get("BREVO_WEBHOOK_SECRET", "")
        if webhook_secret:
            signature = request.headers.get("X-Sib-Signature", "")
            if not signature:
                logger.warning("Brevo webhook: missing signature header")
                return Response(status=status.HTTP_403_FORBIDDEN)

            expected = hmac.new(
                webhook_secret.encode(),
                request.body,
                hashlib.sha256,
            ).hexdigest()

            if not hmac.compare_digest(signature, expected):
                logger.warning("Brevo webhook: invalid signature")
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
