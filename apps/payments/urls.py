from rest_framework.routers import DefaultRouter

from apps.payments.views import (
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

urlpatterns = router.urls
