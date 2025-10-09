"""Router configuration for therapist time off endpoints."""

from __future__ import annotations

from rest_framework.routers import DefaultRouter

from therapist_panel.api.views.time_off import TherapistTimeOffViewSet

app_name = "time_off"

router = DefaultRouter()
router.register("time_off", TherapistTimeOffViewSet, basename="time-off")

urlpatterns = router.urls
