from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.constants import ROLE_THERAPIST, SESSION_ACTIVE_ROLE_KEY
from appointments.models import Appointment
from scheduling.utils import to_utc
from therapist_panel.constants import DEFAULT_THERAPIST_TIMEZONE
from therapist_panel.models import Therapist, TherapistTreatment


class TherapistAppointmentSearchViewTests(TestCase):
    def setUp(self):
        self.url = reverse("therapist_panel:appointments")
        User = get_user_model()
        self.user = User.objects.create_user(
            username="therapist",
            password="testpass123",
            email="therapist@example.com",
            first_name="Jane",
            last_name="Doe",
        )
        self.other_user = User.objects.create_user(
            username="viewer",
            password="viewerpass123",
            email="viewer@example.com",
        )
        self.therapist = Therapist.objects.create(
            user=self.user,
            last_name="Doe",
            first_name="Jane",
            nickname="JD",
            phone_number="123456789",
            address="123 Main St",
            timezone=DEFAULT_THERAPIST_TIMEZONE,
        )
        self.treatment = TherapistTreatment.objects.create(
            therapist=self.therapist,
            name="Deep Tissue",
            duration_minutes=60,
            preparation_minutes=0,
            price="1500.00",
        )
        self.tz_name = self.therapist.timezone
        self.tzinfo = ZoneInfo(self.tz_name)
        self.early_appointment = self._create_appointment(
            "Alice",
            "0912000111",
            datetime(2024, 5, 1, 10, 0, tzinfo=self.tzinfo),
        )
        self.mid_appointment = self._create_appointment(
            "Bob",
            "0987000222",
            datetime(2024, 5, 10, 14, 0, tzinfo=self.tzinfo),
        )
        self.future_appointment = self._create_appointment(
            "Charlie",
            "0977000333",
            datetime(2024, 6, 1, 16, 0, tzinfo=self.tzinfo),
        )
        self.api_base = reverse("api:appointments:appointment-list")

    def _create_appointment(self, customer_name, customer_phone, local_start):
        return Appointment.objects.create(
            therapist=self.therapist,
            treatment=self.treatment,
            start_time=to_utc(local_start, self.tz_name),
            customer_name=customer_name,
            customer_phone=customer_phone,
        )

    def _login_as_therapist(self):
        logged_in = self.client.login(username="therapist", password="testpass123")
        self.assertTrue(logged_in, "Failed to log in therapist user for tests.")
        session = self.client.session
        session[SESSION_ACTIVE_ROLE_KEY] = ROLE_THERAPIST
        session.save()

    def test_login_required(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login", response.headers["Location"])

    def test_requires_therapist_role(self):
        self.client.login(username="viewer", password="viewerpass123")
        session = self.client.session
        session[SESSION_ACTIVE_ROLE_KEY] = ROLE_THERAPIST
        session.save()

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)

    def test_lists_appointments_for_authenticated_therapist(self):
        self._login_as_therapist()

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        appointments = list(response.context["appointments"])
        self.assertEqual(len(appointments), 3)
        self.assertIn(self.future_appointment, appointments)
        self.assertContains(response, "Alice")
        self.assertContains(response, "Charlie")

    def test_filters_by_phone(self):
        self._login_as_therapist()

        response = self.client.get(self.url, {"customer_phone": "00222"})

        self.assertEqual(response.status_code, 200)
        appointments = list(response.context["appointments"])
        self.assertEqual(appointments, [self.mid_appointment])

    def test_filters_by_date_range(self):
        self._login_as_therapist()

        response = self.client.get(
            self.url, {"start_date": "2024-05-02", "end_date": "2024-05-20"}
        )

        self.assertEqual(response.status_code, 200)
        appointments = list(response.context["appointments"])
        self.assertEqual(appointments, [self.mid_appointment])

    def test_invalid_date_range_shows_error(self):
        self._login_as_therapist()

        response = self.client.get(
            self.url, {"start_date": "2024-06-10", "end_date": "2024-06-01"}
        )

        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        self.assertIn("結束日期需在開始日期之後", form.errors["end_date"])
        self.assertFalse(response.context["appointments"])

    def test_template_includes_api_base_for_cancellation(self):
        self._login_as_therapist()

        response = self.client.get(self.url)

        self.assertIn("appointments_api_url", response.context)
        self.assertEqual(response.context["appointments_api_url"], self.api_base)
        self.assertContains(response, f'data-appointment-id="{self.mid_appointment.uuid}"')
        self.assertContains(response, self.api_base)
