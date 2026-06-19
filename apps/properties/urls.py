from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.properties.views import (
    DashboardSummaryView,
    FavoriteViewSet,
    PropertyViewSet,
    PublicPropertyViewSet,
)

router = DefaultRouter()
router.register("properties", PropertyViewSet, basename="properties")
router.register("public/properties", PublicPropertyViewSet, basename="public-properties")
router.register("favorites", FavoriteViewSet, basename="favorites")

urlpatterns = [
    path("dashboard/summary/", DashboardSummaryView.as_view(), name="dashboard-summary"),
    path("", include(router.urls)),
]
