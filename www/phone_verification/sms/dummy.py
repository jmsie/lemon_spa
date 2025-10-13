"""Dummy SMS provider used for development/testing."""

from __future__ import annotations

import logging

from phone_verification.sms.base import SmsProvider

logger = logging.getLogger(__name__)


class DummySmsProvider:
    """Log messages instead of sending real SMS."""

    def send(self, *, phone_number: str, message: str) -> None:
        logger.info("Dummy SMS to %s: %s", phone_number, message)

