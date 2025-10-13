"""Utility helpers for phone verification."""

from __future__ import annotations

import phonenumbers
from phonenumbers import PhoneNumberFormat
from phonenumbers.phonenumberutil import NumberParseException

from phone_verification import exceptions


def normalize_phone_number(raw_number: str) -> str:
    """Convert the input phone string into E.164 format."""

    try:
        parsed = phonenumbers.parse(raw_number, None)
    except NumberParseException as exc:  # pragma: no cover - defensive
        raise exceptions.InvalidPhoneNumber(str(exc)) from exc

    if not phonenumbers.is_valid_number(parsed):
        raise exceptions.InvalidPhoneNumber("Phone number is not valid.")

    return phonenumbers.format_number(parsed, PhoneNumberFormat.E164)


def mask_phone_number(phone_number: str) -> str:
    """Return a lightly masked representation for logging."""

    if len(phone_number) <= 4:
        return "*" * len(phone_number)
    return f"{phone_number[:-4]}****"

