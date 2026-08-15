from rest_framework.routers import DefaultRouter

from apps.payments.views import (
    AdminFinancingApplicationViewSet,
    EscrowProviderViewSet,
    EscrowTransactionViewSet,
    EscrowWebhookViewSet,
    FinancingApplicationViewSet,
    FinancingDocumentViewSet,
    FinancingOfferViewSet,
    FinancingProductViewSet,
    PaymentDisputeViewSet,
    PaymentMilestoneViewSet,
    PaymentProofViewSet,
    TransactionViewSet,
)

router = DefaultRouter()
router.register("transactions", TransactionViewSet, basename="transaction")
router.register("payment-milestones", PaymentMilestoneViewSet, basename="payment-milestone")
router.register("payment-proofs", PaymentProofViewSet, basename="payment-proof")
router.register("payment-disputes", PaymentDisputeViewSet, basename="payment-dispute")
router.register("escrow-providers", EscrowProviderViewSet, basename="escrow-provider")
router.register("payment-escrows", EscrowTransactionViewSet, basename="payment-escrow")
router.register("escrow-webhooks", EscrowWebhookViewSet, basename="escrow-webhook")
router.register("financing-products", FinancingProductViewSet, basename="financing-product")
router.register(
    "financing-applications",
    FinancingApplicationViewSet,
    basename="financing-application",
)
router.register(
    "financing-documents",
    FinancingDocumentViewSet,
    basename="financing-document",
)
router.register("financing-offers", FinancingOfferViewSet, basename="financing-offer")
router.register(
    "admin-financing-applications",
    AdminFinancingApplicationViewSet,
    basename="admin-financing-application",
)

urlpatterns = router.urls
