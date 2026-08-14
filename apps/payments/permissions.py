from rest_framework.permissions import SAFE_METHODS, BasePermission

from apps.accounts.services import user_is_admin
from apps.properties.choices import PropertyAssignmentCapability
from apps.properties.services import user_has_property_capability


class IsTransactionParticipantOrAdmin(BasePermission):
    """Buyer, owner, or admin. Everyone else is denied, including for reads."""

    message = "You are not a participant in this transaction."

    def has_object_permission(self, request, view, obj) -> bool:
        return (
            obj.buyer_id == request.user.id
            or obj.owner_id == request.user.id
            or user_is_admin(request.user)
            or user_has_property_capability(
                request.user,
                obj.property,
                PropertyAssignmentCapability.MANAGE_LISTING,
            )
        )


class IsMilestoneParticipantOrAdmin(BasePermission):
    """Same participant check, resolved through the milestone's transaction."""

    message = "You are not a participant in this transaction."

    def has_object_permission(self, request, view, obj) -> bool:
        transaction = obj.transaction
        return (
            transaction.buyer_id == request.user.id
            or transaction.owner_id == request.user.id
            or user_is_admin(request.user)
            or user_has_property_capability(
                request.user,
                transaction.property,
                PropertyAssignmentCapability.MANAGE_LISTING,
            )
        )


class IsProofParticipantOrAdmin(BasePermission):
    """Same participant check, resolved through proof -> milestone -> transaction."""

    message = "You are not a participant in this transaction."

    def has_object_permission(self, request, view, obj) -> bool:
        transaction = obj.milestone.transaction
        return (
            transaction.buyer_id == request.user.id
            or transaction.owner_id == request.user.id
            or user_is_admin(request.user)
            or user_has_property_capability(
                request.user,
                transaction.property,
                PropertyAssignmentCapability.MANAGE_LISTING,
            )
        )


class IsEscrowParticipantOrAdmin(BasePermission):
    """Buyer, owner, admin, or explicitly transaction-authorized assignee."""

    message = "You are not a participant in this escrow transaction."

    def has_object_permission(self, request, view, obj) -> bool:
        transaction = obj.transaction
        return (
            transaction.buyer_id == request.user.id
            or transaction.owner_id == request.user.id
            or user_is_admin(request.user)
            or user_has_property_capability(
                request.user,
                transaction.property,
                PropertyAssignmentCapability.MANAGE_TRANSACTIONS,
            )
        )


class IsReviewerOrAdmin(BasePermission):
    """Only the property owner (reviewing proof of payment) or an admin may
    accept, reject, or start review on a milestone -- the buyer who
    submitted the proof cannot review their own submission.
    """

    message = "Only the property owner or an admin can review payment proofs."

    def has_object_permission(self, request, view, obj) -> bool:
        if request.method in SAFE_METHODS:
            return True
        transaction = obj.transaction
        return (
            user_is_admin(request.user)
            or transaction.owner_id == request.user.id
            or user_has_property_capability(
                request.user,
                transaction.property,
                PropertyAssignmentCapability.MANAGE_LISTING,
            )
        )


def can_manage_transaction(user, transaction) -> bool:
    if user_is_admin(user) or transaction.owner_id == user.id:
        return True
    return user_has_property_capability(
        user,
        transaction.property,
        PropertyAssignmentCapability.MANAGE_LISTING,
    )
