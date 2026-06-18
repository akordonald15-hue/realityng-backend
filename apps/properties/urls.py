from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.properties.views import PropertyViewSet, PublicPropertyViewSet

router = DefaultRouter()
router.register("properties", PropertyViewSet, basename="properties")
router.register("public/properties", PublicPropertyViewSet, basename="public-properties")

urlpatterns = [
    path("", include(router.urls)),
]
