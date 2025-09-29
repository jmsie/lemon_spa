"""Router configuration for therapist endpoints."""

from rest_framework.routers import DefaultRouter

from therapist_panel.api.views.therapists import TherapistViewSet

app_name = "therapists"

router = DefaultRouter()
router.register("therapists", TherapistViewSet, basename="therapist")

urlpatterns = router.urls
