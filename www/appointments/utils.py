"""Utility helpers for appointments."""

from __future__ import annotations

from typing import Any

from appointments.models import Appointment


def serialize_public_appointment(appointment: Appointment) -> dict[str, Any]:
    """Return the public-facing appointment payload used by the booking flow."""

    therapist = appointment.therapist
    treatment = appointment.treatment

    return {
        "uuid": str(appointment.uuid),
        "start_time": appointment.start_time.isoformat(),
        "therapist": {
            "id": therapist.pk,
            "uuid": str(therapist.uuid),
            "nickname": therapist.nickname,
            "phone_number": therapist.phone_number,
            "address": therapist.address,
            "timezone": therapist.timezone,
        },
        "treatment": {
            "id": treatment.pk,
            "name": treatment.name,
            "duration_minutes": treatment.duration_minutes,
        },
        "customer": {
            "name": appointment.customer_name,
            "phone": appointment.customer_phone,
        },
    }
