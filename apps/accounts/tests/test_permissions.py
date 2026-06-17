import pytest
from rest_framework.test import APIRequestFactory

from apps.accounts.choices import RoleName, UserRoleStatus
from apps.accounts.models import UserRole
from apps.accounts.permissions import HasRole, IsAdmin, IsApprovedProfessional, IsSuperAdmin


class DummyView:
    required_roles = (RoleName.TENANT,)


@pytest.mark.django_db
def test_is_admin_allows_staff_user(admin_user):
    request = APIRequestFactory().get("/")
    request.user = admin_user

    assert IsAdmin().has_permission(request, DummyView())


@pytest.mark.django_db
def test_is_super_admin_allows_superuser(admin_user):
    admin_user.is_superuser = True
    admin_user.save(update_fields=["is_superuser"])
    request = APIRequestFactory().get("/")
    request.user = admin_user

    assert IsSuperAdmin().has_permission(request, DummyView())


@pytest.mark.django_db
def test_has_role_requires_approved_role(user, roles):
    UserRole.objects.create(user=user, role=roles[RoleName.TENANT], status=UserRoleStatus.APPROVED)
    request = APIRequestFactory().get("/")
    request.user = user

    assert HasRole().has_permission(request, DummyView())


@pytest.mark.django_db
def test_is_approved_professional_requires_professional_role(user, roles):
    UserRole.objects.create(
        user=user,
        role=roles[RoleName.INSPECTOR],
        status=UserRoleStatus.APPROVED,
    )
    request = APIRequestFactory().get("/")
    request.user = user

    assert IsApprovedProfessional().has_permission(request, DummyView())
