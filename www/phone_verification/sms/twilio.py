"""Twilio-based SMS provider."""

from __future__ import annotations

import logging

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from twilio.rest import Client

logger = logging.getLogger(__name__)


class TwilioSmsProvider:
    """Send SMS messages via Twilio."""

    def __init__(
        self,
        *,
        account_sid: str | None = None,
        auth_token: str | None = None,
        from_number: str | None = None,
    ):
        config = getattr(settings, "PHONE_VERIFICATION_TWILIO", {}) or {}
        self.account_sid = account_sid or config.get("ACCOUNT_SID")
        self.auth_token = auth_token or config.get("AUTH_TOKEN")
        self.from_number = from_number or config.get("FROM_NUMBER")

        missing = [
            name
            for name, value in [
                ("TWILIO_ACCOUNT_SID", self.account_sid),
                ("TWILIO_AUTH_TOKEN", self.auth_token),
                ("TWILIO_FROM_NUMBER", self.from_number),
            ]
            if not value
        ]
        if missing:
            raise ImproperlyConfigured(
                "Missing Twilio configuration values: " + ", ".join(missing)
            )

        self.client = Client(self.account_sid, self.auth_token)

    def send(self, *, phone_number: str, message: str) -> None:
        logger.debug("Sending Twilio SMS to %s", phone_number)
        self.client.messages.create(
            body=message,
            from_=self.from_number,
            to=phone_number,
        )
