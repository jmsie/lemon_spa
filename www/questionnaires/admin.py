"""Admin configuration for questionnaires."""

from django.contrib import admin

from .models import Questionnaire


@admin.register(Questionnaire)
class QuestionnaireAdmin(admin.ModelAdmin):
    list_display = ("therapist", "rating", "created_at")
    search_fields = (
        "therapist__first_name",
        "therapist__last_name",
        "therapist__nickname",
    )
    list_filter = ("therapist", "rating")
