"""Admin configuration for appointments."""

from django.contrib import admin

from .models import Appointment


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = (
        "uuid",
        "therapist",
        "treatment",
        "start_time",
        "end_time",
        "customer_name",
        "customer_phone",
        "is_cancelled",
    )
    search_fields = (
        "customer_name",
        "customer_phone",
        "therapist__first_name",
        "therapist__last_name",
        "therapist__nickname",
    )
    list_filter = ("therapist", "treatment", "is_cancelled")
    ordering = ("-start_time",)
