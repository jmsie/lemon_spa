"""Routing for therapist working hours API endpoints."""

from __future__ import annotations

from rest_framework.routers import DefaultRouter

from therapist_panel.api.views.working_hours import TherapistWorkingHoursViewSet

app_name = "working_hours"

router = DefaultRouter()
router.register("working_hours", TherapistWorkingHoursViewSet, basename="working-hours")

urlpatterns = router.urls


__all__ = ["urlpatterns"]
