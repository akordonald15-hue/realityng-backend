from django.conf import settings
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthCheckView(APIView):
    authentication_classes: list = []
    permission_classes: list = []

    def get(self, request):
        return Response(
            {
                "status": "ok",
                "service": "realityng-backend",
                "version": settings.SPECTACULAR_SETTINGS["VERSION"],
            }
        )

