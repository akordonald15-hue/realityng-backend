# Generated for RealityNG Sprint 1.

import uuid

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.CreateModel(
            name="User",
            fields=[
                ("password", models.CharField(max_length=128, verbose_name="password")),
                ("last_login", models.DateTimeField(blank=True, null=True, verbose_name="last login")),
                ("is_superuser", models.BooleanField(default=False)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("first_name", models.CharField(blank=True, max_length=100)),
                ("last_name", models.CharField(blank=True, max_length=100)),
                ("email", models.EmailField(max_length=254, unique=True)),
                ("phone_number", models.CharField(blank=True, max_length=32, null=True, unique=True)),
                ("is_email_verified", models.BooleanField(default=False)),
                ("is_phone_verified", models.BooleanField(default=False)),
                ("is_active", models.BooleanField(default=True)),
                ("is_staff", models.BooleanField(default=False)),
                ("is_suspended", models.BooleanField(default=False)),
                ("last_login_at", models.DateTimeField(blank=True, null=True)),
                (
                    "groups",
                    models.ManyToManyField(
                        blank=True,
                        related_name="user_set",
                        related_query_name="user",
                        to="auth.group",
                        verbose_name="groups",
                    ),
                ),
                (
                    "user_permissions",
                    models.ManyToManyField(
                        blank=True,
                        related_name="user_set",
                        related_query_name="user",
                        to="auth.permission",
                        verbose_name="user permissions",
                    ),
                ),
            ],
            options={
                "indexes": [
                    models.Index(fields=["email"], name="accounts_us_email_a7d3a8_idx"),
                    models.Index(fields=["phone_number"], name="accounts_us_phone_n_b58175_idx"),
                    models.Index(fields=["is_active", "is_suspended"], name="accounts_us_is_acti_142586_idx"),
                ],
            },
        ),
        migrations.CreateModel(
            name="Role",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                (
                    "name",
                    models.CharField(
                        choices=[
                            ("tenant", "Tenant"),
                            ("buyer", "Buyer"),
                            ("landlord", "Landlord"),
                            ("agent", "Agent"),
                            ("artisan", "Artisan"),
                            ("lawyer", "Lawyer"),
                            ("inspector", "Inspector"),
                            ("admin", "Admin"),
                            ("super_admin", "Super Admin"),
                        ],
                        max_length=64,
                        unique=True,
                    ),
                ),
                ("description", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="AuditLog",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("action", models.CharField(max_length=120)),
                ("entity_type", models.CharField(max_length=120)),
                ("entity_id", models.UUIDField(default=uuid.uuid4)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                (
                    "actor",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="account_audit_logs",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["action"], name="accounts_au_action_7061b2_idx"),
                    models.Index(fields=["entity_type", "entity_id"], name="accounts_au_entity__6c8b39_idx"),
                    models.Index(fields=["actor", "created_at"], name="accounts_au_actor_i_4512b3_idx"),
                ],
            },
        ),
        migrations.CreateModel(
            name="UserProfile",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("avatar", models.ImageField(blank=True, null=True, upload_to="avatars/")),
                ("bio", models.TextField(blank=True)),
                ("country", models.CharField(blank=True, max_length=100)),
                ("state", models.CharField(blank=True, max_length=100)),
                ("city", models.CharField(blank=True, max_length=120)),
                ("address", models.TextField(blank=True)),
                ("date_of_birth", models.DateField(blank=True, null=True)),
                ("gender", models.CharField(blank=True, max_length=40)),
                ("emergency_contact_name", models.CharField(blank=True, max_length=160)),
                ("emergency_contact_phone", models.CharField(blank=True, max_length=32)),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="profile",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="UserRole",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "status",
                    models.CharField(
                        choices=[("pending", "Pending"), ("approved", "Approved"), ("rejected", "Rejected")],
                        default="pending",
                        max_length=32,
                    ),
                ),
                (
                    "role",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="user_roles",
                        to="accounts.role",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="user_roles",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "indexes": [
                    models.Index(fields=["user", "status"], name="accounts_us_user_id_daf398_idx"),
                    models.Index(fields=["role", "status"], name="accounts_us_role_id_095d3b_idx"),
                    models.Index(fields=["created_at"], name="accounts_us_created_18dc2c_idx"),
                ],
                "constraints": [
                    models.UniqueConstraint(
                        condition=models.Q(("status__in", ["pending", "approved"])),
                        fields=("user", "role"),
                        name="unique_open_or_approved_user_role",
                    )
                ],
            },
        ),
    ]
