from django.urls import path

from apps.accounts.views import (
    AdminRoleApproveView,
    AdminRoleRejectView,
    AdminRoleRequestListView,
    ForgotPasswordView,
    LoginView,
    LogoutView,
    MeView,
    RefreshTokenView,
    RegisterView,
    ResetPasswordView,
    RoleListView,
    RoleRequestView,
)

urlpatterns = [
    path("auth/register/", RegisterView.as_view(), name="auth-register"),
    path("auth/login/", LoginView.as_view(), name="auth-login"),
    path("auth/logout/", LogoutView.as_view(), name="auth-logout"),
    path("auth/token/refresh/", RefreshTokenView.as_view(), name="token-refresh"),
    path("auth/forgot-password/", ForgotPasswordView.as_view(), name="forgot-password"),
    path("auth/reset-password/", ResetPasswordView.as_view(), name="reset-password"),
    path("users/me/", MeView.as_view(), name="users-me"),
    path("roles/", RoleListView.as_view(), name="roles-list"),
    path("roles/request/", RoleRequestView.as_view(), name="roles-request"),
    path("admin/role-requests/", AdminRoleRequestListView.as_view(), name="admin-role-requests"),
    path(
        "admin/role-requests/<uuid:pk>/approve/",
        AdminRoleApproveView.as_view(),
        name="admin-role-request-approve",
    ),
    path(
        "admin/role-requests/<uuid:pk>/reject/",
        AdminRoleRejectView.as_view(),
        name="admin-role-request-reject",
    ),
]
