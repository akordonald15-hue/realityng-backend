from rest_framework.permissions import BasePermission

from apps.accounts.services import user_is_admin
from apps.inspections.services import user_can_view_inspection, user_is_inspector


class IsInspectionAdmin(BasePermission):
    message = "Inspection admin access is required."

    def has_permission(self, request, view) -> bool:
        return user_is_admin(request.user)


class IsInspector(BasePermission):
    message = "Approved inspector access is required."

    def has_permission(self, request, view) -> bool:
        return user_is_inspector(request.user)


class CanViewInspectionObject(BasePermission):
    def has_object_permission(self, request, view, obj) -> bool:
        inspection = getattr(obj, "inspection_request", obj)
        return user_can_view_inspection(request.user, inspection)
