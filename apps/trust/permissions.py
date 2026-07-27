"""Object-level permissions for the trust and verification app."""

from __future__ import annotations

from rest_framework.permissions import BasePermission

from apps.accounts.services import user_is_admin


class IsVerificationRequestOwner(BasePermission):
    """Only the submitting user may read/edit their own verification request."""

    message = "You can only access your own verification request."

    def has_object_permission(self, request, view, obj) -> bool:
        return obj.user_id == request.user.id


class IsPropertyVerificationSubmitter(BasePermission):
    """Only the user who submitted a property verification may access it."""

    message = "You can only access property verifications you submitted."

    def has_object_permission(self, request, view, obj) -> bool:
        return obj.submitted_by_id == request.user.id


class IsVerificationAdmin(BasePermission):
    """Restricts access to users with admin privileges."""

    message = "Only administrators can review verification requests."

    def has_permission(self, request, view) -> bool:
        return bool(request.user and request.user.is_authenticated and user_is_admin(request.user))


class CannotReviewOwnSubmission(BasePermission):
    """Blocks an admin from approving/rejecting/reviewing their own submission.

    Applied alongside IsVerificationAdmin on review actions. This is a
    deliberate second layer, not a duplicate check: IsVerificationAdmin
    confirms reviewer privilege, this confirms the reviewer isn't also
    the submitter, regardless of privilege level.
    """

    message = "You cannot review your own verification submission."

    def has_object_permission(self, request, view, obj) -> bool:
        submitter_id = getattr(obj, "user_id", None) or getattr(obj, "submitted_by_id", None)
        return submitter_id != request.user.id
