"""Tests for therapist SMS notifications."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from appointments.models import Appointment, TherapistSmsNotificationLog
from appointments.notifications import notify_new_public_booking
from therapist_panel.constants import DEFAULT_THERAPIST_TIMEZONE
from therapist_panel.models import Therapist, TherapistTreatment


class TherapistSmsNotificationTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="therapist",
            password="password123",
            email="therapist@example.com",
        )
        self.therapist = Therapist.objects.create(
            user=self.user,
            last_name="Doe",
            first_name="Jane",
            nickname="JD",
            phone_number="+886900000000",
            address="123 Main St",
            timezone=DEFAULT_THERAPIST_TIMEZONE,
        )
        self.treatment = TherapistTreatment.objects.create(
            therapist=self.therapist,
            name="全身按摩 90 分",
            duration_minutes=90,
            preparation_minutes=10,
            price="2200.00",
        )
        start_time = timezone.now() + timedelta(days=1)
        self.appointment = Appointment.objects.create(
            therapist=self.therapist,
            treatment=self.treatment,
            start_time=start_time,
            end_time=start_time + timedelta(minutes=100),
            customer_name="Alice",
            customer_phone="+886987654321",
        )

    def test_notification_success_is_logged(self):
        fake_provider = Mock()
        with patch("appointments.notifications.get_sms_provider", return_value=fake_provider):
            with self.captureOnCommitCallbacks(execute=True):
                notify_new_public_booking(self.appointment)

        fake_provider.send.assert_called_once()
        log = TherapistSmsNotificationLog.objects.get()
        self.assertEqual(log.status, TherapistSmsNotificationLog.STATUS_SENT)
        self.assertLessEqual(len(log.message), 60)
        self.assertIn("新預約", log.message)
        self.assertIn("客戶", log.message)

    def test_notification_failure_logged(self):
        fake_provider = Mock()
        fake_provider.send.side_effect = RuntimeError("Twilio error")
        with patch("appointments.notifications.get_sms_provider", return_value=fake_provider):
            with self.captureOnCommitCallbacks(execute=True):
                notify_new_public_booking(self.appointment)

        log = TherapistSmsNotificationLog.objects.get()
        self.assertEqual(log.status, TherapistSmsNotificationLog.STATUS_FAILED)
        self.assertIn("Twilio error", log.error_message)
