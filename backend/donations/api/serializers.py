from rest_framework import serializers


class DonationCreateSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=1)
    donor_name = serializers.CharField(max_length=200)
    donor_email = serializers.EmailField()
    donor_phone = serializers.CharField(max_length=20, required=False, default="")
    message = serializers.CharField(required=False, default="", allow_blank=True)
