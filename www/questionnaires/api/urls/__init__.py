"""Aggregated routing for questionnaires API."""

from django.urls import include, path

app_name = "questionnaires_api"

urlpatterns = [
    path("", include("questionnaires.api.urls.questionnaires")),
]
