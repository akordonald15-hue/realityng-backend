import django_filters

from apps.payments.models import EscrowTransaction, PaymentDispute, PaymentMilestone, Transaction


class TransactionFilterSet(django_filters.FilterSet):
    class Meta:
        model = Transaction
        fields = ["status", "property", "buyer", "owner"]


class PaymentMilestoneFilterSet(django_filters.FilterSet):
    class Meta:
        model = PaymentMilestone
        fields = ["status", "transaction"]


class PaymentDisputeFilterSet(django_filters.FilterSet):
    class Meta:
        model = PaymentDispute
        fields = ["status", "transaction"]


class EscrowTransactionFilterSet(django_filters.FilterSet):
    class Meta:
        model = EscrowTransaction
        fields = [
            "status",
            "funding_status",
            "release_status",
            "refund_status",
            "reconciliation_status",
            "provider",
            "transaction",
        ]
