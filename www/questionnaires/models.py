"""Data models for service questionnaires."""

from __future__ import annotations

from django.db import models
from django.utils import timezone

from appointments.models import Appointment


class Questionnaire(models.Model):
    """Post-service survey filled out for a therapist."""

    RATING_CHOICES = [(i, f"{i} 星") for i in range(1, 6)]

    appointment = models.OneToOneField(
        Appointment,
        on_delete=models.PROTECT,
        related_name="questionnaire",
        verbose_name="預約",
        null=True,
        blank=True,
    )
    therapist = models.ForeignKey(
        "therapist_panel.Therapist",
        on_delete=models.CASCADE,
        related_name="service_surveys",
    )
    rating = models.PositiveSmallIntegerField(
        choices=RATING_CHOICES,
        default=5,
        verbose_name="星級",
    )
    comment = models.TextField(blank=True, verbose_name="備註")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="填寫時間")

    class Meta:
        verbose_name = "服務問卷"
        verbose_name_plural = "服務問卷"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.therapist} - {self.rating} 星"
