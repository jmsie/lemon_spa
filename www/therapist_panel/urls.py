"""URL routing for therapist panel web and API endpoints."""

from django.contrib.auth.views import LogoutView
from django.urls import include, path
from django.views.generic import RedirectView

from therapist_panel.views import (
    TherapistPanelIndexView,
    TherapistProfileUpdateView,
    TherapistTreatmentManagementView,
)

app_name = "therapist_panel"

urlpatterns = [
    path(
        "login/",
        RedirectView.as_view(pattern_name="accounts:login", permanent=False),
        name="login",
    ),
    path("logout/", LogoutView.as_view(next_page="accounts:login"), name="logout"),
    path("", TherapistPanelIndexView.as_view(), name="index"),
    path("profile/", TherapistProfileUpdateView.as_view(), name="profile_edit"),
    path("treatments/", TherapistTreatmentManagementView.as_view(), name="treatments"),
    path("api/", include("therapist_panel.api.urls", namespace="api")),
]
