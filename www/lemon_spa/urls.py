"""lemon_spa URL Configuration."""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("lemon_spa.api.urls", namespace="api")),
]
