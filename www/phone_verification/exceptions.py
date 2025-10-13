"""Custom exceptions for phone verification workflows."""

from __future__ import annotations

from typing import Any


class PhoneVerificationError(Exception):
    """Base exception for phone verification issues."""

    def __init__(self, message: str = "", **context: Any):
        super().__init__(message)
        self.context: dict[str, Any] = context


class InvalidPhoneNumber(PhoneVerificationError):
    """Raised when an invalid phone number is supplied."""


class SendRateLimited(PhoneVerificationError):
    """Raised when a verification SMS was requested too soon."""


class SendLimitReached(PhoneVerificationError):
    """Raised when the maximum number of sends is reached."""


class VerificationExpired(PhoneVerificationError):
    """Raised when the verification code has expired."""


class VerificationAttemptsExceeded(PhoneVerificationError):
    """Raised when too many incorrect attempts have been made."""


class InvalidVerificationCode(PhoneVerificationError):
    """Raised when code does not match the stored hash."""


class VerificationAlreadyConfirmed(PhoneVerificationError):
    """Raised when verification is attempted on an already verified number."""
