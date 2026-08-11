from __future__ import annotations

from decimal import Decimal

from django.db import transaction

from apps.accounts.models import User
from apps.accounts.services import create_audit_log, user_is_admin
from apps.construction.choices import (
    ConstructionMilestoneStatus,
    ConstructionProgressUpdateStatus,
    ProjectAccessLevel,
    ProjectStakeholderRole,
    ProjectStakeholderStatus,
)
from apps.construction.models import (
    ConstructionMilestone,
    ConstructionProgressUpdate,
    ConstructionProject,
    ConstructionTimelineEvent,
    ProjectStakeholder,
)
from apps.properties.choices import PropertyAssignmentCapability
from apps.properties.models import Property
from apps.properties.services import user_has_property_capability

MANAGER_ACCESS_LEVELS = {
    ProjectAccessLevel.MANAGER,
    ProjectAccessLevel.OWNER,
}
OPERATOR_ACCESS_LEVELS = {
    ProjectAccessLevel.OPERATOR,
    ProjectAccessLevel.MANAGER,
    ProjectAccessLevel.OWNER,
}


def emit_construction_event(
    *,
    actor: User | None,
    action: str,
    entity,
    metadata: dict | None = None,
) -> None:
    create_audit_log(actor=actor, action=action, entity=entity, metadata=metadata or {})


def create_project_timeline_event(
    *,
    project: ConstructionProject,
    event_type: str,
    actor: User | None = None,
    milestone: ConstructionMilestone | None = None,
    description: str = "",
    metadata: dict | None = None,
    is_internal: bool = False,
) -> ConstructionTimelineEvent:
    return ConstructionTimelineEvent.objects.create(
        project=project,
        milestone=milestone,
        event_type=event_type,
        actor=actor if actor and actor.is_authenticated else None,
        description=description,
        metadata=metadata or {},
        is_internal=is_internal,
    )


def user_can_create_project_for_property(user: User, prop: Property) -> bool:
    if not user or not user.is_authenticated or user.is_suspended or not user.is_active:
        return False
    if user_is_admin(user) or prop.owner_id == user.id:
        return True
    return user_has_property_capability(
        user,
        prop,
        PropertyAssignmentCapability.MANAGE_CONSTRUCTION,
    )


def _active_stakeholder(user: User, project: ConstructionProject) -> ProjectStakeholder | None:
    if not user or not user.is_authenticated:
        return None
    return project.stakeholders.filter(
        user=user,
        status=ProjectStakeholderStatus.ACTIVE,
    ).first()


def user_can_view_project(user: User, project: ConstructionProject) -> bool:
    if not user or not user.is_authenticated or user.is_suspended or not user.is_active:
        return False
    if user_is_admin(user) or project.owner_id == user.id or project.created_by_id == user.id:
        return True
    if project.project_manager_id == user.id:
        return True
    if _active_stakeholder(user, project):
        return True
    return user_has_property_capability(
        user,
        project.property,
        PropertyAssignmentCapability.VIEW_PRIVATE_PROJECT_DATA,
    )


def user_can_manage_project(user: User, project: ConstructionProject) -> bool:
    if user_is_admin(user) or project.owner_id == user.id or project.project_manager_id == user.id:
        return True
    stakeholder = _active_stakeholder(user, project)
    if stakeholder and stakeholder.access_level in MANAGER_ACCESS_LEVELS:
        return True
    return user_has_property_capability(
        user,
        project.property,
        PropertyAssignmentCapability.MANAGE_CONSTRUCTION,
    )


def user_can_submit_project_update(user: User, project: ConstructionProject) -> bool:
    if user_can_manage_project(user, project):
        return True
    stakeholder = _active_stakeholder(user, project)
    return bool(
        stakeholder
        and (
            stakeholder.access_level in OPERATOR_ACCESS_LEVELS
            or stakeholder.stakeholder_role
            in [ProjectStakeholderRole.PROJECT_MANAGER, ProjectStakeholderRole.CONTRACTOR]
        )
    )


def user_can_view_evidence(user: User, evidence) -> bool:
    if user_is_admin(user):
        return True
    if evidence.visibility == "admins_only":
        return False
    if evidence.visibility == "owner_and_admins":
        return evidence.project.owner_id == user.id
    return user_can_view_project(user, evidence.project)


def calculate_project_progress(project: ConstructionProject) -> Decimal:
    milestones = project.milestones.exclude(
        status__in=[
            ConstructionMilestoneStatus.SKIPPED,
            ConstructionMilestoneStatus.CANCELLED,
        ]
    )
    total_weight = sum((milestone.weight for milestone in milestones), Decimal("0.00"))
    if total_weight <= 0:
        return Decimal("0.00")
    weighted_total = sum(milestone.progress_percent * milestone.weight for milestone in milestones)
    value = weighted_total / total_weight
    return min(max(value, Decimal("0.00")), Decimal("100.00")).quantize(Decimal("0.01"))


@transaction.atomic
def apply_approved_progress_update(update: ConstructionProgressUpdate) -> None:
    if update.status != ConstructionProgressUpdateStatus.APPROVED:
        return
    if update.milestone_id:
        milestone = update.milestone
        milestone.progress_percent = update.current_progress
        if update.current_progress == Decimal("100.00"):
            milestone.mark_completed_if_allowed()
        else:
            milestone.status = ConstructionMilestoneStatus.IN_PROGRESS
            milestone.save(update_fields=["progress_percent", "status", "updated_at"])
    project = update.project
    project.overall_progress = calculate_project_progress(project)
    project.save(update_fields=["overall_progress", "updated_at"])
    create_project_timeline_event(
        project=project,
        milestone=update.milestone,
        event_type="ConstructionProgressApproved",
        actor=update.reviewed_by,
        description=f"Progress update approved: {update.title}",
        metadata={"progress": str(update.current_progress)},
    )
