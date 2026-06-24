from __future__ import annotations

from django.conf import settings
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenRefreshView

from apps.accounts.choices import RoleName, UserRoleStatus
from apps.accounts.models import Role, User, UserRole
from apps.accounts.permissions import IsAdmin
from apps.accounts.serializers import (
    ForgotPasswordSerializer,
    LoginSerializer,
    LogoutSerializer,
    RegisterSerializer,
    ResetPasswordSerializer,
    RoleDecisionSerializer,
    RoleRequestSerializer,
    RoleSerializer,
    TokenRefreshResponseSerializer,
    UserRoleSerializer,
    UserSerializer,
    UserUpdateSerializer,
)
from apps.accounts.services import decide_role_request


class RegisterView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(request=RegisterSerializer, responses={201: UserSerializer})
    def post(self, request):
        serializer = RegisterSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            UserSerializer(user, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(request=LoginSerializer, responses={200: LoginSerializer})
    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=LogoutSerializer,
        responses={204: OpenApiResponse(description="Logged out")},
    )
    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class RefreshTokenView(TokenRefreshView):
    serializer_class = TokenRefreshResponseSerializer


class ForgotPasswordView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=ForgotPasswordSerializer,
        responses={200: OpenApiResponse(description="Reset queued")},
    )
    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = User.objects.filter(email__iexact=serializer.validated_data["email"]).first()
        reset_payload = None
        if user and settings.DEBUG:
            reset_payload = {
                "uid": urlsafe_base64_encode(force_bytes(user.pk)),
                "token": PasswordResetTokenGenerator().make_token(user),
            }
        return Response({"status": "sent_if_exists", "reset": reset_payload})


class ResetPasswordView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=ResetPasswordSerializer,
        responses={200: OpenApiResponse(description="Password reset")},
    )
    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"status": "ok"})


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: UserSerializer})
    def get(self, request):
        return Response(UserSerializer(request.user, context={"request": request}).data)

    @extend_schema(request=UserUpdateSerializer, responses={200: UserSerializer})
    def patch(self, request):
        serializer = UserUpdateSerializer(
            request.user,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(UserSerializer(user, context={"request": request}).data)


class RoleListView(generics.ListAPIView):
    queryset = Role.objects.filter(name__in=RoleName.values)
    serializer_class = RoleSerializer
    permission_classes = [IsAuthenticated]


class RoleRequestView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=RoleRequestSerializer, responses={201: UserRoleSerializer})
    def post(self, request):
        serializer = RoleRequestSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user_role = serializer.save()
        return Response(UserRoleSerializer(user_role).data, status=status.HTTP_201_CREATED)


class AdminRoleRequestListView(generics.ListAPIView):
    serializer_class = UserRoleSerializer
    permission_classes = [IsAuthenticated, IsAdmin]

    def get_queryset(self):
        return (
            UserRole.objects.select_related("user", "role")
            .filter(status=UserRoleStatus.PENDING)
            .order_by("created_at")
        )


class AdminRoleApproveView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    @extend_schema(request=RoleDecisionSerializer, responses={200: UserRoleSerializer})
    def post(self, request, pk):
        serializer = RoleDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user_role = generics.get_object_or_404(
            UserRole.objects.select_related("user", "role"),
            pk=pk,
        )
        try:
            decided = decide_role_request(
                actor=request.user,
                user_role=user_role,
                status=UserRoleStatus.APPROVED,
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(UserRoleSerializer(decided).data)


class AdminRoleRejectView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    @extend_schema(request=RoleDecisionSerializer, responses={200: UserRoleSerializer})
    def post(self, request, pk):
        serializer = RoleDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user_role = generics.get_object_or_404(
            UserRole.objects.select_related("user", "role"),
            pk=pk,
        )
        try:
            decided = decide_role_request(
                actor=request.user,
                user_role=user_role,
                status=UserRoleStatus.REJECTED,
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(UserRoleSerializer(decided).data)
