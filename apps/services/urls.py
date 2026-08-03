from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.services.views import (
    AdminServiceProviderViewSet,
    PortfolioImageManagementViewSet,
    ProviderProfileDeactivateView,
    ProviderProfileMeView,
    ProviderProfileSubmitView,
    ProviderProfileView,
    ProviderTradeManagementViewSet,
    PublicServiceProviderViewSet,
    ServiceAreaManagementViewSet,
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

urlpatterns = [
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
