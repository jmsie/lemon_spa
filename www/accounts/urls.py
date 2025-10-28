"""URL routing for accounts app."""

from django.urls import path

from .views import (
    RoleAwareLoginView,
    RoleSelectionView,
    SwitchRoleView,
    TherapistRegistrationView,
)

app_name = "accounts"

urlpatterns = [
    path("login/", RoleAwareLoginView.as_view(), name="login"),
    path("select-role/", RoleSelectionView.as_view(), name="select_role"),
    path("switch-role/<str:role>/", SwitchRoleView.as_view(), name="switch_role"),
    path("register/", TherapistRegistrationView.as_view(), name="register"),
]
