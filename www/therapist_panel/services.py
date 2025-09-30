"""Service helpers for therapist panel."""

from __future__ import annotations

from datetime import timedelta

from django.utils import timezone

from appointments.models import Appointment
from therapist_panel.models import Therapist


def get_today_appointments(therapist: Therapist) -> list[Appointment]:
    """Return all appointments starting today for the given therapist."""

    now = timezone.now()
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = start_of_day + timedelta(days=1)

    return list(
        Appointment.objects.filter(
            therapist=therapist,
            start_time__gte=start_of_day,
            start_time__lt=end_of_day,
        )
        .select_related("treatment")
        .order_by("start_time")
    )
