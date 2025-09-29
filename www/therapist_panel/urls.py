"""Backwards-compatible URLs for therapist panel."""

from django.urls import include, path

urlpatterns = [
    path("", include("therapist_panel.api.urls")),
]
