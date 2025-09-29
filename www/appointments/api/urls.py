"""Router configuration for appointment endpoints."""

from rest_framework.routers import DefaultRouter

from appointments.api.views import AppointmentViewSet

app_name = "appointments_api"

router = DefaultRouter()
router.register("appointments", AppointmentViewSet, basename="appointment")

urlpatterns = router.urls
