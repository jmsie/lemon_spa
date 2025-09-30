"""URL configuration for scheduling app."""

from django.urls import path

from scheduling.views import TherapistScheduleView

app_name = "scheduling"

urlpatterns = [
    path("", TherapistScheduleView.as_view(), name="therapist_schedule"),
]
