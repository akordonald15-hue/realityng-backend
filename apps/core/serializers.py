from rest_framework import serializers


class HealthSerializer(serializers.Serializer):
    status = serializers.CharField()
    service = serializers.CharField()
    version = serializers.CharField()

