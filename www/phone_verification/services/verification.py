"""Service orchestration for phone verification workflows."""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.db import transaction
from django.utils import timezone

from phone_verification import exceptions
from phone_verification.models import PhoneVerification, PhoneVerificationAuditLog
from phone_verification.sms import SmsProvider, get_sms_provider
from phone_verification.utils import normalize_phone_number

_DIGITS = "0123456789"


@dataclass(slots=True)
class SendCodeResult:
    """Result payload when (re)sending a verification code."""

    verification: PhoneVerification
    sent: bool
    reason: str | None = None
    wait_seconds: int | None = None


@dataclass(slots=True)
class VerifyCodeResult:
    """Result payload when verifying a submitted code."""

    verification: PhoneVerification
    verified: bool


class PhoneVerificationService:
    """Coordinate verification code issuance and validation."""

    def __init__(self, sms_provider: SmsProvider | None = None):
        config = getattr(settings, "PHONE_VERIFICATION", {})
        self.code_length = int(config.get("CODE_LENGTH", 4))
        self.code_ttl_seconds = int(config.get("CODE_TTL_SECONDS", 5 * 60))
        self.resend_interval_seconds = int(config.get("RESEND_INTERVAL_SECONDS", 60))
        self.max_attempts = int(config.get("MAX_VERIFICATION_ATTEMPTS", 3))
        self.max_send_count = int(config.get("MAX_SEND_COUNT", 3))
        self.sms_provider = sms_provider or get_sms_provider()

    def request_code(self, phone_number: str) -> SendCodeResult:
        """Generate and send a verification code to ``phone_number``."""

        normalized = normalize_phone_number(phone_number)
        now = timezone.now()

        error: exceptions.PhoneVerificationError | None = None
        send_result: SendCodeResult | None = None

        with transaction.atomic():
            verification, created = (
                PhoneVerification.objects.select_for_update()
                .get_or_create(
                    phone_number=normalized,
                    defaults=self._verification_defaults(now),
                )
            )

            if created:
                code = self._generate_code()
                self._apply_new_code(verification, code=code, now=now, reset_counters=True)
                self._log_event(verification, PhoneVerificationAuditLog.EVENT_SEND, {"created": True})
                self._queue_sms(normalized, code)
                return SendCodeResult(verification=verification, sent=True)

            if verification.is_verified:
                error = exceptions.VerificationAlreadyConfirmed("Phone number already verified.")
            else:
                expired = verification.expires_at <= now
                if expired:
                    verification.send_count = 0
                    verification.attempt_count = 0

                if verification.send_count >= self.max_send_count and not expired:
                    self._log_event(
                        verification,
                        PhoneVerificationAuditLog.EVENT_RESEND_BLOCKED,
                        {
                            "reason": "send_limit_reached",
                            "max_send_count": self.max_send_count,
                        },
                    )
                    error = exceptions.SendLimitReached("Maximum number of verification messages sent.")
                elif verification.last_sent_at and not expired:
                    delta = now - verification.last_sent_at
                    if delta < timedelta(seconds=self.resend_interval_seconds):
                        wait_seconds = self.resend_interval_seconds - int(delta.total_seconds())
                        self._log_event(
                            verification,
                            PhoneVerificationAuditLog.EVENT_RESEND_BLOCKED,
                            {"reason": "rate_limited", "wait_seconds": wait_seconds},
                        )
                        error = exceptions.SendRateLimited(
                            f"Please wait {wait_seconds} seconds before requesting another code."
                        )

                if error is None:
                    code = self._generate_code()
                    self._apply_new_code(
                        verification,
                        code=code,
                        now=now,
                        reset_counters=expired,
                    )
                    self._log_event(
                        verification,
                        PhoneVerificationAuditLog.EVENT_SEND,
                        {"created": False, "send_count": verification.send_count},
                    )
                    self._queue_sms(normalized, code)
                    send_result = SendCodeResult(verification=verification, sent=True)

        if error:
            raise error
        if send_result is None:
            raise exceptions.PhoneVerificationError("Unexpected verification flow state.")
        return send_result

    def verify_code(self, phone_number: str, submitted_code: str) -> VerifyCodeResult:
        """Validate the code provided by the user."""

        normalized = normalize_phone_number(phone_number)
        now = timezone.now()

        error: exceptions.PhoneVerificationError | None = None
        verify_result: VerifyCodeResult | None = None

        with transaction.atomic():
            try:
                verification = (
                    PhoneVerification.objects.select_for_update()
                    .get(phone_number=normalized)
                )
            except PhoneVerification.DoesNotExist as exc:
                error = exceptions.VerificationExpired("No verification code found.")
                verification = None  # type: ignore[assignment]

            if verification is not None:
                if verification.is_verified:
                    error = exceptions.VerificationAlreadyConfirmed("Phone number already verified.")
                elif verification.expires_at <= now:
                    self._log_event(
                        verification,
                        PhoneVerificationAuditLog.EVENT_CODE_EXPIRED,
                        {"expired_at": verification.expires_at.isoformat()},
                    )
                    error = exceptions.VerificationExpired("Verification code expired.")
                elif verification.attempt_count >= self.max_attempts:
                    self._log_event(
                        verification,
                        PhoneVerificationAuditLog.EVENT_ATTEMPTS_EXCEEDED,
                        {"attempt_count": verification.attempt_count},
                    )
                    error = exceptions.VerificationAttemptsExceeded("Maximum verification attempts exceeded.")
                else:
                    if not check_password(submitted_code, verification.code_hash):
                        verification.attempt_count += 1
                        verification.save(update_fields=["attempt_count", "updated_at"])
                        self._log_event(
                            verification,
                            PhoneVerificationAuditLog.EVENT_CODE_INVALID,
                            {"attempt_count": verification.attempt_count},
                        )
                        if verification.attempt_count >= self.max_attempts:
                            self._log_event(
                                verification,
                                PhoneVerificationAuditLog.EVENT_ATTEMPTS_EXCEEDED,
                                {"attempt_count": verification.attempt_count},
                            )
                            error = exceptions.VerificationAttemptsExceeded("Maximum verification attempts exceeded.")
                        else:
                            error = exceptions.InvalidVerificationCode("The verification code is incorrect.")
                    else:
                        verification.is_verified = True
                        verification.verified_at = now
                        verification.attempt_count = 0
                        verification.save(update_fields=["is_verified", "verified_at", "attempt_count", "updated_at"])
                        self._log_event(
                            verification,
                            PhoneVerificationAuditLog.EVENT_CODE_VERIFIED,
                            {"verified_at": verification.verified_at.isoformat()},
                        )
                        verify_result = VerifyCodeResult(verification=verification, verified=True)

        if error:
            raise error
        if verify_result is None:
            raise exceptions.PhoneVerificationError("Unexpected verification flow state.")
        return verify_result

    def get_status(self, phone_number: str) -> dict[str, Any]:
        """Return the verification status for ``phone_number``."""

        normalized = normalize_phone_number(phone_number)
        now = timezone.now()

        try:
            verification = PhoneVerification.objects.get(phone_number=normalized)
        except PhoneVerification.DoesNotExist:
            return {
                "phone_number": normalized,
                "exists": False,
                "is_verified": False,
                "requires_verification": True,
            }

        return {
            "phone_number": normalized,
            "exists": True,
            "is_verified": verification.is_verified,
            "requires_verification": not verification.is_verified,
            "expires_at": verification.expires_at,
            "expired": verification.expires_at <= now,
            "send_count": verification.send_count,
            "attempt_count": verification.attempt_count,
        }

    def _verification_defaults(self, now):
        return {
            "code_hash": make_password(self._generate_code()),  # placeholder, replaced immediately
            "expires_at": now,
            "attempt_count": 0,
            "send_count": 0,
            "last_sent_at": None,
            "is_verified": False,
        }

    def _apply_new_code(
        self,
        verification: PhoneVerification,
        *,
        code: str,
        now,
        reset_counters: bool,
    ) -> None:
        if reset_counters:
            verification.attempt_count = 0
            verification.send_count = 0

        verification.code_hash = make_password(code)
        verification.expires_at = now + timedelta(seconds=self.code_ttl_seconds)
        verification.last_sent_at = now
        verification.send_count += 1
        verification.is_verified = False
        verification.verified_at = None
        verification.save(
            update_fields=[
                "code_hash",
                "expires_at",
                "attempt_count",
                "send_count",
                "last_sent_at",
                "is_verified",
                "verified_at",
                "updated_at",
            ]
        )

    def _queue_sms(self, phone_number: str, code: str) -> None:
        message = settings.PHONE_VERIFICATION.get(
            "MESSAGE_TEMPLATE",
            "Your Lemon Spa verification code is {code}. It expires in 5 minutes.",
        ).format(code=code)

        transaction.on_commit(
            lambda: self.sms_provider.send(phone_number=phone_number, message=message)
        )

    def _log_event(
        self,
        verification: PhoneVerification,
        event_type: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        PhoneVerificationAuditLog.objects.create(
            verification=verification,
            phone_number=verification.phone_number,
            event_type=event_type,
            metadata=metadata or {},
        )

    def _generate_code(self) -> str:
        return "".join(secrets.choice(_DIGITS) for _ in range(self.code_length))
