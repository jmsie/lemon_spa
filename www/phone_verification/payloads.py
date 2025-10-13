"""Helper functions for building verification payloads."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from django.utils import timezone

from phone_verification.exceptions import PhoneVerificationError
from phone_verification.services import PhoneVerificationService
from phone_verification.services.verification import SendCodeResult


def build_verification_success_payload(
    *,
    result: SendCodeResult,
    service: PhoneVerificationService,
) -> dict[str, Any]:
    """Return a standardized payload when an SMS has been sent."""

    verification = result.verification
    resend_interval = service.resend_interval_seconds
    resend_available_in = result.resend_available_in or resend_interval
    resend_available_at = (
        verification.last_sent_at + timedelta(seconds=resend_interval)
        if verification.last_sent_at
        else None
    )
    attempts_remaining = max(service.max_attempts - verification.attempt_count, 0)

    return {
        "status": "sent",
        "phone_number": verification.phone_number,
        "expires_at": verification.expires_at.isoformat(),
        "resend_available_in": resend_available_in,
        "resend_available_at": resend_available_at.isoformat() if resend_available_at else None,
        "attempts_remaining": attempts_remaining,
        "max_attempts": service.max_attempts,
        "send_count": verification.send_count,
        "max_send_count": service.max_send_count,
        "message": "驗證碼已傳送至您的手機。",
    }


def build_verification_error_payload(
    *,
    phone_number: str,
    status: dict[str, Any],
    error: PhoneVerificationError,
    service: PhoneVerificationService,
) -> dict[str, Any]:
    """Return a standardized payload when verification fails."""

    base_message = str(error) or "手機驗證失敗，請稍後再試。"

    payload: dict[str, Any] = {
        "status": "error",
        "phone_number": status.get("phone_number", phone_number),
        "message": base_message,
        "error_code": error.__class__.__name__,
        "context": getattr(error, "context", {}),
    }

    expires_at = status.get("expires_at")
    if expires_at:
        payload["expires_at"] = expires_at.isoformat()

    payload["attempts_remaining"] = max(service.max_attempts - status.get("attempt_count", 0), 0)
    payload["max_attempts"] = service.max_attempts
    payload["send_count"] = status.get("send_count")
    payload["max_send_count"] = service.max_send_count

    wait_seconds = payload["context"].get("wait_seconds")
    if wait_seconds is not None:
        payload["resend_available_in"] = wait_seconds
        payload["resend_available_at"] = (
            timezone.now() + timedelta(seconds=wait_seconds)
        ).isoformat()

    friendly_messages = {
        "SendRateLimited": "驗證碼已寄出，請稍候再試。",
        "SendLimitReached": "驗證碼發送次數已達上限，請聯絡客服人員協助。",
        "VerificationAlreadyConfirmed": "手機已完成驗證。",
    }
    payload["message"] = friendly_messages.get(payload["error_code"], payload["message"])

    return payload
