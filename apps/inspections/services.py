from __future__ import annotations

from django.db.models import Q

from apps.accounts.choices import RoleName
from apps.accounts.models import User
from apps.accounts.services import create_audit_log, user_has_role, user_is_admin
from apps.inspections.choices import (
    EvidenceVisibility,
    InspectorVerificationStatus,
    WalkthroughStatus,
)
from apps.inspections.models import InspectionRequest, InspectionTimelineEvent
from apps.properties.models import Property


def emit_inspection_event(
    *,
    actor: User | None,
    action: str,
    entity,
    metadata: dict | None = None,
) -> None:
    create_audit_log(actor=actor, action=action, entity=entity, metadata=metadata or {})


def create_timeline_event(
    *,
    inspection_request: InspectionRequest,
    event_type: str,
    actor: User | None = None,
    description: str = "",
    metadata: dict | None = None,
    is_internal: bool = False,
) -> InspectionTimelineEvent:
    return InspectionTimelineEvent.objects.create(
        inspection_request=inspection_request,
        event_type=event_type,
        actor=actor if actor and actor.is_authenticated else None,
        description=description,
        metadata=metadata or {},
        is_internal=is_internal,
    )


def user_can_upload_walkthrough(user: User, prop: Property) -> bool:
    """Conservative MVP policy until property management assignments exist.

    The product policy allows landlords, assigned agents, verified property
    managers, and admins. The current property schema has a single owner field
    and no assignment/management relationship, so non-owner agent/manager
    uploads are intentionally rejected rather than trusted by role alone.
    """
    if not user or not user.is_authenticated or user.is_suspended or not user.is_active:
        return False
    if user_is_admin(user):
        return True
    return prop.owner_id == user.id and (
        user_has_role(user, RoleName.LANDLORD) or user_has_role(user, RoleName.AGENT)
    )


def user_is_inspector(user: User) -> bool:
    if not user or not user.is_authenticated or not user.is_active or user.is_suspended:
        return False
    if user_is_admin(user):
        return True
    has_role = user_has_role(user, RoleName.INSPECTOR)
    profile = getattr(user, "inspector_profile", None)
    return bool(
        has_role
        and profile
        and profile.active
        and profile.verification_status == InspectorVerificationStatus.APPROVED
    )


def user_can_view_inspection(user: User, inspection: InspectionRequest) -> bool:
    if user_is_admin(user):
        return True
    if inspection.requester_id == user.id or inspection.property.owner_id == user.id:
        return True
    if inspection.assigned_inspector_id == user.id:
        return True
    return inspection.assignments.filter(inspector=user).exists()


def user_can_view_evidence(user: User, evidence) -> bool:
    report = evidence.inspection_report
    inspection = report.inspection_request
    if user_is_admin(user) or report.inspector_id == user.id:
        return True
    if evidence.visibility == EvidenceVisibility.REQUESTER_VISIBLE:
        return inspection.requester_id == user.id
    if evidence.visibility == EvidenceVisibility.PROPERTY_OWNER_VISIBLE:
        return inspection.property.owner_id == user.id
    return False


def inspection_queryset_for_user(user: User):
    from apps.inspections.models import InspectionRequest

    queryset = InspectionRequest.objects.select_related(
        "property",
        "property__owner",
        "requester",
        "assigned_inspector",
        "assigned_by",
    )
    if user_is_admin(user):
        return queryset
    return queryset.filter(
        Q(requester=user) | Q(property__owner=user) | Q(assigned_inspector=user)
    ).distinct()


def public_walkthrough_queryset():
    from apps.inspections.models import PropertyWalkthrough

    return PropertyWalkthrough.objects.filter(status=WalkthroughStatus.APPROVED).select_related(
        "property",
        "uploaded_by",
        "reviewed_by",
    )
