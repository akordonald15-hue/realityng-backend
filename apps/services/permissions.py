from rest_framework.permissions import SAFE_METHODS, BasePermission

from apps.accounts.choices import RoleName
from apps.accounts.services import user_has_role, user_is_admin


class PublicReadOrAdminOnly(BasePermission):
    def has_permission(self, request, view) -> bool:
        if request.method in SAFE_METHODS:
            return True
        return user_is_admin(request.user)


class IsEligibleServiceProvider(BasePermission):
    def has_permission(self, request, view) -> bool:
        user = request.user
        if not user or not user.is_authenticated:
            return False
        return bool(
            user_is_admin(user)
            or user_has_role(user, RoleName.ARTISAN)
            or user_has_role(user, RoleName.AGENT)
        )


class IsServiceProviderOwner(BasePermission):
    def has_object_permission(self, request, view, obj) -> bool:
        if user_is_admin(request.user):
            return True
        provider = getattr(obj, "provider", obj)
        return bool(provider.user_id == request.user.id)


class IsServicesAdmin(BasePermission):
    def has_permission(self, request, view) -> bool:
        return user_is_admin(request.user)
