"""Base interfaces for SMS providers."""

from __future__ import annotations

from typing import Protocol


class SmsProvider(Protocol):
    """Protocol expected from SMS provider implementations."""

    def send(self, *, phone_number: str, message: str) -> None:
        """Send ``message`` to ``phone_number``."""

