"""Data models for scheduling domain objects."""

from __future__ import annotations

import uuid

from django.db import models


class TherapistTimeOffSeries(models.Model):
    """Describe a recurring time off pattern for a therapist."""

    REPEAT_DAILY = "daily"
    REPEAT_WEEKLY = "weekly"
    REPEAT_CHOICES = (
        (REPEAT_DAILY, "Daily"),
        (REPEAT_WEEKLY, "Weekly"),
    )

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    therapist = models.ForeignKey(
        "therapist_panel.Therapist",
        on_delete=models.CASCADE,
        related_name="time_off_series",
    )
    repeat_type = models.CharField(max_length=16, choices=REPEAT_CHOICES)
    repeat_interval = models.PositiveIntegerField(default=1)
    start_date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    repeat_until = models.DateField(blank=True, null=True)
    note = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["start_date", "start_time"]
        verbose_name = "Therapist time off series"
        verbose_name_plural = "Therapist time off series"
        indexes = [
            models.Index(fields=["therapist", "start_date"]),
            models.Index(fields=["therapist", "is_active"]),
        ]

    def __str__(self) -> str:
        repeat = "daily" if self.repeat_type == self.REPEAT_DAILY else "weekly"
        return f"{self.therapist.nickname} {repeat} time off starting {self.start_date:%Y-%m-%d}"


class TherapistTimeOff(models.Model):
    """Represent a block of time where a therapist is unavailable for appointments."""

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    therapist = models.ForeignKey(
        "therapist_panel.Therapist",
        on_delete=models.CASCADE,
        related_name="time_off_periods",
    )
    series = models.ForeignKey(
        TherapistTimeOffSeries,
        on_delete=models.CASCADE,
        related_name="occurrences",
        blank=True,
        null=True,
    )
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    note = models.TextField(blank=True)
    is_skipped = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["starts_at"]
        verbose_name = "Therapist time off"
        verbose_name_plural = "Therapist time off"
        indexes = [
            models.Index(fields=["therapist", "starts_at"]),
            models.Index(fields=["therapist", "ends_at"]),
            models.Index(fields=["series", "starts_at"]),
            models.Index(fields=["therapist", "is_skipped"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(ends_at__gt=models.F("starts_at")),
                name="therapist_time_off_end_after_start",
            ),
            models.UniqueConstraint(
                fields=["series", "starts_at"],
                condition=models.Q(series__isnull=False),
                name="therapist_time_off_unique_series_occurrence",
            ),
        ]

    def __str__(self) -> str:
        from scheduling.utils import from_utc  # Lazy import to avoid circular dependencies

        start = from_utc(self.starts_at, self.therapist.timezone) if self.starts_at else None
        end = from_utc(self.ends_at, self.therapist.timezone) if self.ends_at else None
        status = " (skipped)" if self.is_skipped else ""
        if start and end:
            return f"{self.therapist.nickname} off {start:%Y-%m-%d %H:%M} – {end:%Y-%m-%d %H:%M}{status}"
        return f"{self.therapist.nickname} time off{status}"
