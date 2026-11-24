from django.urls import path
from .views import (
    ChangePasswordView,
    DeleteAccountView,
    ExportDataView,
    LoginView,
    SafeTokenRefreshView,
    LogoutView,
    MeView,
    PasswordResetConfirmView,
    PasswordResetView,
    RegisterView,
)

urlpatterns = [
    path("register/", RegisterView.as_view()),
    path("token/", LoginView.as_view()),
    path("token/refresh/", SafeTokenRefreshView.as_view()),
    path("logout/", LogoutView.as_view()),
    path("me/", MeView.as_view()),
    path("delete-account/", DeleteAccountView.as_view()),
    path("export/", ExportDataView.as_view()),
    path("change-password/", ChangePasswordView.as_view()),
    path("password-reset/", PasswordResetView.as_view()),
    path("password-reset/confirm/", PasswordResetConfirmView.as_view()),
]
