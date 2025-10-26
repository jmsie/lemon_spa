"""Service helpers for scheduling domain logic."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Iterable

from django.db import models, transaction
from django.utils import timezone

from scheduling.models import (
    TherapistTimeOff,
    TherapistTimeOffSeries,
    TherapistWorkingHours,
    TherapistWorkingHoursSeries,
)
from scheduling.utils import ensure_timezone, to_local, to_utc


def _occurrence_delta(series: TherapistTimeOffSeries) -> timedelta:
    if series.repeat_type == TherapistTimeOffSeries.REPEAT_DAILY:
        return timedelta(days=series.repeat_interval)
    if series.repeat_type == TherapistTimeOffSeries.REPEAT_WEEKLY:
        return timedelta(weeks=series.repeat_interval)
    raise ValueError(f"Unsupported repeat type: {series.repeat_type}")


def _first_occurrence_on_or_after(series: TherapistTimeOffSeries, target_date) -> datetime.date:
    current = series.start_date
    if current >= target_date:
        return current

    delta = _occurrence_delta(series)
    if delta.days <= 0:
        return current

    if series.repeat_type == TherapistTimeOffSeries.REPEAT_DAILY:
        days_diff = (target_date - current).days
        steps = days_diff // delta.days
        current = current + timedelta(days=steps * delta.days)
        if current < target_date:
            current = current + timedelta(days=delta.days)
    elif series.repeat_type == TherapistTimeOffSeries.REPEAT_WEEKLY:
        days_diff = (target_date - current).days
        weeks = max(delta.days // 7, 1)
        steps = days_diff // (7 * weeks)
        current = current + timedelta(weeks=steps * weeks)
        if current < target_date:
            current = current + timedelta(weeks=weeks)
    return current


def _iter_occurrence_dates(series: TherapistTimeOffSeries, start_date, end_date) -> Iterable[datetime.date]:
    if series.repeat_until and series.repeat_until < start_date:
        return
    effective_end = series.repeat_until if series.repeat_until else end_date
    if effective_end < start_date:
        return

    current = series.start_date
    if current < start_date:
        current = _first_occurrence_on_or_after(series, start_date)
    delta = _occurrence_delta(series)
    while current <= effective_end:
        yield current
        current = current + delta


@transaction.atomic
def ensure_series_occurrences(therapist, range_start=None, range_end=None) -> None:
    """Materialize recurring time off occurrences for the requested range."""

    tzinfo = ensure_timezone(therapist.timezone)
    now_local = timezone.localtime(timezone.now(), timezone=tzinfo)
    local_start = to_local(range_start, therapist.timezone) if range_start else now_local
    local_end = to_local(range_end, therapist.timezone) if range_end else local_start + timedelta(days=90)

    if local_end < local_start:
        local_end = local_start

    start_date = local_start.date()
    end_date = local_end.date()

    series_qs = (
        TherapistTimeOffSeries.objects.filter(therapist=therapist, is_active=True)
        .filter(start_date__lte=end_date)
        .filter(models.Q(repeat_until__isnull=True) | models.Q(repeat_until__gte=start_date))
    )

    for series in series_qs:
        for occurrence_date in _iter_occurrence_dates(series, start_date, end_date):
            start_local_naive = datetime.combine(occurrence_date, series.start_time)
            end_local_naive = datetime.combine(occurrence_date, series.end_time)
            start_utc = to_utc(start_local_naive, therapist.timezone)
            end_utc = to_utc(end_local_naive, therapist.timezone)

            TherapistTimeOff.objects.get_or_create(
                therapist=therapist,
                series=series,
                starts_at=start_utc,
                defaults={
                    "ends_at": end_utc,
                    "note": series.note,
                    "is_skipped": False,
                },
            )


def _iter_working_hours_dates(series: TherapistWorkingHoursSeries, start_date, end_date) -> Iterable[datetime.date]:
    if series.repeat_until and series.repeat_until < start_date:
        return
    effective_end = series.repeat_until if series.repeat_until else end_date
    if effective_end < start_date:
        return

    interval_weeks = max(series.repeat_interval, 1)
    current = series.start_date
    if current < start_date:
        delta_days = (start_date - current).days
        steps = delta_days // (7 * interval_weeks)
        current = current + timedelta(weeks=steps * interval_weeks)
        while current < start_date:
            current = current + timedelta(weeks=interval_weeks)

    effective_end = min(effective_end, end_date)
    while current <= effective_end:
        yield current
        current = current + timedelta(weeks=interval_weeks)


@transaction.atomic
def ensure_working_hours_occurrences(therapist, range_start=None, range_end=None) -> None:
    """Materialize recurring working-hour occurrences for the requested range."""

    tzinfo = ensure_timezone(therapist.timezone)
    now_local = timezone.localtime(timezone.now(), timezone=tzinfo)
    local_start = to_local(range_start, therapist.timezone) if range_start else now_local
    local_end = to_local(range_end, therapist.timezone) if range_end else local_start + timedelta(days=90)

    if local_end < local_start:
        local_end = local_start

    start_date = local_start.date()
    end_date = local_end.date()

    series_qs = (
        TherapistWorkingHoursSeries.objects.filter(therapist=therapist, is_active=True)
        .filter(start_date__lte=end_date)
        .filter(models.Q(repeat_until__isnull=True) | models.Q(repeat_until__gte=start_date))
    )

    for series in series_qs:
        for occurrence_date in _iter_working_hours_dates(series, start_date, end_date):
            start_local_naive = datetime.combine(occurrence_date, series.start_time)
            end_local_naive = datetime.combine(occurrence_date, series.end_time)
            start_utc = to_utc(start_local_naive, therapist.timezone)
            end_utc = to_utc(end_local_naive, therapist.timezone)

            day_start_local = datetime.combine(occurrence_date, datetime.min.time())
            next_day_local = day_start_local + timedelta(days=1)
            day_start_utc = to_utc(day_start_local, therapist.timezone)
            day_end_utc = to_utc(next_day_local, therapist.timezone)

            has_existing_occurrence = TherapistWorkingHours.objects.filter(
                therapist=therapist,
                series=series,
                starts_at__gte=day_start_utc,
                starts_at__lt=day_end_utc,
                is_skipped=False,
            ).exists()
            if has_existing_occurrence:
                continue

            TherapistWorkingHours.objects.get_or_create(
                therapist=therapist,
                series=series,
                starts_at=start_utc,
                defaults={
                    "ends_at": end_utc,
                    "note": "",
                    "is_generated": True,
                },
            )


__all__ = ["ensure_series_occurrences", "ensure_working_hours_occurrences"]
