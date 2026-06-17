from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from apps.accounts.models import AuditLog, Role, User, UserProfile, UserRole


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    model = User
    ordering = ["email"]
    list_display = ["email", "first_name", "last_name", "is_active", "is_suspended", "is_staff"]
    list_filter = [
        "is_active",
        "is_suspended",
        "is_staff",
        "is_email_verified",
        "is_phone_verified",
    ]
    search_fields = ["email", "first_name", "last_name", "phone_number"]
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal", {"fields": ("first_name", "last_name", "phone_number")}),
        ("Verification", {"fields": ("is_email_verified", "is_phone_verified")}),
        ("Status", {"fields": ("is_active", "is_suspended", "is_staff", "is_superuser")}),
        ("Permissions", {"fields": ("groups", "user_permissions")}),
        (
            "Important dates",
            {"fields": ("last_login", "last_login_at", "created_at", "updated_at")},
        ),
    )
    readonly_fields = ["created_at", "updated_at", "last_login"]
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "password1", "password2", "is_staff", "is_superuser"),
            },
        ),
    )


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ["name", "description", "created_at"]
    search_fields = ["name", "description"]


@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    list_display = ["user", "role", "status", "created_at", "updated_at"]
    list_filter = ["status", "role"]
    search_fields = ["user__email", "role__name"]


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "country", "state", "city", "updated_at"]
    search_fields = ["user__email", "country", "state", "city"]


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ["action", "entity_type", "entity_id", "actor", "created_at"]
    list_filter = ["action", "entity_type", "created_at"]
    search_fields = ["action", "entity_type", "actor__email"]
    readonly_fields = ["actor", "action", "entity_type", "entity_id", "metadata", "created_at"]
