"""Tests for questionnaire invitation SMS endpoint."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import Mock, patch
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from appointments.models import Appointment, AppointmentQuestionnaireLog
from questionnaires.models import Questionnaire
from scheduling.utils import to_utc
from therapist_panel.constants import DEFAULT_THERAPIST_TIMEZONE
from therapist_panel.models import Therapist, TherapistTreatment


class QuestionnaireSmsTests(APITestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="therapist",
            password="testpass123",
            email="therapist@example.com",
            first_name="Jane",
            last_name="Doe",
            phone_number="+886900000300",
        )
        self.therapist = Therapist.objects.create(
            user=self.user,
            nickname="JD",
            address="123 Main St",
            timezone=DEFAULT_THERAPIST_TIMEZONE,
        )
        self.treatment = TherapistTreatment.objects.create(
            therapist=self.therapist,
            name="Massage",
            duration_minutes=60,
            preparation_minutes=0,
            price="800.00",
        )
        tz = ZoneInfo(self.therapist.timezone)
        start_local = datetime(2024, 5, 1, 10, 0, tzinfo=tz)
        self.appointment = Appointment.objects.create(
            therapist=self.therapist,
            treatment=self.treatment,
            start_time=to_utc(start_local, self.therapist.timezone),
            customer_name="Client A",
            customer_phone="+886900000000",
        )
        self.client.force_login(self.user)
        self.url = reverse(
            "api:appointments:appointment-send-questionnaire",
            args=[self.appointment.uuid],
        )

    @patch("appointments.api.views.get_sms_provider")
    def test_send_questionnaire_success(self, mock_provider_factory):
        provider = Mock()
        mock_provider_factory.return_value = provider

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        provider.send.assert_called_once()
        log = AppointmentQuestionnaireLog.objects.get(appointment=self.appointment)
        self.assertEqual(log.status, AppointmentQuestionnaireLog.STATUS_SENT)
        self.assertIsNotNone(log.sent_at)

    @patch("appointments.api.views.get_sms_provider")
    def test_prevent_duplicate_send(self, mock_provider_factory):
        AppointmentQuestionnaireLog.objects.create(
            appointment=self.appointment,
            therapist=self.therapist,
            phone_number=self.appointment.customer_phone,
            message="test",
            status=AppointmentQuestionnaireLog.STATUS_SENT,
        )

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        mock_provider_factory.assert_not_called()

    @patch("appointments.api.views.get_sms_provider")
    def test_send_failure_is_logged(self, mock_provider_factory):
        provider = Mock()
        provider.send.side_effect = RuntimeError("sms failure")
        mock_provider_factory.return_value = provider

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)
        log = AppointmentQuestionnaireLog.objects.get(appointment=self.appointment)
        self.assertEqual(log.status, AppointmentQuestionnaireLog.STATUS_FAILED)
        self.assertIn("sms failure", log.error_message)

    @patch("appointments.api.views.get_sms_provider")
    def test_questionnaire_already_completed(self, mock_provider_factory):
        Questionnaire.objects.create(
            appointment=self.appointment,
            therapist=self.therapist,
            rating=5,
        )

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        mock_provider_factory.assert_not_called()
        self.assertFalse(
            AppointmentQuestionnaireLog.objects.filter(appointment=self.appointment).exists()
        )
