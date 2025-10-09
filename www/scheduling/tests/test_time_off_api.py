"""Integration tests for therapist time off API."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from appointments.models import Appointment
from scheduling.models import TherapistTimeOff, TherapistTimeOffSeries
from therapist_panel.constants import DEFAULT_THERAPIST_TIMEZONE
from therapist_panel.models import Therapist, TherapistTreatment


class TherapistTimeOffAPITests(APITestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="therapist", password="pass1234", email="t@example.com")
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
            preparation_minutes=15,
            price=Decimal("80.00"),
        )
        self.client.force_authenticate(user=self.user)
        self.time_off_url = reverse("therapist_panel:api:time_off:time-off-list")

    def test_create_time_off_converts_to_utc_and_returns_localized_response(self):
        payload = {
            "starts_at": "2024-03-01T09:00:00",
            "ends_at": "2024-03-01T12:00:00",
            "note": "Morning break",
        }

        response = self.client.post(self.time_off_url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["therapist_uuid"], str(self.therapist.uuid))
        self.assertEqual(response.data["therapist_timezone"], DEFAULT_THERAPIST_TIMEZONE)
        self.assertFalse(response.data["is_recurring"])
        self.assertIsNone(response.data["series_uuid"])
        self.assertTrue(response.data["starts_at"].endswith("+08:00"))
        self.assertTrue(response.data["ends_at"].endswith("+08:00"))

        record = TherapistTimeOff.objects.get(uuid=response.data["uuid"])
        self.assertEqual(record.starts_at.tzinfo, ZoneInfo("UTC"))
        self.assertEqual(record.ends_at.tzinfo, ZoneInfo("UTC"))
        self.assertEqual(
            record.starts_at,
            datetime(2024, 3, 1, 1, 0, tzinfo=ZoneInfo("UTC")),
        )
        self.assertEqual(
            record.ends_at,
            datetime(2024, 3, 1, 4, 0, tzinfo=ZoneInfo("UTC")),
        )

    def test_appointment_creation_blocked_when_overlapping_time_off(self):
        # Prepare an existing time off window from 09:00 to 12:00 local time.
        local_start = datetime(2024, 3, 1, 9, 0, tzinfo=ZoneInfo(DEFAULT_THERAPIST_TIMEZONE))
        local_end = datetime(2024, 3, 1, 12, 0, tzinfo=ZoneInfo(DEFAULT_THERAPIST_TIMEZONE))
        TherapistTimeOff.objects.create(
            therapist=self.therapist,
            starts_at=local_start.astimezone(ZoneInfo("UTC")),
            ends_at=local_end.astimezone(ZoneInfo("UTC")),
        )

        appointments_url = reverse("api:appointments:appointment-list")
        payload = {
            "treatment": self.treatment.pk,
            "start_time": "2024-03-01T09:30:00",
            "customer_name": "Client A",
            "customer_phone": "987654321",
        }

        response = self.client.post(appointments_url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("overlaps with an existing time off", str(response.data))

    def test_appointment_start_time_saved_in_utc(self):
        appointments_url = reverse("api:appointments:appointment-list")
        payload = {
            "treatment": self.treatment.pk,
            "start_time": "2024-03-02T15:00:00",
            "customer_name": "Client B",
            "customer_phone": "555000111",
        }

        response = self.client.post(appointments_url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        appointment = Appointment.objects.get(uuid=response.data["uuid"])
        self.assertEqual(
            appointment.start_time,
            datetime(2024, 3, 2, 7, 0, tzinfo=ZoneInfo("UTC")),
        )

    def test_update_time_off_uses_uuid_lookup(self):
        record = TherapistTimeOff.objects.create(
            therapist=self.therapist,
            starts_at=datetime(2024, 3, 10, 1, 0, tzinfo=ZoneInfo("UTC")),
            ends_at=datetime(2024, 3, 10, 4, 0, tzinfo=ZoneInfo("UTC")),
            note="Initial",
        )
        detail_url = reverse("therapist_panel:api:time_off:time-off-detail", args=[record.uuid])
        payload = {
            "starts_at": "2024-03-10T10:00:00",
            "ends_at": "2024-03-10T13:00:00",
            "note": "Updated note",
        }

        response = self.client.patch(detail_url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        record.refresh_from_db()
        self.assertEqual(record.note, "Updated note")
        self.assertEqual(record.starts_at, datetime(2024, 3, 10, 2, 0, tzinfo=ZoneInfo("UTC")))
        self.assertEqual(record.ends_at, datetime(2024, 3, 10, 5, 0, tzinfo=ZoneInfo("UTC")))

    def test_delete_time_off_by_uuid(self):
        record = TherapistTimeOff.objects.create(
            therapist=self.therapist,
            starts_at=datetime(2024, 4, 1, 0, 0, tzinfo=ZoneInfo("UTC")),
            ends_at=datetime(2024, 4, 1, 3, 0, tzinfo=ZoneInfo("UTC")),
            note="Delete me",
        )
        detail_url = reverse("therapist_panel:api:time_off:time-off-detail", args=[record.uuid])

        response = self.client.delete(detail_url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(TherapistTimeOff.objects.filter(uuid=record.uuid).exists())

    def test_create_recurring_time_off_creates_series(self):
        payload = {
            "starts_at": "2024-03-01T09:00:00",
            "ends_at": "2024-03-01T11:00:00",
            "note": "Weekly break",
            "repeat_type": TherapistTimeOffSeries.REPEAT_WEEKLY,
            "repeat_interval": 1,
            "repeat_until": "2024-03-29",
        }

        response = self.client.post(self.time_off_url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["is_recurring"])
        self.assertIsNotNone(response.data["series_uuid"])

        series = TherapistTimeOffSeries.objects.get(uuid=response.data["series_uuid"])
        self.assertEqual(series.repeat_type, TherapistTimeOffSeries.REPEAT_WEEKLY)
        self.assertEqual(series.repeat_interval, 1)
        self.assertTrue(series.is_active)

        occurrence = TherapistTimeOff.objects.get(uuid=response.data["uuid"])
        self.assertEqual(occurrence.series_id, series.id)
        self.assertFalse(occurrence.is_skipped)

    def test_delete_single_occurrence_marks_skipped(self):
        payload = {
            "starts_at": "2024-03-01T09:00:00",
            "ends_at": "2024-03-01T11:00:00",
            "note": "Daily break",
            "repeat_type": TherapistTimeOffSeries.REPEAT_DAILY,
            "repeat_interval": 1,
            "repeat_until": "2024-03-05",
        }

        response = self.client.post(self.time_off_url, payload, format="json")
        occurrence_uuid = response.data["uuid"]

        detail_url = reverse("therapist_panel:api:time_off:time-off-detail", args=[occurrence_uuid])
        delete_response = self.client.delete(detail_url)

        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)
        occurrence = TherapistTimeOff.objects.get(uuid=occurrence_uuid)
        self.assertTrue(occurrence.is_skipped)

    def test_delete_series_deactivates_recurring_series(self):
        payload = {
            "starts_at": "2024-03-01T09:00:00",
            "ends_at": "2024-03-01T11:00:00",
            "note": "Daily break",
            "repeat_type": TherapistTimeOffSeries.REPEAT_DAILY,
            "repeat_interval": 1,
            "repeat_until": "2024-03-05",
        }

        response = self.client.post(self.time_off_url, payload, format="json")
        occurrence_uuid = response.data["uuid"]
        series_uuid = response.data["series_uuid"]

        detail_url = reverse("therapist_panel:api:time_off:time-off-detail", args=[occurrence_uuid])
        delete_response = self.client.delete(f"{detail_url}?scope=series")

        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)
        series = TherapistTimeOffSeries.objects.get(uuid=series_uuid)
        self.assertFalse(series.is_active)
        self.assertEqual(TherapistTimeOff.objects.filter(series=series).count(), 0)

    def test_list_materializes_future_occurrences(self):
        payload = {
            "starts_at": "2024-03-01T09:00:00",
            "ends_at": "2024-03-01T11:00:00",
            "note": "Daily break",
            "repeat_type": TherapistTimeOffSeries.REPEAT_DAILY,
            "repeat_interval": 1,
            "repeat_until": "2024-03-03",
        }

        response = self.client.post(self.time_off_url, payload, format="json")
        series_uuid = response.data["series_uuid"]

        series = TherapistTimeOffSeries.objects.get(uuid=series_uuid)
        self.assertEqual(TherapistTimeOff.objects.filter(series=series, is_skipped=False).count(), 1)

        list_response = self.client.get(
            self.time_off_url,
            {
                "start": "2024-03-01T00:00:00",
                "end": "2024-03-05T00:00:00",
            },
        )

        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(TherapistTimeOff.objects.filter(series=series, is_skipped=False).count(), 3)
