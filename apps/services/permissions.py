from rest_framework.permissions import SAFE_METHODS, BasePermission

from apps.accounts.services import user_is_admin


class PublicReadOrAdminOnly(BasePermission):
    def has_permission(self, request, view) -> bool:
        if request.method in SAFE_METHODS:
            return True
        return user_is_admin(request.user)
