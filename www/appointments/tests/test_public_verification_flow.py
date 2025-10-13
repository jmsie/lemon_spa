"""Tests covering the public booking phone verification flow."""

from __future__ import annotations

from datetime import timedelta, timezone as dt_timezone

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from appointments.models import Appointment
from phone_verification.models import PhoneVerification
from therapist_panel.constants import DEFAULT_THERAPIST_TIMEZONE
from therapist_panel.models import Therapist, TherapistTreatment


class AppointmentPhoneVerificationTests(TestCase):
    """Ensure booking flow interacts with phone verification as expected."""

    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
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
            name="Deep Tissue",
            duration_minutes=60,
            preparation_minutes=10,
            price="120.00",
        )
        self.booking_url = reverse("appointments:book")
        self.start_time = (timezone.now() + timedelta(days=1)).replace(microsecond=0)

    def _payload(self, phone: str) -> dict[str, str]:
        start_iso = (
            self.start_time.astimezone(dt_timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z")
        )
        return {
            "therapist": str(self.therapist.pk),
            "treatment": str(self.treatment.pk),
            "start_time": start_iso,
            "appointment-date": self.start_time.date().isoformat(),
            "customer_name": "Client",
            "customer_phone": phone,
            "note": "",
        }

    def test_new_phone_triggers_verification(self):
        payload = self._payload("+886987654321")
        response = self.client.post(
            self.booking_url,
            data=payload,
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
            HTTP_ACCEPT="application/json",
        )

        self.assertEqual(response.status_code, 202)
        data = response.json()
        self.assertTrue(data["verification_required"])
        self.assertIn("appointment", data)
        self.assertIn("verification", data)
        verification = data["verification"]
        self.assertEqual(verification["status"], "sent")
        self.assertEqual(verification["phone_number"], "+886987654321")
        self.assertIn("expires_at", verification)
        appointment = Appointment.objects.get()
        self.assertEqual(str(appointment.uuid), data["appointment"]["uuid"])

    def test_verified_phone_skips_verification(self):
        PhoneVerification.objects.create(
            phone_number="+886987654321",
            code_hash="unused",
            expires_at=timezone.now(),
            is_verified=True,
            verified_at=timezone.now(),
        )

        payload = self._payload("+886987654321")
        response = self.client.post(
            self.booking_url,
            data=payload,
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
            HTTP_ACCEPT="application/json",
        )

        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertNotIn("verification", data)

    def test_rate_limited_phone_returns_error_payload(self):
        PhoneVerification.objects.create(
            phone_number="+886987654321",
            code_hash="unused",
            expires_at=timezone.now() + timedelta(minutes=5),
            send_count=1,
            attempt_count=0,
            last_sent_at=timezone.now(),
            is_verified=False,
        )

        payload = self._payload("+886987654321")
        response = self.client.post(
            self.booking_url,
            data=payload,
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
            HTTP_ACCEPT="application/json",
        )

        self.assertEqual(response.status_code, 429)
        data = response.json()
        self.assertTrue(data["verification_required"])
        verification = data["verification"]
        self.assertEqual(verification["status"], "error")
        self.assertEqual(verification["error_code"], "SendRateLimited")
        self.assertIn("resend_available_in", verification)
