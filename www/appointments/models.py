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


class TherapistSmsNotificationLog(models.Model):
    """Record SMS notification attempts sent to therapists."""

    STATUS_PENDING = "pending"
    STATUS_SENT = "sent"
    STATUS_FAILED = "failed"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_SENT, "Sent"),
        (STATUS_FAILED, "Failed"),
    ]

    appointment = models.ForeignKey(
        Appointment,
        on_delete=models.CASCADE,
        related_name="therapist_sms_logs",
    )
    therapist = models.ForeignKey(
        "therapist_panel.Therapist",
        on_delete=models.CASCADE,
        related_name="sms_notification_logs",
    )
    phone_number = models.CharField(max_length=32)
    message = models.CharField(max_length=160)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=STATUS_PENDING)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.therapist.nickname} - {self.status} @ {self.created_at:%Y-%m-%d %H:%M}"
