from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.trust.views import PropertyVerificationViewSet, VerificationRequestViewSet

router = DefaultRouter()
router.register("verifications", VerificationRequestViewSet, basename="verifications")
router.register(
    "property-verifications", PropertyVerificationViewSet, basename="property-verifications"
)

urlpatterns = [
    path("", include(router.urls)),
]
