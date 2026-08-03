from __future__ import annotations

from apps.accounts.models import User
from apps.accounts.services import create_audit_log


def emit_service_event(
    *,
    actor: User | None,
    action: str,
    entity,
    metadata: dict | None = None,
) -> None:
    create_audit_log(
        actor=actor,
        action=action,
        entity=entity,
        metadata=metadata or {},
    )
