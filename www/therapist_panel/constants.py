"""Shared constants for therapist panel domain."""

from __future__ import annotations

from functools import lru_cache
from typing import Iterable, Tuple
from zoneinfo import available_timezones

DEFAULT_THERAPIST_TIMEZONE = "Asia/Taipei"


@lru_cache
def therapist_timezone_choices() -> Tuple[Tuple[str, str], ...]:
    """Return cached list of available IANA timezone choices."""

    def _build(source: Iterable[str]) -> Tuple[Tuple[str, str], ...]:
        sorted_zones = sorted(source)
        return tuple((tz, tz) for tz in sorted_zones)

    return _build(available_timezones())


THERAPIST_TIMEZONE_CHOICES = therapist_timezone_choices()

__all__ = [
    "DEFAULT_THERAPIST_TIMEZONE",
    "THERAPIST_TIMEZONE_CHOICES",
    "therapist_timezone_choices",
]
