"""Data models for therapist information."""

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class Therapist(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="therapist_profile",
    )
    last_name = models.CharField(max_length=150)
    first_name = models.CharField(max_length=150)
    nickname = models.CharField(max_length=150)
    phone_number = models.CharField(max_length=32)
    address = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["last_name", "first_name"]

    def __str__(self) -> str:
        return f"{self.nickname} ({self.first_name} {self.last_name})"


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
