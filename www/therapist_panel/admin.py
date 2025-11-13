"""Admin configuration for therapist panel."""

from django.contrib import admin

from .models import Therapist, TherapistTreatment
from scheduling.models import (
    TherapistTimeOff,
    TherapistTimeOffSeries,
    TherapistWorkingHours,
    TherapistWorkingHoursSeries,
)


class TherapistTreatmentInline(admin.TabularInline):
    model = TherapistTreatment
    extra = 0
    fields = ("name", "duration_minutes", "preparation_minutes", "price", "is_active")
    show_change_link = True


@admin.register(Therapist)
class TherapistAdmin(admin.ModelAdmin):
    list_display = (
        "nickname",
        "get_first_name",
        "get_last_name",
        "user",
        "get_phone_number",
        "timezone",
        "get_email",
        "uuid",
    )
    search_fields = (
        "user__first_name",
        "user__last_name",
        "nickname",
        "user__username",
        "user__email",
        "user__phone_number",
        "uuid",
    )
    autocomplete_fields = ("user",)
    inlines = (TherapistTreatmentInline,)
    list_filter = ("timezone",)

    @admin.display(description="First name", ordering="user__first_name")
    def get_first_name(self, obj):
        return obj.user.first_name

    @admin.display(description="Last name", ordering="user__last_name")
    def get_last_name(self, obj):
        return obj.user.last_name

    @admin.display(description="Phone number", ordering="user__phone_number")
    def get_phone_number(self, obj):
        return obj.user.phone_number

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
    search_fields = ("name", "therapist__nickname", "therapist__user__first_name", "therapist__user__last_name")


@admin.register(TherapistTimeOff)
class TherapistTimeOffAdmin(admin.ModelAdmin):
    list_display = (
        "therapist",
        "get_local_starts_at",
        "get_local_ends_at",
        "series",
        "is_skipped",
        "note",
        "created_at",
    )
    list_filter = ("therapist", "is_skipped")
    search_fields = (
        "therapist__nickname",
        "therapist__user__first_name",
        "therapist__user__last_name",
        "note",
    )
    ordering = ("-starts_at",)
    readonly_fields = ("created_at", "updated_at")
    autocomplete_fields = ("therapist",)

    @admin.display(description="Starts at", ordering="starts_at")
    def get_local_starts_at(self, obj):
        from scheduling.utils import from_utc

        return from_utc(obj.starts_at, obj.therapist.timezone).strftime("%Y-%m-%d %H:%M")

    @admin.display(description="Ends at", ordering="ends_at")
    def get_local_ends_at(self, obj):
        from scheduling.utils import from_utc

        return from_utc(obj.ends_at, obj.therapist.timezone).strftime("%Y-%m-%d %H:%M")


@admin.register(TherapistTimeOffSeries)
class TherapistTimeOffSeriesAdmin(admin.ModelAdmin):
    list_display = (
        "therapist",
        "repeat_type",
        "repeat_interval",
        "start_date",
        "start_time",
        "end_time",
        "repeat_until",
        "is_active",
    )
    list_filter = ("repeat_type", "is_active")
    search_fields = (
        "therapist__nickname",
        "therapist__user__first_name",
        "therapist__user__last_name",
        "note",
    )
    autocomplete_fields = ("therapist",)


@admin.register(TherapistWorkingHours)
class TherapistWorkingHoursAdmin(admin.ModelAdmin):
    list_display = (
        "therapist",
        "get_local_starts_at",
        "get_local_ends_at",
        "series",
        "is_generated",
        "is_skipped",
        "note",
        "created_at",
    )
    list_filter = ("therapist", "is_generated", "is_skipped")
    search_fields = (
        "therapist__nickname",
        "therapist__user__first_name",
        "therapist__user__last_name",
        "note",
    )
    ordering = ("-starts_at",)
    readonly_fields = ("created_at", "updated_at")
    autocomplete_fields = ("therapist",)

    @admin.display(description="Starts at", ordering="starts_at")
    def get_local_starts_at(self, obj):
        from scheduling.utils import from_utc

        return from_utc(obj.starts_at, obj.therapist.timezone).strftime("%Y-%m-%d %H:%M")

    @admin.display(description="Ends at", ordering="ends_at")
    def get_local_ends_at(self, obj):
        from scheduling.utils import from_utc

        return from_utc(obj.ends_at, obj.therapist.timezone).strftime("%Y-%m-%d %H:%M")


@admin.register(TherapistWorkingHoursSeries)
class TherapistWorkingHoursSeriesAdmin(admin.ModelAdmin):
    list_display = (
        "therapist",
        "weekday",
        "repeat_interval",
        "start_date",
        "start_time",
        "end_time",
        "repeat_until",
        "is_active",
    )
    list_filter = ("weekday", "is_active")
    search_fields = (
        "therapist__nickname",
        "therapist__user__first_name",
        "therapist__user__last_name",
    )
    autocomplete_fields = ("therapist",)
