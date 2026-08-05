from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.inspections.views import (
    AdminInspectionDashboardView,
    AdminInspectionReportViewSet,
    AdminInspectionRequestViewSet,
    AdminWalkthroughViewSet,
    CustomerInspectionDashboardView,
    InspectionAssignmentViewSet,
    InspectionEvidenceViewSet,
    InspectionReportViewSet,
    InspectionRequestViewSet,
    InspectorDashboardView,
    InspectorProfileViewSet,
    PropertyWalkthroughManagementViewSet,
    PublicPropertyWalkthroughViewSet,
)

router = DefaultRouter()
router.register("inspections/requests", InspectionRequestViewSet, basename="inspection-requests")
router.register(
    "inspections/assignments", InspectionAssignmentViewSet, basename="inspection-assignments"
)
router.register("inspections/reports", InspectionReportViewSet, basename="inspection-reports")
router.register("inspections/evidence", InspectionEvidenceViewSet, basename="inspection-evidence")
router.register(
    "inspections/walkthroughs",
    PropertyWalkthroughManagementViewSet,
    basename="inspection-walkthroughs",
)
router.register(
    "inspections/admin/requests",
    AdminInspectionRequestViewSet,
    basename="inspection-admin-requests",
)
router.register(
    "inspections/admin/walkthroughs",
    AdminWalkthroughViewSet,
    basename="inspection-admin-walkthroughs",
)
router.register(
    "inspections/admin/reports", AdminInspectionReportViewSet, basename="inspection-admin-reports"
)
router.register(
    "inspections/admin/inspectors", InspectorProfileViewSet, basename="inspection-admin-inspectors"
)

urlpatterns = [
    path(
        "inspections/properties/<uuid:property_id>/walkthroughs/",
        PropertyWalkthroughManagementViewSet.as_view({"post": "create"}),
        name="inspection-property-walkthrough-create",
    ),
    path(
        "inspections/properties/<uuid:property_id>/walkthroughs/public/",
        PublicPropertyWalkthroughViewSet.as_view({"get": "list"}),
        name="inspection-property-walkthrough-public",
    ),
    path(
        "inspections/requests/<uuid:request_id>/report/",
        InspectionReportViewSet.as_view({"post": "create", "get": "by_request"}),
        name="inspection-request-report-create",
    ),
    path(
        "inspections/dashboard/customer/",
        CustomerInspectionDashboardView.as_view(),
        name="inspection-dashboard-customer",
    ),
    path(
        "inspections/dashboard/inspector/",
        InspectorDashboardView.as_view(),
        name="inspection-dashboard-inspector",
    ),
    path(
        "inspections/dashboard/admin/",
        AdminInspectionDashboardView.as_view(),
        name="inspection-dashboard-admin",
    ),
    path("", include(router.urls)),
]
