"""Public questionnaire URLs."""

from django.urls import path

from questionnaires.views import (
    QuestionnaireAlreadySubmittedView,
    QuestionnaireCreateView,
    QuestionnaireThankYouView,
)

app_name = "questionnaires"

urlpatterns = [
    path("fill/<uuid:appointment_uuid>/", QuestionnaireCreateView.as_view(), name="fill"),
    path(
        "fill/<uuid:appointment_uuid>/submitted/",
        QuestionnaireThankYouView.as_view(),
        name="thank_you",
    ),
    path(
        "fill/<uuid:appointment_uuid>/already-submitted/",
        QuestionnaireAlreadySubmittedView.as_view(),
        name="already_submitted",
    ),
]
