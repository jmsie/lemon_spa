"""lemon_spa URL Configuration."""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("lemon_spa.api.urls", namespace="api")),
    path("accounts/", include("accounts.urls", namespace="accounts")),
    path("client_dashboard/", include("client_dashboard.urls", namespace="client_dashboard")),
    path("therapist_panel/", include("therapist_panel.urls", namespace="therapist_panel")),
]
