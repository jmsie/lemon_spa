"""URL patterns for therapist registration workflow."""

from django.urls import path

from therapist_panel.api.views import (
    TherapistRegistrationCompleteView,
    TherapistRegistrationSendCodeView,
    TherapistRegistrationVerifyView,
)

app_name = "registration"

urlpatterns = [
    path(
        "registration/send-code/",
        TherapistRegistrationSendCodeView.as_view(),
        name="send_code",
    ),
    path(
        "registration/verify-code/",
        TherapistRegistrationVerifyView.as_view(),
        name="verify_code",
    ),
    path(
        "registration/complete/",
        TherapistRegistrationCompleteView.as_view(),
        name="complete",
    ),
]
