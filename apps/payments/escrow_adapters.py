from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass
from decimal import Decimal

from django.conf import settings

from apps.payments.choices import EscrowIntegrationMode
from apps.payments.models import EscrowProvider


@dataclass(frozen=True)
class ProviderStatusSnapshot:
    amount: Decimal
    status: str
    reference: str = ""


class EscrowProviderAdapter:
    """Provider abstraction for escrow orchestration.

    This interface deliberately avoids real money movement in Sprint 14.1.
    Production adapters must be added only after partner/legal approval.
    """

    def __init__(self, provider: EscrowProvider):
        self.provider = provider

    def create_escrow(self, *, escrow) -> str:
        return escrow.external_reference or f"{self.provider.slug}-{escrow.id}"

    def request_release(self, *, release) -> str:
        return release.provider_instruction_id or f"release-{release.id}"

    def request_refund(self, *, refund) -> str:
        return refund.provider_instruction_id or f"refund-{refund.id}"

    def fetch_status(self, *, escrow) -> ProviderStatusSnapshot:
        return ProviderStatusSnapshot(
            amount=escrow.confirmed_funded_amount,
            status=escrow.status,
            reference=escrow.external_reference,
        )

    def verify_webhook(self, *, body: bytes, signature: str | None) -> bool:
        secret = self._webhook_secret()
        if not secret:
            return self.provider.integration_mode == EscrowIntegrationMode.MANUAL and not signature
        if not signature:
            return False
        expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)

    def _webhook_secret(self) -> str:
        env_name = f"ESCROW_{self.provider.slug.upper().replace('-', '_')}_WEBHOOK_SECRET"
        return getattr(settings, env_name, "")


class ManualEscrowProviderAdapter(EscrowProviderAdapter):
    pass


class SandboxEscrowProviderAdapter(EscrowProviderAdapter):
    pass


def get_escrow_provider_adapter(provider: EscrowProvider) -> EscrowProviderAdapter:
    if provider.integration_mode == EscrowIntegrationMode.SANDBOX:
        return SandboxEscrowProviderAdapter(provider)
    return ManualEscrowProviderAdapter(provider)
