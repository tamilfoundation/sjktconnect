import logging
import os

from django.http import HttpResponse
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from donations.models import Donation
from donations import services
from .serializers import DonationCreateSerializer

logger = logging.getLogger(__name__)


@api_view(["POST"])
@permission_classes([AllowAny])
def create_donation(request):
    """Create a donation and return the Toyyib payment URL."""
    serializer = DonationCreateSerializer(data=request.data)

    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data

    donation = Donation(
        amount=data["amount"],
        donor_name=data["donor_name"],
        donor_email=data["donor_email"],
        donor_phone=data.get("donor_phone", ""),
        message=data.get("message", ""),
    )
    donation.generate_order_id()
    donation.save()

    frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:3000")
    backend_url = request.build_absolute_uri("/")[:-1]
    return_url = f"{frontend_url}/donate/thank-you?order_id={donation.order_id}"
    callback_url = f"{backend_url}/api/v1/donations/callback/"

    try:
        bill_code = services.create_bill(donation, return_url, callback_url)
        redirect_url = services.get_redirect_url(bill_code)
        return Response({"payment_url": redirect_url}, status=status.HTTP_201_CREATED)
    except Exception as e:
        logger.error("Failed to create Toyyib bill: %s", e)
        donation.status = "failed"
        donation.save()
        return Response(
            {"error": "Payment service unavailable"},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )


@api_view(["POST"])
@permission_classes([AllowAny])
def toyyib_callback(request):
    """Handle Toyyib Pay server-to-server callback."""
    try:
        services.process_callback(
            bill_code=request.POST.get("billcode", ""),
            status_id=request.POST.get("status_id", ""),
            order_id=request.POST.get("order_id", ""),
            refno=request.POST.get("refno", ""),
            reason=request.POST.get("reason", ""),
            amount=request.POST.get("amount", ""),
            received_hash=request.POST.get("hash", ""),
        )
    except ValueError as e:
        logger.warning("Callback error: %s", e)
    return HttpResponse("OK")


@api_view(["GET"])
@permission_classes([AllowAny])
def donation_status(request):
    """Check donation status by order_id."""
    order_id = request.query_params.get("order_id")
    if not order_id:
        return Response({"error": "order_id required"}, status=400)

    try:
        donation = Donation.objects.get(order_id=order_id)
    except Donation.DoesNotExist:
        return Response({"error": "Not found"}, status=404)

    return Response({
        "order_id": donation.order_id,
        "amount": str(donation.amount),
        "status": donation.status,
        "donor_name": donation.donor_name,
    })
