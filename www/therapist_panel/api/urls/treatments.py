"""Router configuration for therapist treatment endpoints."""

from rest_framework.routers import DefaultRouter

from therapist_panel.api.views.treatments import TherapistTreatmentViewSet

app_name = "treatments"

router = DefaultRouter()
router.register("treatments", TherapistTreatmentViewSet, basename="treatment")

urlpatterns = router.urls
