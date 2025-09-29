"""Aggregated routing for therapist panel API."""

from django.urls import include, path

app_name = "therapist_panel_api"

urlpatterns = [
    path("", include("therapist_panel.api.urls.therapists")),
]
