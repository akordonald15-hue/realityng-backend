from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.services.views import PublicServiceProviderViewSet, TradeCategoryViewSet

router = DefaultRouter()
router.register("services/categories", TradeCategoryViewSet, basename="service-categories")
router.register("services/providers", PublicServiceProviderViewSet, basename="service-providers")

urlpatterns = [
    path("", include(router.urls)),
]
