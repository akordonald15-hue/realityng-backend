from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.properties.views import (
    DashboardSummaryView,
    FavoriteViewSet,
    InquiryViewSet,
    PropertyViewSet,
    PublicPropertyViewSet,
    ViewingViewSet,
)

router = DefaultRouter()
router.register("properties", PropertyViewSet, basename="properties")
router.register("public/properties", PublicPropertyViewSet, basename="public-properties")
router.register("favorites", FavoriteViewSet, basename="favorites")
router.register("inquiries", InquiryViewSet, basename="inquiries")
router.register("viewings", ViewingViewSet, basename="viewings")

urlpatterns = [
    path("dashboard/summary/", DashboardSummaryView.as_view(), name="dashboard-summary"),
    path("", include(router.urls)),
]
