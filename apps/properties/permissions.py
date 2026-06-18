from rest_framework.permissions import SAFE_METHODS, BasePermission

from apps.accounts.services import user_is_admin


class IsOwnerOrAdmin(BasePermission):
    message = "You can only modify properties you own."

    def has_object_permission(self, request, view, obj) -> bool:
        if request.method in SAFE_METHODS:
            return True
        return obj.owner_id == request.user.id or user_is_admin(request.user)
