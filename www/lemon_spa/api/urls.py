"""Project-level API routing."""

from django.urls import include, path

from therapist_panel.api import urls as therapist_panel_urls
from questionnaires.api import urls as questionnaires_urls

app_name = "api"

urlpatterns = [
    path(
        "therapist_panel/",
        include((therapist_panel_urls.urlpatterns, therapist_panel_urls.app_name), namespace="therapist_panel"),
    ),
    path(
        "questionnaires/",
        include((questionnaires_urls.urlpatterns, questionnaires_urls.app_name), namespace="questionnaires"),
    ),
]
