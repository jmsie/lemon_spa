"""Data models for client profiles."""

from django.conf import settings
from django.db import models


class Client(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="client_profile",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["user__username"]

    def __str__(self) -> str:
        return f"Client profile for {self.user.get_username()}"

    @property
    def phone_number(self) -> str:
        return self.user.phone_number

    @property
    def email(self) -> str:
        return self.user.email

    @property
    def full_name(self) -> str:
        combined = f"{self.user.first_name} {self.user.last_name}".strip()
        return combined or self.user.get_username()
