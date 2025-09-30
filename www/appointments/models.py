"""Data models for appointment scheduling."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from django.db import models


class Appointment(models.Model):
    """Individual booking between a therapist and a customer."""

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    therapist = models.ForeignKey(
        "therapist_panel.Therapist",
        on_delete=models.PROTECT,
        related_name="appointments",
    )
    treatment = models.ForeignKey(
        "therapist_panel.TherapistTreatment",
        on_delete=models.PROTECT,
        related_name="appointments",
    )
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    customer_name = models.CharField(max_length=150)
    customer_phone = models.CharField(max_length=32)
    note = models.TextField(blank=True)
    is_cancelled = models.BooleanField(default=False)

    class Meta:
        db_table = "appoinments"
        ordering = ["start_time"]
        verbose_name = "Appointment"
        verbose_name_plural = "Appointments"
        constraints = [
            models.CheckConstraint(
                check=models.Q(end_time__gt=models.F("start_time")),
                name="appointments_end_after_start",
            )
        ]

    def __str__(self) -> str:
        return f"{self.customer_name} @ {self.start_time:%Y-%m-%d %H:%M}"

    def _computed_end_time(self) -> datetime | None:
        if self.start_time and self.treatment_id:
            total_minutes = self.treatment.duration_minutes + self.treatment.preparation_minutes
            return self.start_time + timedelta(minutes=total_minutes)
        return None

    def save(self, *args, **kwargs):
        computed = self._computed_end_time()
        if computed is not None:
            self.end_time = computed
        super().save(*args, **kwargs)
