"""Tests for the therapist availability API."""

from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from appointments.models import Appointment
from scheduling.models import TherapistTimeOff, TherapistWorkingHours
from scheduling.utils import to_utc
from therapist_panel.constants import DEFAULT_THERAPIST_TIMEZONE
from therapist_panel.models import Therapist, TherapistTreatment


class TherapistAvailabilityAPITests(APITestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="therapist",
            password="testpass123",
            email="therapist@example.com",
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
            name="Massage",
            duration_minutes=60,
            preparation_minutes=0,
            price="80.00",
        )
        self.tz = ZoneInfo(self.therapist.timezone)
        self.availability_url = reverse(
            "api:appointments:availability", args=[self.therapist.uuid]
        )

    def test_availability_returns_windows(self):
        working_start = datetime(2024, 3, 1, 9, 0, tzinfo=self.tz)
        working_end = datetime(2024, 3, 1, 17, 0, tzinfo=self.tz)
        TherapistWorkingHours.objects.create(
            therapist=self.therapist,
            starts_at=to_utc(working_start, self.therapist.timezone),
            ends_at=to_utc(working_end, self.therapist.timezone),
            note="Day shift",
        )

        time_off_start = datetime(2024, 3, 1, 12, 0, tzinfo=self.tz)
        time_off_end = datetime(2024, 3, 1, 13, 0, tzinfo=self.tz)
        TherapistTimeOff.objects.create(
            therapist=self.therapist,
            starts_at=to_utc(time_off_start, self.therapist.timezone),
            ends_at=to_utc(time_off_end, self.therapist.timezone),
            note="Lunch",
        )

        appointment_start = datetime(2024, 3, 1, 15, 0, tzinfo=self.tz)
        Appointment.objects.create(
            therapist=self.therapist,
            treatment=self.treatment,
            start_time=to_utc(appointment_start, self.therapist.timezone),
            end_time=to_utc(
                appointment_start + timedelta(minutes=60), self.therapist.timezone
            ),
            customer_name="Client A",
            customer_phone="555-0100",
        )

        response = self.client.get(
            self.availability_url,
            {
                "start": "2024-03-01T00:00:00",
                "end": "2024-03-02T00:00:00",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = response.json()
        self.assertEqual(payload["therapist_uuid"], str(self.therapist.uuid))
        self.assertIn("available", payload)
        self.assertIn("blocked", payload)

        self.assertEqual(len(payload["available"]), 1)
        self.assertEqual(
            payload["available"][0]["start"], "2024-03-01T09:00:00+08:00"
        )
        self.assertEqual(payload["available"][0]["end"], "2024-03-01T17:00:00+08:00")

        blocked_intervals = payload["blocked"]
        self.assertEqual(len(blocked_intervals), 2)
        starts = {entry["start"] for entry in blocked_intervals}
        self.assertIn("2024-03-01T12:00:00+08:00", starts)
        self.assertIn("2024-03-01T15:00:00+08:00", starts)

    def test_missing_parameters_returns_400(self):
        response = self.client.get(self.availability_url, {"start": "2024-03-01T00:00"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_range_limit_enforced(self):
        response = self.client.get(
            self.availability_url,
            {
                "start": "2024-01-01T00:00:00",
                "end": "2024-02-15T00:00:00",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_nonexistent_therapist_returns_404(self):
        url = reverse(
            "api:appointments:availability",
            args=["00000000-0000-0000-0000-000000000000"],
        )
        response = self.client.get(
            url, {"start": "2024-03-01T00:00:00", "end": "2024-03-02T00:00:00"}
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
