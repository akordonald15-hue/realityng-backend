from rest_framework.permissions import BasePermission

from apps.accounts.services import user_is_admin


class IsConstructionAdmin(BasePermission):
    def has_permission(self, request, view) -> bool:
        return user_is_admin(request.user)
