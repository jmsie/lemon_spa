"""Public URLs for appointments."""

from django.urls import path

from appointments.views import AppointmentCreateView

app_name = "appointments"

urlpatterns = [
    path("book/", AppointmentCreateView.as_view(), name="book"),
    path("book/<uuid:therapist_uuid>/", AppointmentCreateView.as_view(), name="book_with_therapist"),
]
