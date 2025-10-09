"""Router configuration for appointment endpoints."""

from django.urls import path
from rest_framework.routers import DefaultRouter

from appointments.api.views import AppointmentViewSet, TherapistAvailabilityView

app_name = "appointments_api"

router = DefaultRouter()
router.register("appointments", AppointmentViewSet, basename="appointment")

urlpatterns = router.urls + [
    path(
        "availability/<uuid:therapist_uuid>/",
        TherapistAvailabilityView.as_view(),
        name="availability",
    ),
]
