from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.properties.views import (
    DashboardActivityView,
    DashboardSummaryView,
    FavoriteViewSet,
    InquiryViewSet,
    PropertyViewSet,
    PublicPropertyViewSet,
    RentalApplicationViewSet,
    TransactionCenterView,
    ViewingViewSet,
)

router = DefaultRouter()
router.register("properties", PropertyViewSet, basename="properties")
router.register("public/properties", PublicPropertyViewSet, basename="public-properties")
router.register("favorites", FavoriteViewSet, basename="favorites")
router.register("inquiries", InquiryViewSet, basename="inquiries")
router.register("viewings", ViewingViewSet, basename="viewings")
router.register("applications", RentalApplicationViewSet, basename="applications")

urlpatterns = [
    path("dashboard/activity/", DashboardActivityView.as_view(), name="dashboard-activity"),
    path("dashboard/summary/", DashboardSummaryView.as_view(), name="dashboard-summary"),
    path("dashboard/transactions/", TransactionCenterView.as_view(), name="dashboard-transactions"),
    path("", include(router.urls)),
]
