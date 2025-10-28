"""Data models for therapist information."""

from __future__ import annotations

import uuid

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from therapist_panel.constants import DEFAULT_THERAPIST_TIMEZONE


class Therapist(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="therapist_profile",
    )
    nickname = models.CharField(max_length=150)
    address = models.CharField(max_length=255)
    timezone = models.CharField(
        max_length=64,
        default=DEFAULT_THERAPIST_TIMEZONE,
        help_text="IANA timezone identifier describing the therapist's local time.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["user__last_name", "user__first_name"]

    def __str__(self) -> str:
        full_name = self.full_name or self.user.get_username()
        return f"{self.nickname} ({full_name})"

    @property
    def first_name(self) -> str:
        return self.user.first_name

    @first_name.setter
    def first_name(self, value: str) -> None:
        self.user.first_name = value

    @property
    def last_name(self) -> str:
        return self.user.last_name

    @last_name.setter
    def last_name(self, value: str) -> None:
        self.user.last_name = value

    @property
    def phone_number(self) -> str:
        return self.user.phone_number

    @phone_number.setter
    def phone_number(self, value: str) -> None:
        self.user.phone_number = value

    @property
    def email(self) -> str:
        return self.user.email

    @email.setter
    def email(self, value: str) -> None:
        self.user.email = value

    @property
    def full_name(self) -> str:
        combined = f"{self.user.first_name} {self.user.last_name}".strip()
        return combined or self.user.get_username()


class TherapistTreatment(models.Model):
    therapist = models.ForeignKey(
        "therapist_panel.Therapist",
        on_delete=models.CASCADE,
        related_name="treatments",
    )
    name = models.CharField(max_length=150)
    duration_minutes = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        help_text="Length of the session in minutes.",
    )
    price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Charge for the session in local currency.",
    )
    preparation_minutes = models.PositiveIntegerField(
        default=20,
        help_text="Setup time required before the session begins.",
    )
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["therapist", "name"]
        verbose_name = "Therapist treatment"
        verbose_name_plural = "Therapist treatments"

    def __str__(self) -> str:
        return f"{self.name} ({self.duration_minutes} min)"
