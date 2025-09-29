"""URL routing for client dashboard."""

from django.urls import path

from .views import ClientDashboardView

app_name = "client_dashboard"

urlpatterns = [
    path("", ClientDashboardView.as_view(), name="index"),
]
