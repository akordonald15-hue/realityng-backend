from __future__ import annotations

import uuid

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.db.models import Q
from django.utils import timezone

from apps.accounts.choices import RoleName, UserRoleStatus
from apps.accounts.managers import UserManager
from apps.common.models import TimestampMixin, UUIDPrimaryKeyMixin


class User(UUIDPrimaryKeyMixin, TimestampMixin, AbstractBaseUser, PermissionsMixin):
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=32, unique=True, null=True, blank=True)
    is_email_verified = models.BooleanField(default=False)
    is_phone_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_suspended = models.BooleanField(default=False)
    last_login_at = models.DateTimeField(null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []

    class Meta:
        indexes = [
            models.Index(fields=["email"]),
            models.Index(fields=["phone_number"]),
            models.Index(fields=["is_active", "is_suspended"]),
        ]

    def __str__(self) -> str:
        return self.email

    @property
    def full_name(self) -> str:
        return " ".join(part for part in [self.first_name, self.last_name] if part).strip()

    def suspend(self) -> None:
        self.is_suspended = True
        self.save(update_fields=["is_suspended", "updated_at"])

    def unsuspend(self) -> None:
        self.is_suspended = False
        self.save(update_fields=["is_suspended", "updated_at"])


class Role(UUIDPrimaryKeyMixin):
    name = models.CharField(max_length=64, choices=RoleName.choices, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.get_name_display()


class UserRole(UUIDPrimaryKeyMixin, TimestampMixin):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="user_roles",
    )
    role = models.ForeignKey(Role, on_delete=models.PROTECT, related_name="user_roles")
    status = models.CharField(
        max_length=32,
        choices=UserRoleStatus.choices,
        default=UserRoleStatus.PENDING,
    )

    class Meta:
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["role", "status"]),
            models.Index(fields=["created_at"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "role"],
                condition=Q(status__in=[UserRoleStatus.PENDING, UserRoleStatus.APPROVED]),
                name="unique_open_or_approved_user_role",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.user.email} -> {self.role.name} ({self.status})"


class UserProfile(UUIDPrimaryKeyMixin, TimestampMixin):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    avatar = models.ImageField(upload_to="avatars/", null=True, blank=True)
    bio = models.TextField(blank=True)
    country = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=120, blank=True)
    address = models.TextField(blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=40, blank=True)
    emergency_contact_name = models.CharField(max_length=160, blank=True)
    emergency_contact_phone = models.CharField(max_length=32, blank=True)

    def __str__(self) -> str:
        return f"Profile for {self.user.email}"


class AuditLog(UUIDPrimaryKeyMixin):
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="account_audit_logs",
    )
    action = models.CharField(max_length=120)
    entity_type = models.CharField(max_length=120)
    entity_id = models.UUIDField(default=uuid.uuid4)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["action"]),
            models.Index(fields=["entity_type", "entity_id"]),
            models.Index(fields=["actor", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.action} {self.entity_type}:{self.entity_id}"
