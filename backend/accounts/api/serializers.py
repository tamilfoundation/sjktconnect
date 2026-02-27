from rest_framework import serializers


class RequestMagicLinkSerializer(serializers.Serializer):
    email = serializers.EmailField()


class VerifyTokenSerializer(serializers.Serializer):
    school_moe_code = serializers.CharField(source="school.moe_code")
    school_name = serializers.CharField(source="school.short_name")
    email = serializers.EmailField()


class SchoolContactSerializer(serializers.Serializer):
    school_moe_code = serializers.CharField(source="school.moe_code")
    school_name = serializers.CharField(source="school.short_name")
    email = serializers.EmailField()
    name = serializers.CharField()
    role = serializers.CharField()
    verified_at = serializers.DateTimeField()
