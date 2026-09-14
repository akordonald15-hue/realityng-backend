from rest_framework.permissions import SAFE_METHODS, BasePermission

from apps.accounts.services import user_is_admin
from apps.properties.choices import PropertyAssignmentCapability
from apps.properties.services import user_has_property_capability


class IsOwnerOrAdmin(BasePermission):
    message = "You can only modify properties you own."

    def has_object_permission(self, request, view, obj) -> bool:
        if request.method in SAFE_METHODS:
            return True
        return obj.owner_id == request.user.id or user_is_admin(request.user)


class IsListingManagerOrOwnerOrAdmin(BasePermission):
    message = "You can only manage listings you own or are assigned to manage."

    listing_management_actions = {
        "partial_update",
        "update",
        "images",
        "image_detail",
        "set_cover_image",
        "submit_for_review",
    }

    def has_object_permission(self, request, view, obj) -> bool:
        if request.method in SAFE_METHODS:
            return True

        if obj.owner_id == request.user.id or user_is_admin(request.user):
            return True

        if getattr(view, "action", None) not in self.listing_management_actions:
            return False

        return user_has_property_capability(
            request.user,
            obj,
            PropertyAssignmentCapability.MANAGE_LISTING,
        )
