"""SMS notification helpers for appointments."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from appointments.models import Appointment, TherapistSmsNotificationLog
from phone_verification.sms import get_sms_provider

logger = logging.getLogger(__name__)

MAX_MESSAGE_LENGTH = 60


@dataclass(slots=True)
class NotificationContext:
    therapist_phone: str
    message: str


def notify_new_public_booking(appointment: Appointment) -> None:
    """Send SMS to the therapist when a public booking is submitted."""

    therapist = appointment.therapist
    if not therapist or not therapist.phone_number:
        logger.warning("Skipping therapist SMS; missing phone number for appointment %s", appointment.pk)
        return

    try:
        context = _build_notification_context(appointment)
    except Exception:  # pragma: no cover - defensive
        logger.exception("Failed to build notification context for appointment %s", appointment.pk)
        return

    transaction.on_commit(
        lambda: _send_and_log(appointment=appointment, context=context)
    )


def _build_notification_context(appointment: Appointment) -> NotificationContext:
    therapist = appointment.therapist
    tz_name = therapist.timezone or settings.TIME_ZONE
    try:
        tz = ZoneInfo(tz_name)
    except ZoneInfoNotFoundError:
        tz = timezone.get_current_timezone()

    local_start = timezone.localtime(appointment.start_time, tz)
    date_str = local_start.strftime("%m/%d %H:%M")
    treatment_name = appointment.treatment.name if appointment.treatment else ""
    customer_phone = appointment.customer_phone

    base_without_name = f"新預約{date_str} 客戶{customer_phone}"
    base_message = f"新預約{date_str}{treatment_name} 客戶{customer_phone}"
    if len(base_message) > MAX_MESSAGE_LENGTH:
        max_treatment_len = MAX_MESSAGE_LENGTH - len(base_without_name)
        truncated_name = treatment_name
        if max_treatment_len <= 0:
            base_message = base_without_name[:MAX_MESSAGE_LENGTH]
        else:
            if len(truncated_name) > max_treatment_len:
                if max_treatment_len == 1:
                    truncated_name = treatment_name[:1]
                else:
                    truncated_name = treatment_name[: max_treatment_len - 1] + "…"
            base_message = f"新預約{date_str}{truncated_name} 客戶電話{customer_phone}"

    return NotificationContext(
        therapist_phone=therapist.phone_number,
        message=base_message,
    )


def _send_and_log(*, appointment: Appointment, context: NotificationContext) -> None:
    log_entry = TherapistSmsNotificationLog.objects.create(
        appointment=appointment,
        therapist=appointment.therapist,
        phone_number=context.therapist_phone,
        message=context.message,
    )

    provider = get_sms_provider()
    try:
        provider.send(phone_number=context.therapist_phone, message=context.message)
    except Exception as exc:  # pragma: no cover
        logger.exception(
            "Failed to send therapist SMS for appointment %s to %s",
            appointment.pk,
            context.therapist_phone,
        )
        log_entry.status = TherapistSmsNotificationLog.STATUS_FAILED
        log_entry.error_message = str(exc)[:500]
        log_entry.sent_at = timezone.now()
        log_entry.save(update_fields=["status", "error_message", "sent_at"])
    else:
        log_entry.status = TherapistSmsNotificationLog.STATUS_SENT
        log_entry.sent_at = timezone.now()
        log_entry.save(update_fields=["status", "sent_at"])
