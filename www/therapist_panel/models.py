"""Data models for therapist information."""

from django.db import models


class Therapist(models.Model):
    last_name = models.CharField(max_length=150)
    first_name = models.CharField(max_length=150)
    nickname = models.CharField(max_length=150)
    phone_number = models.CharField(max_length=32)
    address = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["last_name", "first_name"]

    def __str__(self) -> str:
        return f"{self.nickname} ({self.first_name} {self.last_name})"
