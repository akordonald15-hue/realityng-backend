import pytest
from django.urls import reverse
from rest_framework import status

from apps.accounts.choices import RoleName, UserRoleStatus
from apps.accounts.models import AuditLog, UserRole


@pytest.mark.django_db
def test_tenant_role_request_is_auto_approved(api_client, user, roles):
    api_client.force_authenticate(user)

    response = api_client.post(reverse("roles-request"), {"role": RoleName.TENANT}, format="json")

    assert response.status_code == status.HTTP_201_CREATED
    user_role = UserRole.objects.get(user=user, role=roles[RoleName.TENANT])
    assert user_role.status == UserRoleStatus.APPROVED
    assert AuditLog.objects.filter(action="role.requested", entity_id=user_role.id).exists()


@pytest.mark.django_db
def test_professional_role_request_is_pending(api_client, user, roles):
    api_client.force_authenticate(user)

    response = api_client.post(reverse("roles-request"), {"role": RoleName.AGENT}, format="json")

    assert response.status_code == status.HTTP_201_CREATED
    user_role = UserRole.objects.get(user=user, role=roles[RoleName.AGENT])
    assert user_role.status == UserRoleStatus.PENDING


@pytest.mark.django_db
def test_admin_role_cannot_be_self_requested(api_client, user):
    api_client.force_authenticate(user)

    response = api_client.post(reverse("roles-request"), {"role": RoleName.ADMIN}, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_duplicate_open_role_request_is_rejected(api_client, user):
    api_client.force_authenticate(user)
    api_client.post(reverse("roles-request"), {"role": RoleName.AGENT}, format="json")

    response = api_client.post(reverse("roles-request"), {"role": RoleName.AGENT}, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_admin_can_approve_role_request(api_client, user, admin_user, roles):
    user_role = UserRole.objects.create(
        user=user,
        role=roles[RoleName.AGENT],
        status=UserRoleStatus.PENDING,
    )
    api_client.force_authenticate(admin_user)

    response = api_client.post(
        reverse("admin-role-request-approve", args=[user_role.id]),
        {},
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    user_role.refresh_from_db()
    assert user_role.status == UserRoleStatus.APPROVED
    assert AuditLog.objects.filter(
        action="role.approved",
        entity_id=user_role.id,
        actor=admin_user,
    ).exists()


@pytest.mark.django_db
def test_user_cannot_approve_own_role_request(api_client, user, roles):
    user_role = UserRole.objects.create(
        user=user,
        role=roles[RoleName.AGENT],
        status=UserRoleStatus.PENDING,
    )
    user.is_staff = True
    user.save(update_fields=["is_staff"])
    api_client.force_authenticate(user)

    response = api_client.post(
        reverse("admin-role-request-approve", args=[user_role.id]),
        {},
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
