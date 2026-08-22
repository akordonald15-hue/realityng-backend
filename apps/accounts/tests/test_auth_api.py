import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import User


@pytest.mark.django_db
def test_register_creates_user_profile(api_client):
    response = api_client.post(
        reverse("auth-register"),
        {
            "email": "new@example.com",
            "password": "Str0ngPass123!",
            "first_name": "New",
            "last_name": "User",
            "phone_number": "+2348010000000",
            "accepts_terms": True,
            "accepts_privacy": True,
            "terms_version": "2026-08",
            "privacy_version": "2026-08",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED
    user = User.objects.get(email="new@example.com")
    assert user.profile is not None
    assert response.data["email"] == "new@example.com"


@pytest.mark.django_db
def test_register_rejects_duplicate_email(api_client, user):
    response = api_client.post(
        reverse("auth-register"),
        {
            "email": user.email,
            "password": "Str0ngPass123!",
            "accepts_terms": True,
            "accepts_privacy": True,
            "terms_version": "2026-08",
            "privacy_version": "2026-08",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_register_requires_versioned_terms_and_privacy_acceptance(api_client):
    response = api_client.post(
        reverse("auth-register"),
        {"email": "no-consent@example.com", "password": "Str0ngPass123!"},
        format="json",
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_login_returns_jwt_pair(api_client, user):
    response = api_client.post(
        reverse("auth-login"),
        {"email": user.email, "password": "Str0ngPass123!"},
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["access"]
    assert response.data["refresh"]
    assert response.data["user"]["email"] == user.email


@pytest.mark.django_db
def test_jwt_refresh_returns_access_token(api_client, user):
    refresh = RefreshToken.for_user(user)

    response = api_client.post(
        reverse("token-refresh"),
        {"refresh": str(refresh)},
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["access"]


@pytest.mark.django_db
def test_suspended_user_cannot_login(api_client, user):
    user.suspend()

    response = api_client.post(
        reverse("auth-login"),
        {"email": user.email, "password": "Str0ngPass123!"},
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_suspended_user_token_is_denied(api_client, user):
    refresh = RefreshToken.for_user(user)
    user.suspend()

    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    response = api_client.get(reverse("users-me"))

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
