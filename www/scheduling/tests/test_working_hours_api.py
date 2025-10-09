"""Integration tests for therapist working hours API."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from scheduling.models import TherapistWorkingHours, TherapistWorkingHoursSeries
from therapist_panel.constants import DEFAULT_THERAPIST_TIMEZONE
from therapist_panel.models import Therapist


class TherapistWorkingHoursAPITests(APITestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="therapist", password="pass1234", email="therapist@example.com")
        self.therapist = Therapist.objects.create(
            user=self.user,
            last_name="Doe",
            first_name="Jane",
            nickname="JD",
            phone_number="123456789",
            address="123 Main St",
            timezone=DEFAULT_THERAPIST_TIMEZONE,
        )
        self.client.force_authenticate(user=self.user)
        self.working_hours_url = reverse("therapist_panel:api:working_hours:working-hours-list")

    def test_create_working_hours_converts_times_to_utc(self):
        payload = {
            "starts_at": "2024-03-04T10:00:00",
            "ends_at": "2024-03-04T18:00:00",
            "note": "Regular shift",
        }

        response = self.client.post(self.working_hours_url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        record = TherapistWorkingHours.objects.get(uuid=response.data["uuid"])
        self.assertEqual(
            record.starts_at,
            datetime(2024, 3, 4, 2, 0, tzinfo=ZoneInfo("UTC")),
        )
        self.assertEqual(
            record.ends_at,
            datetime(2024, 3, 4, 10, 0, tzinfo=ZoneInfo("UTC")),
        )
        self.assertEqual(response.data["weekday"], 0)
        self.assertFalse(response.data["is_recurring"])

    def test_create_recurring_working_hours_creates_series(self):
        payload = {
            "starts_at": "2024-03-05T12:00:00",
            "ends_at": "2024-03-05T20:00:00",
            "weekday": 1,
            "repeat_interval": 1,
            "repeat_until": "2024-03-26",
            "note": "Weekly afternoon shift",
        }

        response = self.client.post(self.working_hours_url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["is_recurring"])
        self.assertIsNotNone(response.data["series_uuid"])

        series = TherapistWorkingHoursSeries.objects.get(uuid=response.data["series_uuid"])
        self.assertEqual(series.weekday, 1)
        self.assertEqual(series.repeat_interval, 1)
        self.assertTrue(series.is_active)

        occurrence = TherapistWorkingHours.objects.get(uuid=response.data["uuid"])
        self.assertEqual(occurrence.series_id, series.id)
        self.assertFalse(occurrence.is_generated)

    def test_list_materializes_future_occurrences(self):
        payload = {
            "starts_at": "2024-03-06T10:00:00",
            "ends_at": "2024-03-06T16:00:00",
            "weekday": 2,
            "repeat_interval": 1,
            "repeat_until": "2024-03-20",
        }

        create_response = self.client.post(self.working_hours_url, payload, format="json")
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        series = TherapistWorkingHoursSeries.objects.get(uuid=create_response.data["series_uuid"])
        self.assertEqual(TherapistWorkingHours.objects.filter(series=series).count(), 1)

        list_response = self.client.get(
            self.working_hours_url,
            {
                "start": "2024-03-04T00:00:00",
                "end": "2024-03-27T00:00:00",
            },
        )

        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(TherapistWorkingHours.objects.filter(series=series).count(), 3)

    def test_delete_single_occurrence_from_series_is_forbidden(self):
        payload = {
            "starts_at": "2024-03-07T10:00:00",
            "ends_at": "2024-03-07T18:00:00",
            "weekday": 3,
            "repeat_interval": 1,
            "repeat_until": "2024-03-21",
        }

        response = self.client.post(self.working_hours_url, payload, format="json")
        occurrence_uuid = response.data["uuid"]
        detail_url = reverse("therapist_panel:api:working_hours:working-hours-detail", args=[occurrence_uuid])

        delete_response = self.client.delete(detail_url)

        self.assertEqual(delete_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Create a time off entry instead", str(delete_response.data))

    def test_delete_series_deactivates_recurring_series(self):
        payload = {
            "starts_at": "2024-03-08T09:00:00",
            "ends_at": "2024-03-08T17:00:00",
            "weekday": 4,
            "repeat_interval": 1,
            "repeat_until": "2024-03-29",
        }

        response = self.client.post(self.working_hours_url, payload, format="json")
        occurrence_uuid = response.data["uuid"]
        series_uuid = response.data["series_uuid"]
        detail_url = reverse("therapist_panel:api:working_hours:working-hours-detail", args=[occurrence_uuid])

        delete_response = self.client.delete(f"{detail_url}?scope=series")

        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)
        series = TherapistWorkingHoursSeries.objects.get(uuid=series_uuid)
        self.assertFalse(series.is_active)
        self.assertEqual(TherapistWorkingHours.objects.filter(series=series).count(), 0)
