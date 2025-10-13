"""Custom exceptions for phone verification workflows."""

from __future__ import annotations


class PhoneVerificationError(Exception):
    """Base exception for phone verification issues."""


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

