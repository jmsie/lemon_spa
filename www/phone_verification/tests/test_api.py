"""API tests for phone verification endpoints."""

from __future__ import annotations

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from appointments.models import Appointment
from phone_verification.models import PhoneVerification
from therapist_panel.constants import DEFAULT_THERAPIST_TIMEZONE
from therapist_panel.models import Therapist, TherapistTreatment


class PhoneVerificationAPITests(APITestCase):
    """Exercise the phone verification REST endpoints."""

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
        start_time = timezone.now() + timedelta(days=1)
        self.appointment = Appointment.objects.create(
            therapist=self.therapist,
            treatment=self.treatment,
            start_time=start_time,
            end_time=start_time + timedelta(minutes=70),
            customer_name="Client",
            customer_phone="+886987654321",
        )
        self.resend_url = reverse("api:phone_verification:resend")
        self.verify_url = reverse("api:phone_verification:verify")

    def test_resend_generates_new_code(self):
        response = self.client.post(
            self.resend_url,
            {
                "phone_number": "+886987654321",
                "appointment_uuid": str(self.appointment.uuid),
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertTrue(data["success"])
        verification = data["verification"]
        self.assertEqual(verification["status"], "sent")
        self.assertEqual(verification["phone_number"], "+886987654321")
        self.assertIn("expires_at", verification)
        self.assertTrue(PhoneVerification.objects.filter(phone_number="+886987654321").exists())

    def test_resend_rate_limited(self):
        PhoneVerification.objects.create(
            phone_number="+886987654321",
            code_hash=make_password("1234"),
            expires_at=timezone.now() + timedelta(minutes=5),
            send_count=1,
            last_sent_at=timezone.now(),
            is_verified=False,
        )

        response = self.client.post(
            self.resend_url,
            {
                "phone_number": "+886987654321",
                "appointment_uuid": str(self.appointment.uuid),
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        verification = response.json()["verification"]
        self.assertEqual(verification["error_code"], "SendRateLimited")

    def test_verify_success(self):
        PhoneVerification.objects.create(
            phone_number="+886987654321",
            code_hash=make_password("1234"),
            expires_at=timezone.now() + timedelta(minutes=5),
            last_sent_at=timezone.now() - timedelta(minutes=1),
            is_verified=False,
        )

        response = self.client.post(
            self.verify_url,
            {
                "phone_number": "+886987654321",
                "appointment_uuid": str(self.appointment.uuid),
                "code": "1234",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["appointment"]["uuid"], str(self.appointment.uuid))

    def test_verify_invalid_code(self):
        PhoneVerification.objects.create(
            phone_number="+886987654321",
            code_hash=make_password("1234"),
            expires_at=timezone.now() + timedelta(minutes=5),
            last_sent_at=timezone.now() - timedelta(minutes=1),
            is_verified=False,
        )

        response = self.client.post(
            self.verify_url,
            {
                "phone_number": "+886987654321",
                "appointment_uuid": str(self.appointment.uuid),
                "code": "0000",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data = response.json()
        self.assertEqual(data["error_code"], "InvalidVerificationCode")
