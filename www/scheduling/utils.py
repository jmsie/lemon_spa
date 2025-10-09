"""Utility helpers for scheduling services."""

from __future__ import annotations

from datetime import datetime, timezone as dt_timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.utils import timezone

from therapist_panel.constants import DEFAULT_THERAPIST_TIMEZONE


def ensure_timezone(tz_name: str | None) -> ZoneInfo:
    """Return a ZoneInfo instance for the supplied timezone name.

    Falls back to the default therapist timezone when the provided name is
    empty or invalid. The helper avoids leaking ZoneInfoNotFoundError outside
    of the scheduling layer.
    """

    candidate = tz_name or DEFAULT_THERAPIST_TIMEZONE
    try:
        return ZoneInfo(candidate)
    except ZoneInfoNotFoundError:  # pragma: no cover - defensive fallback
        return ZoneInfo(DEFAULT_THERAPIST_TIMEZONE)


def to_utc(value: datetime, tz_name: str | None) -> datetime:
    """Convert a datetime expressed in the given timezone to UTC."""

    tzinfo = ensure_timezone(tz_name)
    if timezone.is_naive(value):
        localized = value.replace(tzinfo=tzinfo)
    else:
        localized = value.astimezone(tzinfo)
    return localized.astimezone(dt_timezone.utc)


def to_local(value: datetime, tz_name: str | None) -> datetime:
    """Convert a datetime to the supplied timezone without losing wall-clock information."""

    tzinfo = ensure_timezone(tz_name)
    if timezone.is_naive(value):
        return value.replace(tzinfo=tzinfo)
    return value.astimezone(tzinfo)


def from_utc(value: datetime, tz_name: str | None) -> datetime:
    """Return the datetime converted from UTC into the supplied timezone."""

    tzinfo = ensure_timezone(tz_name)
    return timezone.localtime(value, timezone=tzinfo)


__all__ = ["ensure_timezone", "to_utc", "to_local", "from_utc"]
