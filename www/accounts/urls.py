"""URL routing for accounts app."""

from django.urls import path

from .api.views import PasswordResetConfirmView, PasswordResetSendCodeView
from .views import (
    RoleAwareLoginView,
    RoleSelectionView,
    SwitchRoleView,
    PasswordResetView,
    TherapistRegistrationView,
)

app_name = "accounts"

urlpatterns = [
    path("login/", RoleAwareLoginView.as_view(), name="login"),
    path("select-role/", RoleSelectionView.as_view(), name="select_role"),
    path("switch-role/<str:role>/", SwitchRoleView.as_view(), name="switch_role"),
    path("register/", TherapistRegistrationView.as_view(), name="register"),
    path("password-reset/", PasswordResetView.as_view(), name="password_reset"),
    path("api/password-reset/send-code/", PasswordResetSendCodeView.as_view(), name="password_reset_send_code"),
    path("api/password-reset/confirm/", PasswordResetConfirmView.as_view(), name="password_reset_confirm"),
]
