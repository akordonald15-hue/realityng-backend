from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.services.views import (
    AdminProviderAppealViewSet,
    AdminQuoteRequestViewSet,
    AdminServiceComplaintViewSet,
    AdminServiceProviderViewSet,
    AdminServiceReviewViewSet,
    AdminServicesDashboardView,
    CustomerServicesDashboardView,
    PortfolioImageManagementViewSet,
    ProviderAppealViewSet,
    ProviderComplaintViewSet,
    ProviderProfileDeactivateView,
    ProviderProfileMeView,
    ProviderProfileSubmitView,
    ProviderProfileView,
    ProviderQuoteRequestViewSet,
    ProviderReviewViewSet,
    ProviderServicesDashboardView,
    ProviderTradeManagementViewSet,
    PublicProviderReviewViewSet,
    PublicQuoteRequestCreateViewSet,
    PublicServiceProviderViewSet,
    ServiceAreaManagementViewSet,
    ServiceComplaintViewSet,
    ServiceReviewViewSet,
    TradeCategoryViewSet,
)

router = DefaultRouter()
router.register("services/categories", TradeCategoryViewSet, basename="service-categories")
router.register("services/providers", PublicServiceProviderViewSet, basename="service-providers")
router.register(
    "services/provider-profile/trades",
    ProviderTradeManagementViewSet,
    basename="service-provider-profile-trades",
)
router.register(
    "services/provider-profile/service-areas",
    ServiceAreaManagementViewSet,
    basename="service-provider-profile-service-areas",
)
router.register(
    "services/provider-profile/portfolio",
    PortfolioImageManagementViewSet,
    basename="service-provider-profile-portfolio",
)
router.register(
    "services/admin/providers",
    AdminServiceProviderViewSet,
    basename="service-admin-providers",
)
router.register(
    "services/provider-profile/quote-requests",
    ProviderQuoteRequestViewSet,
    basename="service-provider-profile-quote-requests",
)
router.register(
    "services/admin/quote-requests",
    AdminQuoteRequestViewSet,
    basename="service-admin-quote-requests",
)
router.register("services/reviews", ServiceReviewViewSet, basename="service-reviews")
router.register("services/complaints", ServiceComplaintViewSet, basename="service-complaints")
router.register(
    "services/provider-profile/reviews",
    ProviderReviewViewSet,
    basename="service-provider-profile-reviews",
)
router.register(
    "services/provider-profile/complaints",
    ProviderComplaintViewSet,
    basename="service-provider-profile-complaints",
)
router.register(
    "services/provider-profile/appeals",
    ProviderAppealViewSet,
    basename="service-provider-profile-appeals",
)
router.register(
    "services/admin/reviews",
    AdminServiceReviewViewSet,
    basename="service-admin-reviews",
)
router.register(
    "services/admin/complaints",
    AdminServiceComplaintViewSet,
    basename="service-admin-complaints",
)
router.register(
    "services/admin/appeals",
    AdminProviderAppealViewSet,
    basename="service-admin-appeals",
)

urlpatterns = [
    path(
        "services/providers/<slug:provider_slug>/reviews/",
        PublicProviderReviewViewSet.as_view({"get": "list"}),
        name="service-provider-reviews",
    ),
    path(
        "services/providers/<slug:provider_slug>/quote-requests/",
        PublicQuoteRequestCreateViewSet.as_view({"post": "create"}),
        name="service-provider-quote-request-create",
    ),
    path(
        "services/provider-profile/",
        ProviderProfileView.as_view(),
        name="service-provider-profile",
    ),
    path(
        "services/provider-profile/me/",
        ProviderProfileMeView.as_view(),
        name="service-provider-profile-me",
    ),
    path(
        "services/provider-profile/submit/",
        ProviderProfileSubmitView.as_view(),
        name="service-provider-profile-submit",
    ),
    path(
        "services/provider-profile/deactivate/",
        ProviderProfileDeactivateView.as_view(),
        name="service-provider-profile-deactivate",
    ),
    path(
        "services/dashboard/customer/",
        CustomerServicesDashboardView.as_view(),
        name="services-dashboard-customer",
    ),
    path(
        "services/dashboard/provider/",
        ProviderServicesDashboardView.as_view(),
        name="services-dashboard-provider",
    ),
    path(
        "services/dashboard/admin/",
        AdminServicesDashboardView.as_view(),
        name="services-dashboard-admin",
    ),
    path("", include(router.urls)),
]
