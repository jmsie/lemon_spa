"""Tests for appointment forms."""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from appointments.forms import AppointmentForm
from therapist_panel.constants import DEFAULT_THERAPIST_TIMEZONE
from therapist_panel.models import Therapist, TherapistTreatment


class AppointmentFormPhoneTests(TestCase):
    """Ensure phone numbers are normalized and validated."""

    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="therapist",
            password="password123",
            email="therapist@example.com",
            first_name="Jane",
            last_name="Doe",
            phone_number="+886900000700",
        )
        self.therapist = Therapist.objects.create(
            user=self.user,
            nickname="JD",
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

    def test_clean_customer_phone_normalizes_e164(self):
        form = AppointmentForm(
            data={
                "therapist": self.therapist.pk,
                "treatment": self.treatment.pk,
                "start_time": timezone.now().replace(microsecond=0).isoformat(),
                "customer_name": "Client",
                "customer_phone_region": "TW",
                "customer_phone_national": "0987-654-321",
                "customer_phone": "",
                "note": "",
            }
        )
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["customer_phone"], "+886987654321")

    def test_clean_customer_phone_rejects_invalid_input(self):
        form = AppointmentForm(
            data={
                "therapist": self.therapist.pk,
                "treatment": self.treatment.pk,
                "start_time": timezone.now().replace(microsecond=0).isoformat(),
                "customer_name": "Client",
                "customer_phone_region": "TW",
                "customer_phone_national": "12345",
                "customer_phone": "",
                "note": "",
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("customer_phone_national", form.errors)
