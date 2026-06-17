import pytest
from rest_framework.test import APIClient

from apps.accounts.models import Role, User


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def roles(db):
    return {role.name: role for role in Role.objects.all()}


@pytest.fixture
def user(db):
    return User.objects.create_user(
        email="ada@example.com",
        password="Str0ngPass123!",
        first_name="Ada",
        last_name="Okafor",
    )


@pytest.fixture
def admin_user(db):
    return User.objects.create_user(
        email="admin@example.com",
        password="Str0ngPass123!",
        is_staff=True,
        is_email_verified=True,
    )
