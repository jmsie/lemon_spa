"""Admin configuration for therapist panel."""

from django.contrib import admin

from .models import Therapist, TherapistTreatment


class TherapistTreatmentInline(admin.TabularInline):
    model = TherapistTreatment
    extra = 0
    fields = ("name", "duration_minutes", "preparation_minutes", "price", "is_active")
    show_change_link = True


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
    inlines = (TherapistTreatmentInline,)

    @admin.display(description="Email", ordering="user__email")
    def get_email(self, obj):
        return obj.user.email


@admin.register(TherapistTreatment)
class TherapistTreatmentAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "therapist",
        "duration_minutes",
        "price",
        "preparation_minutes",
        "is_active",
    )
    list_filter = ("is_active",)
    search_fields = ("name", "therapist__nickname", "therapist__first_name", "therapist__last_name")
