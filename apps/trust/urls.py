from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.trust.views import (
    AdminPropertyVerificationApproveView,
    AdminPropertyVerificationDetailView,
    AdminPropertyVerificationExpireView,
    AdminPropertyVerificationListView,
    AdminPropertyVerificationRejectView,
    AdminPropertyVerificationRequestInfoView,
    AdminPropertyVerificationSuspendView,
    AdminVerificationApproveView,
    AdminVerificationDetailView,
    AdminVerificationExpireView,
    AdminVerificationListView,
    AdminVerificationRejectView,
    AdminVerificationRequestInfoView,
    AdminVerificationSuspendView,
    PropertyVerificationViewSet,
    VerificationRequestViewSet,
)

router = DefaultRouter()
router.register("verifications", VerificationRequestViewSet, basename="verifications")
router.register(
    "property-verifications", PropertyVerificationViewSet, basename="property-verifications"
)

urlpatterns = [
    path("", include(router.urls)),
    path(
        "admin/verifications/",
        AdminVerificationListView.as_view(),
        name="admin-verifications-list",
    ),
    path(
        "admin/verifications/<uuid:pk>/",
        AdminVerificationDetailView.as_view(),
        name="admin-verification-detail",
    ),
    path(
        "admin/verifications/<uuid:pk>/approve/",
        AdminVerificationApproveView.as_view(),
        name="admin-verification-approve",
    ),
    path(
        "admin/verifications/<uuid:pk>/reject/",
        AdminVerificationRejectView.as_view(),
        name="admin-verification-reject",
    ),
    path(
        "admin/verifications/<uuid:pk>/request-info/",
        AdminVerificationRequestInfoView.as_view(),
        name="admin-verification-request-info",
    ),
    path(
        "admin/verifications/<uuid:pk>/suspend/",
        AdminVerificationSuspendView.as_view(),
        name="admin-verification-suspend",
    ),
    path(
        "admin/verifications/<uuid:pk>/expire/",
        AdminVerificationExpireView.as_view(),
        name="admin-verification-expire",
    ),
    path(
        "admin/property-verifications/",
        AdminPropertyVerificationListView.as_view(),
        name="admin-property-verifications-list",
    ),
    path(
        "admin/property-verifications/<uuid:pk>/",
        AdminPropertyVerificationDetailView.as_view(),
        name="admin-property-verification-detail",
    ),
    path(
        "admin/property-verifications/<uuid:pk>/approve/",
        AdminPropertyVerificationApproveView.as_view(),
        name="admin-property-verification-approve",
    ),
    path(
        "admin/property-verifications/<uuid:pk>/reject/",
        AdminPropertyVerificationRejectView.as_view(),
        name="admin-property-verification-reject",
    ),
    path(
        "admin/property-verifications/<uuid:pk>/request-info/",
        AdminPropertyVerificationRequestInfoView.as_view(),
        name="admin-property-verification-request-info",
    ),
    path(
        "admin/property-verifications/<uuid:pk>/suspend/",
        AdminPropertyVerificationSuspendView.as_view(),
        name="admin-property-verification-suspend",
    ),
    path(
        "admin/property-verifications/<uuid:pk>/expire/",
        AdminPropertyVerificationExpireView.as_view(),
        name="admin-property-verification-expire",
    ),
]
