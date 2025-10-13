"""Database models for phone verification workflows."""

from __future__ import annotations

from django.db import models


class PhoneVerification(models.Model):
    """Track verification codes tied to customer phone numbers."""

    phone_number = models.CharField(max_length=32, unique=True)
    code_hash = models.CharField(max_length=128)
    expires_at = models.DateTimeField()
    attempt_count = models.PositiveSmallIntegerField(default=0)
    send_count = models.PositiveSmallIntegerField(default=0)
    last_sent_at = models.DateTimeField(blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["phone_number"]),
            models.Index(fields=["is_verified", "expires_at"]),
        ]
        verbose_name = "Phone Verification"
        verbose_name_plural = "Phone Verifications"

    def __str__(self) -> str:
        return f"{self.phone_number} (verified={self.is_verified})"


class PhoneVerificationAuditLog(models.Model):
    """Audit log capturing send and verify events."""

    EVENT_SEND = "send"
    EVENT_RESEND_BLOCKED = "resend_blocked"
    EVENT_CODE_VERIFIED = "code_verified"
    EVENT_CODE_INVALID = "code_invalid"
    EVENT_CODE_EXPIRED = "code_expired"
    EVENT_ATTEMPTS_EXCEEDED = "attempts_exceeded"

    EVENT_CHOICES = [
        (EVENT_SEND, "Code sent"),
        (EVENT_RESEND_BLOCKED, "Resend blocked"),
        (EVENT_CODE_VERIFIED, "Code verified"),
        (EVENT_CODE_INVALID, "Invalid code submitted"),
        (EVENT_CODE_EXPIRED, "Expired code submitted"),
        (EVENT_ATTEMPTS_EXCEEDED, "Maximum attempts exceeded"),
    ]

    verification = models.ForeignKey(
        PhoneVerification,
        on_delete=models.CASCADE,
        related_name="audit_logs",
    )
    phone_number = models.CharField(max_length=32)
    event_type = models.CharField(max_length=32, choices=EVENT_CHOICES)
    metadata = models.JSONField(blank=True, default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Phone Verification Audit Log"
        verbose_name_plural = "Phone Verification Audit Logs"
        indexes = [
            models.Index(fields=["phone_number", "event_type"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.phone_number}: {self.event_type} @ {self.created_at:%Y-%m-%d %H:%M:%S}"
