"""Admin registrations for phone verification models."""

from __future__ import annotations

from django.contrib import admin

from phone_verification.models import PhoneVerification, PhoneVerificationAuditLog


@admin.register(PhoneVerification)
class PhoneVerificationAdmin(admin.ModelAdmin):
    """Configure admin display for phone verification records."""

    list_display = [
        "phone_number",
        "is_verified",
        "expires_at",
        "attempt_count",
        "send_count",
        "last_sent_at",
        "verified_at",
        "updated_at",
    ]
    list_filter = ["is_verified"]
    search_fields = ["phone_number"]
    readonly_fields = ["created_at", "updated_at", "verified_at", "last_sent_at"]


@admin.register(PhoneVerificationAuditLog)
class PhoneVerificationAuditLogAdmin(admin.ModelAdmin):
    """Expose audit log entries in the admin."""

    list_display = ["phone_number", "event_type", "created_at"]
    list_filter = ["event_type", "created_at"]
    search_fields = ["phone_number", "verification__phone_number"]
    readonly_fields = ["verification", "phone_number", "event_type", "metadata", "created_at"]
