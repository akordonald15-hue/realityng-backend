from __future__ import annotations

from django.conf import settings
from django.db import transaction

from apps.accounts.choices import ADMIN_ONLY_ROLES, AUTO_APPROVED_ROLES, RoleName, UserRoleStatus
from apps.accounts.models import AuditLog, Role, User, UserProfile, UserRole

LANDLORD_AUTO_APPROVAL = getattr(settings, "LANDLORD_ROLE_AUTO_APPROVAL", True)


def create_audit_log(
    actor: User | None,
    action: str,
    entity,
    metadata: dict | None = None,
) -> AuditLog:
    return AuditLog.objects.create(
        actor=actor,
        action=action,
        entity_type=entity.__class__.__name__,
        entity_id=entity.id,
        metadata=metadata or {},
    )


def user_has_role(user: User, role_name: str) -> bool:
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return user.user_roles.filter(role__name=role_name, status=UserRoleStatus.APPROVED).exists()


def user_is_admin(user: User) -> bool:
    return bool(
        user.is_authenticated
        and (
            user.is_staff
            or user.is_superuser
            or user_has_role(user, RoleName.ADMIN)
            or user_has_role(user, RoleName.SUPER_ADMIN)
        )
    )


def user_is_super_admin(user: User) -> bool:
    return bool(
        user.is_authenticated
        and (user.is_superuser or user_has_role(user, RoleName.SUPER_ADMIN))
    )


def role_auto_approved(role_name: str) -> bool:
    if role_name == RoleName.LANDLORD:
        return LANDLORD_AUTO_APPROVAL
    return role_name in AUTO_APPROVED_ROLES


@transaction.atomic
def create_user_with_profile(
    *,
    email: str,
    password: str,
    first_name: str = "",
    last_name: str = "",
    phone_number: str | None = None,
) -> User:
    user = User.objects.create_user(
        email=email,
        password=password,
        first_name=first_name,
        last_name=last_name,
        phone_number=phone_number or None,
    )
    UserProfile.objects.create(user=user)
    return user


@transaction.atomic
def request_role(*, user: User, role: Role, actor: User | None = None) -> UserRole:
    if role.name in ADMIN_ONLY_ROLES:
        raise ValueError("Admin roles cannot be self-assigned.")

    status = UserRoleStatus.APPROVED if role_auto_approved(role.name) else UserRoleStatus.PENDING
    user_role = UserRole.objects.create(user=user, role=role, status=status)
    create_audit_log(
        actor=actor or user,
        action="role.requested",
        entity=user_role,
        metadata={"role": role.name, "status": status},
    )
    return user_role


@transaction.atomic
def decide_role_request(*, actor: User, user_role: UserRole, status: str) -> UserRole:
    if actor.id == user_role.user_id:
        raise ValueError("Users cannot approve or reject their own role requests.")

    user_role.status = status
    user_role.save(update_fields=["status", "updated_at"])
    create_audit_log(
        actor=actor,
        action=f"role.{status}",
        entity=user_role,
        metadata={"role": user_role.role.name, "user_id": str(user_role.user_id)},
    )
    return user_role
