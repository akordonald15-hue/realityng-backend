from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.construction.views import (
    AdminConstructionDashboardView,
    ConstructionEvidenceViewSet,
    ConstructionMilestoneViewSet,
    ConstructionProgressUpdateViewSet,
    ConstructionProjectViewSet,
    OwnerConstructionDashboardView,
    ProjectManagerConstructionDashboardView,
    ProjectStakeholderViewSet,
)

router = DefaultRouter()
router.register(
    "construction/projects", ConstructionProjectViewSet, basename="construction-projects"
)

urlpatterns = [
    path(
        "construction/dashboard/owner/",
        OwnerConstructionDashboardView.as_view(),
        name="construction-dashboard-owner",
    ),
    path(
        "construction/dashboard/operations/",
        ProjectManagerConstructionDashboardView.as_view(),
        name="construction-dashboard-operations",
    ),
    path(
        "construction/dashboard/admin/",
        AdminConstructionDashboardView.as_view(),
        name="construction-dashboard-admin",
    ),
    path(
        "construction/projects/<slug:project_slug>/stakeholders/",
        ProjectStakeholderViewSet.as_view({"get": "list", "post": "create"}),
        name="construction-project-stakeholders-list",
    ),
    path(
        "construction/projects/<slug:project_slug>/stakeholders/<uuid:pk>/",
        ProjectStakeholderViewSet.as_view(
            {"get": "retrieve", "patch": "partial_update", "delete": "destroy"}
        ),
        name="construction-project-stakeholders-detail",
    ),
    path(
        "construction/projects/<slug:project_slug>/stakeholders/<uuid:pk>/accept/",
        ProjectStakeholderViewSet.as_view({"post": "accept"}),
        name="construction-project-stakeholders-accept",
    ),
    path(
        "construction/projects/<slug:project_slug>/milestones/",
        ConstructionMilestoneViewSet.as_view({"get": "list", "post": "create"}),
        name="construction-project-milestones-list",
    ),
    path(
        "construction/projects/<slug:project_slug>/milestones/<uuid:pk>/",
        ConstructionMilestoneViewSet.as_view(
            {"get": "retrieve", "patch": "partial_update", "delete": "destroy"}
        ),
        name="construction-project-milestones-detail",
    ),
    path(
        "construction/projects/<slug:project_slug>/milestones/<uuid:pk>/progress/",
        ConstructionMilestoneViewSet.as_view({"post": "progress"}),
        name="construction-project-milestones-progress",
    ),
    path(
        "construction/projects/<slug:project_slug>/milestones/<uuid:pk>/request-inspection/",
        ConstructionMilestoneViewSet.as_view({"post": "request_inspection"}),
        name="construction-project-milestones-request-inspection",
    ),
    path(
        "construction/projects/<slug:project_slug>/updates/",
        ConstructionProgressUpdateViewSet.as_view({"get": "list", "post": "create"}),
        name="construction-project-updates-list",
    ),
    path(
        "construction/projects/<slug:project_slug>/updates/<uuid:pk>/",
        ConstructionProgressUpdateViewSet.as_view(
            {"get": "retrieve", "patch": "partial_update", "delete": "destroy"}
        ),
        name="construction-project-updates-detail",
    ),
    path(
        "construction/projects/<slug:project_slug>/updates/<uuid:pk>/submit/",
        ConstructionProgressUpdateViewSet.as_view({"post": "submit"}),
        name="construction-project-updates-submit",
    ),
    path(
        "construction/projects/<slug:project_slug>/updates/<uuid:pk>/approve/",
        ConstructionProgressUpdateViewSet.as_view({"post": "approve"}),
        name="construction-project-updates-approve",
    ),
    path(
        "construction/projects/<slug:project_slug>/updates/<uuid:pk>/reject/",
        ConstructionProgressUpdateViewSet.as_view({"post": "reject"}),
        name="construction-project-updates-reject",
    ),
    path(
        "construction/projects/<slug:project_slug>/evidence/",
        ConstructionEvidenceViewSet.as_view({"get": "list", "post": "create"}),
        name="construction-project-evidence-list",
    ),
    path(
        "construction/projects/<slug:project_slug>/evidence/<uuid:pk>/",
        ConstructionEvidenceViewSet.as_view({"get": "retrieve", "delete": "destroy"}),
        name="construction-project-evidence-detail",
    ),
    path(
        "construction/projects/<slug:project_slug>/evidence/<uuid:pk>/signed-url/",
        ConstructionEvidenceViewSet.as_view({"get": "signed_url"}),
        name="construction-project-evidence-signed-url",
    ),
    path("", include(router.urls)),
]
