from __future__ import annotations

from django.contrib.auth import authenticate, password_validation
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.db.models import Q
from django.utils import timezone
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.choices import ADMIN_ONLY_ROLES, RoleName, UserRoleStatus
from apps.accounts.models import Role, User, UserProfile, UserRole
from apps.accounts.services import create_user_with_profile, request_role


class RoleSerializer(serializers.ModelSerializer):
    approval_required = serializers.SerializerMethodField()

    class Meta:
        model = Role
        fields = ["id", "name", "description", "created_at", "approval_required"]

    def get_approval_required(self, role: Role) -> bool:
        return role.name in {RoleName.AGENT, RoleName.ARTISAN, RoleName.LAWYER, RoleName.INSPECTOR}


class UserRoleSerializer(serializers.ModelSerializer):
    role = RoleSerializer(read_only=True)
    user_id = serializers.UUIDField(source="user.id", read_only=True)
    user_email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = UserRole
        fields = ["id", "user_id", "user_email", "role", "status", "created_at", "updated_at"]


class UserProfileSerializer(serializers.ModelSerializer):
    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = UserProfile
        fields = [
            "avatar",
            "avatar_url",
            "bio",
            "country",
            "state",
            "city",
            "address",
            "date_of_birth",
            "gender",
            "emergency_contact_name",
            "emergency_contact_phone",
        ]
        extra_kwargs = {"avatar": {"write_only": True, "required": False}}

    def get_avatar_url(self, profile: UserProfile) -> str | None:
        if not profile.avatar:
            return None
        request = self.context.get("request")
        url = profile.avatar.url
        return request.build_absolute_uri(url) if request else url


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    profile = serializers.SerializerMethodField()
    roles = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "phone_number",
            "first_name",
            "last_name",
            "full_name",
            "is_email_verified",
            "is_phone_verified",
            "is_active",
            "is_suspended",
            "last_login_at",
            "created_at",
            "updated_at",
            "profile",
            "roles",
        ]
        read_only_fields = [
            "id",
            "email",
            "is_email_verified",
            "is_phone_verified",
            "is_active",
            "is_suspended",
            "last_login_at",
            "created_at",
            "updated_at",
            "roles",
        ]

    def get_roles(self, user: User) -> list[dict]:
        return UserRoleSerializer(user.user_roles.select_related("role").all(), many=True).data

    def get_profile(self, user: User) -> dict:
        profile, _ = UserProfile.objects.get_or_create(user=user)
        return UserProfileSerializer(profile, context=self.context).data


class UserUpdateSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(required=False)

    class Meta:
        model = User
        fields = ["first_name", "last_name", "phone_number", "profile"]

    def validate_phone_number(self, value: str | None) -> str | None:
        if not value:
            return None

        exists = User.objects.filter(phone_number=value).exclude(id=self.instance.id).exists()
        if exists:
            raise serializers.ValidationError("A user with this phone number already exists.")
        return value

    def update(self, instance: User, validated_data: dict) -> User:
        profile_data = validated_data.pop("profile", None)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()

        if profile_data is not None:
            profile, _ = UserProfile.objects.get_or_create(user=instance)
            for field, value in profile_data.items():
                setattr(profile, field, value)
            profile.save()

        return instance


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    first_name = serializers.CharField(required=False, allow_blank=True, max_length=100)
    last_name = serializers.CharField(required=False, allow_blank=True, max_length=100)
    phone_number = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        max_length=32,
    )

    def validate_email(self, value: str) -> str:
        email = User.objects.normalize_email(value).lower()
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return email

    def validate_phone_number(self, value: str | None) -> str | None:
        if not value:
            return None
        if User.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError("A user with this phone number already exists.")
        return value

    def validate_password(self, value: str) -> str:
        password_validation.validate_password(value)
        return value

    def create(self, validated_data: dict) -> User:
        return create_user_with_profile(**validated_data)


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs: dict) -> dict:
        email = User.objects.normalize_email(attrs["email"]).lower()
        user = authenticate(
            request=self.context.get("request"),
            username=email,
            password=attrs["password"],
        )

        if user is None:
            raise serializers.ValidationError("Invalid email or password.")
        if user.is_suspended:
            raise serializers.ValidationError("User account is suspended.")

        user.last_login_at = timezone.now()
        user.save(update_fields=["last_login_at", "updated_at"])

        refresh = RefreshToken.for_user(user)
        return {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": UserSerializer(user, context=self.context).data,
        }


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()

    def save(self, **kwargs):
        try:
            token = RefreshToken(self.validated_data["refresh"])
            token.blacklist()
        except TokenError as exc:
            raise serializers.ValidationError(
                "Refresh token is invalid or already logged out."
            ) from exc


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()


class ResetPasswordSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    password = serializers.CharField(write_only=True, min_length=8)

    def validate_password(self, value: str) -> str:
        password_validation.validate_password(value)
        return value

    def validate(self, attrs: dict) -> dict:
        try:
            user_id = force_str(urlsafe_base64_decode(attrs["uid"]))
            user = User.objects.get(pk=user_id)
        except (User.DoesNotExist, ValueError, TypeError, OverflowError):
            raise serializers.ValidationError("Invalid reset link.") from None

        if not PasswordResetTokenGenerator().check_token(user, attrs["token"]):
            raise serializers.ValidationError("Invalid reset link.")

        attrs["user"] = user
        return attrs

    def save(self, **kwargs):
        user: User = self.validated_data["user"]
        user.set_password(self.validated_data["password"])
        user.save(update_fields=["password", "updated_at"])


class TokenRefreshResponseSerializer(TokenRefreshSerializer):
    def validate(self, attrs: dict) -> dict:
        refresh = self.token_class(attrs["refresh"])
        user_id = refresh.payload.get(api_settings.USER_ID_CLAIM)
        user = User.objects.filter(pk=user_id).first()
        if user is None or user.is_suspended or not user.is_active:
            raise AuthenticationFailed("User account is not allowed to refresh tokens.")
        return super().validate(attrs)


class RoleRequestSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=RoleName.choices)

    def validate_role(self, value: str) -> Role:
        if value in ADMIN_ONLY_ROLES:
            raise serializers.ValidationError("Admin roles cannot be self-assigned.")
        role = Role.objects.get(name=value)
        exists = UserRole.objects.filter(
            Q(status=UserRoleStatus.PENDING) | Q(status=UserRoleStatus.APPROVED),
            user=self.context["request"].user,
            role=role,
        ).exists()
        if exists:
            raise serializers.ValidationError("This role has already been requested or approved.")
        return role

    def create(self, validated_data: dict) -> UserRole:
        return request_role(
            user=self.context["request"].user,
            role=validated_data["role"],
            actor=self.context["request"].user,
        )

    def to_representation(self, instance: UserRole) -> dict:
        return UserRoleSerializer(instance).data


class RoleDecisionSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True)
