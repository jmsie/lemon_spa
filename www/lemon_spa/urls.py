"""lemon_spa URL Configuration."""

from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView

urlpatterns = [
    path("", TemplateView.as_view(template_name="landing.html"), name="landing"),
    path("admin/", admin.site.urls),
    path("api/", include("lemon_spa.api.urls", namespace="api")),
    path("accounts/", include("accounts.urls", namespace="accounts")),
    path("client_dashboard/", include("client_dashboard.urls", namespace="client_dashboard")),
    path("therapist_panel/", include("therapist_panel.urls", namespace="therapist_panel")),
    path("appointments/", include("appointments.urls", namespace="appointments")),
    path("questionnaires/", include("questionnaires.urls")),
]
