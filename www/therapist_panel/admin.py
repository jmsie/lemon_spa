"""Admin configuration for therapist panel."""

from django.contrib import admin

from .models import Therapist


@admin.register(Therapist)
class TherapistAdmin(admin.ModelAdmin):
    list_display = (
        "nickname",
        "first_name",
        "last_name",
        "user",
        "phone_number",
        "get_email",
    )
    search_fields = (
        "first_name",
        "last_name",
        "nickname",
        "user__username",
        "user__email",
        "phone_number",
    )
    autocomplete_fields = ("user",)

    @admin.display(description="Email", ordering="user__email")
    def get_email(self, obj):
        return obj.user.email
