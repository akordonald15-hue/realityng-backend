import pytest
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.choices import RoleName, UserRoleStatus
from apps.accounts.models import Role, UserRole


@pytest.mark.django_db
def test_auth_and_profile_endpoint_flow(api_client):
    register_response = api_client.post(
        reverse("auth-register"),
        {
            "email": "flow@example.com",
            "password": "Str0ngPass123!",
            "first_name": "Flow",
            "accepts_terms": True,
            "accepts_privacy": True,
            "terms_version": "2026-08",
            "privacy_version": "2026-08",
        },
        format="json",
    )
    assert register_response.status_code == status.HTTP_201_CREATED

    login_response = api_client.post(
        reverse("auth-login"),
        {"email": "flow@example.com", "password": "Str0ngPass123!"},
        format="json",
    )
    assert login_response.status_code == status.HTTP_200_OK

    access = login_response.data["access"]
    refresh = login_response.data["refresh"]
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    me_response = api_client.get(reverse("users-me"))
    assert me_response.status_code == status.HTTP_200_OK

    patch_response = api_client.patch(
        reverse("users-me"),
        {"profile": {"city": "Lagos"}},
        format="json",
    )
    assert patch_response.status_code == status.HTTP_200_OK
    assert patch_response.data["profile"]["city"] == "Lagos"

    refresh_response = api_client.post(
        reverse("token-refresh"),
        {"refresh": refresh},
        format="json",
    )
    assert refresh_response.status_code == status.HTTP_200_OK

    rotated_refresh = refresh_response.data.get("refresh", refresh)
    logout_response = api_client.post(
        reverse("auth-logout"),
        {"refresh": rotated_refresh},
        format="json",
    )
    assert logout_response.status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.django_db
@override_settings(DEBUG=True)
def test_password_reset_endpoint_flow(api_client, user):
    forgot_response = api_client.post(
        reverse("forgot-password"),
        {"email": user.email},
        format="json",
    )
    assert forgot_response.status_code == status.HTTP_200_OK
    assert forgot_response.data["status"] == "sent_if_exists"
    assert forgot_response.data["reset"]

    reset_response = api_client.post(
        reverse("reset-password"),
        {
            "uid": forgot_response.data["reset"]["uid"],
            "token": forgot_response.data["reset"]["token"],
            "password": "NewStr0ngPass123!",
        },
        format="json",
    )
    assert reset_response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_role_admin_endpoint_flow(api_client, user, admin_user, roles):
    api_client.force_authenticate(user)
    roles_response = api_client.get(reverse("roles-list"))
    assert roles_response.status_code == status.HTTP_200_OK

    request_response = api_client.post(
        reverse("roles-request"),
        {"role": RoleName.ARTISAN},
        format="json",
    )
    assert request_response.status_code == status.HTTP_201_CREATED
    user_role_id = request_response.data["id"]

    api_client.force_authenticate(admin_user)
    role_requests_response = api_client.get(reverse("admin-role-requests"))
    assert role_requests_response.status_code == status.HTTP_200_OK

    approve_response = api_client.post(
        reverse("admin-role-request-approve", args=[user_role_id]),
        {},
        format="json",
    )
    assert approve_response.status_code == status.HTTP_200_OK
    assert approve_response.data["status"] == UserRoleStatus.APPROVED

    second_user = user.__class__.objects.create_user(
        email="reject-me@example.com",
        password="Str0ngPass123!",
    )
    pending_role = UserRole.objects.create(
        user=second_user,
        role=Role.objects.get(name=RoleName.INSPECTOR),
        status=UserRoleStatus.PENDING,
    )
    reject_response = api_client.post(
        reverse("admin-role-request-reject", args=[pending_role.id]),
        {},
        format="json",
    )
    assert reject_response.status_code == status.HTTP_200_OK
    assert reject_response.data["status"] == UserRoleStatus.REJECTED


@pytest.mark.django_db
def test_admin_endpoint_rejects_non_admin(api_client, user):
    api_client.force_authenticate(user)
    response = api_client.get(reverse("admin-role-requests"))
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_suspended_user_cannot_refresh_token(api_client, user):
    refresh = RefreshToken.for_user(user)
    user.suspend()

    response = api_client.post(reverse("token-refresh"), {"refresh": str(refresh)}, format="json")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
