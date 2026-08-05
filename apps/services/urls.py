from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.services.views import (
    AdminQuoteRequestViewSet,
    AdminServiceProviderViewSet,
    AdminServiceReviewViewSet,
    PortfolioImageManagementViewSet,
    ProviderProfileDeactivateView,
    ProviderProfileMeView,
    ProviderProfileSubmitView,
    ProviderProfileView,
    ProviderQuoteRequestViewSet,
    ProviderReviewViewSet,
    ProviderTradeManagementViewSet,
    PublicProviderReviewViewSet,
    PublicQuoteRequestCreateViewSet,
    PublicServiceProviderViewSet,
    ServiceAreaManagementViewSet,
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
router.register(
    "services/provider-profile/reviews",
    ProviderReviewViewSet,
    basename="service-provider-profile-reviews",
)
router.register(
    "services/admin/reviews",
    AdminServiceReviewViewSet,
    basename="service-admin-reviews",
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
    path("", include(router.urls)),
]
