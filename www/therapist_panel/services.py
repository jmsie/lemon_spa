"""Service helpers for therapist panel."""

from __future__ import annotations

from datetime import timedelta

from django.utils import timezone

from appointments.models import Appointment
from scheduling.models import TherapistTimeOff, TherapistWorkingHours
from scheduling.utils import ensure_timezone, to_utc
from therapist_panel.models import Therapist, TherapistTreatment


def get_today_appointments(therapist: Therapist) -> list[Appointment]:
    """Return all appointments starting today for the given therapist."""

    tzinfo = ensure_timezone(therapist.timezone)
    local_now = timezone.localtime(timezone.now(), timezone=tzinfo)
    start_of_day_local = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day_local = start_of_day_local + timedelta(days=1)
    start_of_day = to_utc(start_of_day_local, therapist.timezone)
    end_of_day = to_utc(end_of_day_local, therapist.timezone)

    return list(
        Appointment.objects.filter(
            therapist=therapist,
            start_time__gte=start_of_day,
            start_time__lt=end_of_day,
        )
        .select_related("treatment")
        .order_by("start_time")
    )


def get_onboarding_status(therapist: Therapist) -> dict[str, int | bool]:
    """Return counts and completion status for therapist onboarding."""

    treatments_count = TherapistTreatment.objects.filter(therapist=therapist).count()
    working_hours_count = TherapistWorkingHours.objects.filter(
        therapist=therapist,
        is_generated=False,
        is_skipped=False,
    ).count()
    time_off_count = TherapistTimeOff.objects.filter(
        therapist=therapist,
        is_skipped=False,
    ).count()
    is_complete = all(
        count > 0 for count in (treatments_count, working_hours_count, time_off_count)
    )
    return {
        "treatments_count": treatments_count,
        "working_hours_count": working_hours_count,
        "time_off_count": time_off_count,
        "is_complete": is_complete,
    }


def needs_onboarding(therapist: Therapist) -> bool:
    """Determine if the therapist should be routed through onboarding."""

    status = get_onboarding_status(therapist)
    return not status["is_complete"]
