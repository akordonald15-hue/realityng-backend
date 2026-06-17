from __future__ import annotations

from rest_framework.permissions import BasePermission

from apps.accounts.choices import PROFESSIONAL_ROLES
from apps.accounts.services import user_has_role, user_is_admin, user_is_super_admin


class IsAdmin(BasePermission):
    message = "Admin access is required."

    def has_permission(self, request, view) -> bool:
        return user_is_admin(request.user)


class IsSuperAdmin(BasePermission):
    message = "Super admin access is required."

    def has_permission(self, request, view) -> bool:
        return user_is_super_admin(request.user)


class HasRole(BasePermission):
    required_roles: tuple[str, ...] = ()

    def has_permission(self, request, view) -> bool:
        required_roles = getattr(view, "required_roles", self.required_roles)
        return any(user_has_role(request.user, role) for role in required_roles)


class IsApprovedProfessional(BasePermission):
    message = "An approved professional role is required."

    def has_permission(self, request, view) -> bool:
        return any(user_has_role(request.user, role) for role in PROFESSIONAL_ROLES)
