"""Admin configuration for therapist panel."""

from django.contrib import admin

from .models import Therapist


@admin.register(Therapist)
class TherapistAdmin(admin.ModelAdmin):
    list_display = (
        "nickname",
        "first_name",
        "last_name",
        "phone_number",
        "email",
    )
    search_fields = (
        "first_name",
        "last_name",
        "nickname",
        "phone_number",
        "email",
    )
