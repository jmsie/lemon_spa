"""Admin configuration for appointments."""

from django.contrib import admin

from .models import Appointment, AppointmentQuestionnaireLog, TherapistSmsNotificationLog


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
        "therapist__user__first_name",
        "therapist__user__last_name",
        "therapist__nickname",
    )
    list_filter = ("therapist", "treatment", "is_cancelled")
    ordering = ("-start_time",)


@admin.register(TherapistSmsNotificationLog)
class TherapistSmsNotificationLogAdmin(admin.ModelAdmin):
    list_display = ("appointment", "therapist", "phone_number", "status", "sent_at", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("appointment__customer_name", "therapist__nickname", "phone_number")
    readonly_fields = ("appointment", "therapist", "phone_number", "message", "status", "error_message", "created_at", "sent_at")


@admin.register(AppointmentQuestionnaireLog)
class AppointmentQuestionnaireLogAdmin(admin.ModelAdmin):
    list_display = ("appointment", "therapist", "phone_number", "status", "sent_at", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("appointment__customer_name", "therapist__nickname", "phone_number")
    readonly_fields = ("appointment", "therapist", "phone_number", "message", "status", "error_message", "created_at", "sent_at")
