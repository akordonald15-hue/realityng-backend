from django.conf import settings
from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.serializers import HealthSerializer


class HealthCheckView(APIView):
    authentication_classes: list = []
    permission_classes: list = []
    throttle_classes: list = []

    @extend_schema(responses={200: HealthSerializer})
    def get(self, request):
        return Response(
            {
                "status": "ok",
                "service": "realityng-backend",
                "version": settings.SPECTACULAR_SETTINGS["VERSION"],
            }
        )
