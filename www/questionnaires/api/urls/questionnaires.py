"""Router configuration for questionnaire endpoints."""

from rest_framework.routers import DefaultRouter

from questionnaires.api.views import QuestionnaireViewSet

app_name = "questionnaires"

router = DefaultRouter()
router.register("questionnaires", QuestionnaireViewSet, basename="questionnaire")

urlpatterns = router.urls
