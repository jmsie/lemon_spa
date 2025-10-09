"""Data models for scheduling domain objects."""

from __future__ import annotations

import uuid

from django.db import models


class TherapistTimeOff(models.Model):
    """Represent a block of time where a therapist is unavailable for appointments."""

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    therapist = models.ForeignKey(
        "therapist_panel.Therapist",
        on_delete=models.CASCADE,
        related_name="time_off_periods",
    )
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["starts_at"]
        verbose_name = "Therapist time off"
        verbose_name_plural = "Therapist time off"
        indexes = [
            models.Index(fields=["therapist", "starts_at"]),
            models.Index(fields=["therapist", "ends_at"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(ends_at__gt=models.F("starts_at")),
                name="therapist_time_off_end_after_start",
            )
        ]

    def __str__(self) -> str:
        from scheduling.utils import from_utc  # Lazy import to avoid circular dependencies

        start = from_utc(self.starts_at, self.therapist.timezone) if self.starts_at else None
        end = from_utc(self.ends_at, self.therapist.timezone) if self.ends_at else None
        if start and end:
            return f"{self.therapist.nickname} off {start:%Y-%m-%d %H:%M} – {end:%Y-%m-%d %H:%M}"
        return f"{self.therapist.nickname} time off"
