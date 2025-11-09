from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.core import signing

from rest_framework import status
from rest_framework.test import APITestCase

from accounts.constants import ROLE_THERAPIST, SESSION_ACTIVE_ROLE_KEY
from appointments.models import Appointment, AppointmentQuestionnaireLog
from phone_verification.models import PhoneVerification
from scheduling.models import TherapistTimeOff, TherapistWorkingHours
from scheduling.utils import to_utc
from therapist_panel.constants import DEFAULT_THERAPIST_TIMEZONE
from therapist_panel.models import Therapist, TherapistTreatment


class TherapistOnboardingFlowTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="therapist",
            password="strongpass123",
            email="therapist@example.com",
            first_name="Terry",
            last_name="Therapist",
            phone_number="+886900000001",
        )
        self.index_url = reverse("therapist_panel:index")
        self.onboarding_url = reverse("therapist_panel:onboarding")
        self.therapist = Therapist.objects.create(
            user=self.user,
            nickname="TT",
            address="Taipei City",
            timezone=DEFAULT_THERAPIST_TIMEZONE,
        )
        self.tzinfo = ZoneInfo(self.therapist.timezone)

    def _login_as_therapist(self):
        logged_in = self.client.login(username="therapist", password="strongpass123")
        self.assertTrue(logged_in, "Failed to log in therapist user for onboarding tests.")
        session = self.client.session
        session[SESSION_ACTIVE_ROLE_KEY] = ROLE_THERAPIST
        session.save()

    def test_redirects_to_onboarding_when_missing_setup(self):
        self._login_as_therapist()

        response = self.client.get(self.index_url)

        self.assertRedirects(
            response,
            self.onboarding_url,
            status_code=302,
            target_status_code=200,
        )

    def test_onboarding_redirects_to_index_when_requirements_completed(self):
        self._login_as_therapist()
        TherapistTreatment.objects.create(
            therapist=self.therapist,
            name="Deep Tissue",
            duration_minutes=60,
            preparation_minutes=10,
            price="1500.00",
        )
        working_start = datetime(2024, 7, 1, 9, 0, tzinfo=self.tzinfo)
        TherapistWorkingHours.objects.create(
            therapist=self.therapist,
            starts_at=to_utc(working_start, self.therapist.timezone),
            ends_at=to_utc(working_start + timedelta(hours=2), self.therapist.timezone),
            note="Morning shift",
        )
        break_start = datetime(2024, 7, 1, 13, 0, tzinfo=self.tzinfo)
        TherapistTimeOff.objects.create(
            therapist=self.therapist,
            starts_at=to_utc(break_start, self.therapist.timezone),
            ends_at=to_utc(break_start + timedelta(hours=1), self.therapist.timezone),
            note="Lunch break",
        )

        response = self.client.get(self.onboarding_url)

        self.assertRedirects(
            response,
            self.index_url,
            status_code=302,
            target_status_code=200,
        )

    def test_onboarding_context_includes_api_endpoints(self):
        self._login_as_therapist()

        response = self.client.get(self.onboarding_url)

        self.assertEqual(response.status_code, 200)
        self.assertIn("treatments_api_url", response.context)
        self.assertIn("working_hours_api_url", response.context)
        self.assertIn("time_off_api_url", response.context)
        self.assertIn("appointments_booking_path", response.context)
        self.assertEqual(response.context["therapist_timezone"], DEFAULT_THERAPIST_TIMEZONE)


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
            phone_number="+886900000002",
        )
        self.other_user = User.objects.create_user(
            username="viewer",
            password="viewerpass123",
            email="viewer@example.com",
            phone_number="+886900000010",
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
            preparation_minutes=0,
            price="1500.00",
        )
        self.tz_name = self.therapist.timezone
        self.tzinfo = ZoneInfo(self.tz_name)
        self._create_onboarding_requirements()
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

    def _create_onboarding_requirements(self):
        working_start = datetime(2024, 4, 1, 9, 0, tzinfo=self.tzinfo)
        TherapistWorkingHours.objects.create(
            therapist=self.therapist,
            starts_at=to_utc(working_start, self.tz_name),
            ends_at=to_utc(working_start + timedelta(hours=4), self.tz_name),
            note="Initial shift",
        )
        time_off_start = datetime(2024, 4, 2, 12, 0, tzinfo=self.tzinfo)
        TherapistTimeOff.objects.create(
            therapist=self.therapist,
            starts_at=to_utc(time_off_start, self.tz_name),
            ends_at=to_utc(time_off_start + timedelta(hours=1), self.tz_name),
            note="Break",
        )

    def _login_as_therapist(self):
        logged_in = self.client.login(username="therapist", password="testpass123")
        self.assertTrue(logged_in, "Failed to log in therapist user for tests.")
        session = self.client.session
        session[SESSION_ACTIVE_ROLE_KEY] = ROLE_THERAPIST
        session.save()

    def test_login_required(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)

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

    def test_questionnaire_button_disabled_after_successful_send(self):
        self._login_as_therapist()
        AppointmentQuestionnaireLog.objects.create(
            appointment=self.mid_appointment,
            therapist=self.therapist,
            phone_number=self.mid_appointment.customer_phone,
            message="link",
            status=AppointmentQuestionnaireLog.STATUS_SENT,
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        appointments = list(response.context["appointments"])
        target = next(a for a in appointments if a.pk == self.mid_appointment.pk)
        self.assertTrue(target.questionnaire_sent)
        self.assertContains(response, f'data-appointment-id="{self.mid_appointment.uuid}" disabled')

    def test_template_includes_api_base_for_cancellation(self):
        self._login_as_therapist()

        response = self.client.get(self.url)

        self.assertIn("appointments_api_url", response.context)
        self.assertEqual(response.context["appointments_api_url"], self.api_base)
        self.assertContains(response, f'data-appointment-id="{self.mid_appointment.uuid}"')
        self.assertContains(response, self.api_base)


class TherapistRegistrationAPITests(APITestCase):
    def setUp(self):
        self.send_url = reverse("therapist_panel:api:registration:send_code")
        self.verify_url = reverse("therapist_panel:api:registration:verify_code")
        self.complete_url = reverse("therapist_panel:api:registration:complete")
        self.phone = "+886900000900"
        self.code = "1234"

    def _create_verification(self, *, phone: str | None = None, code: str | None = None, verified: bool = False):
        return PhoneVerification.objects.create(
            phone_number=phone or self.phone,
            code_hash=make_password(code or self.code),
            expires_at=timezone.now() + timedelta(minutes=5),
            send_count=1,
            attempt_count=0,
            is_verified=verified,
        )

    def test_send_code_starts_verification(self):
        phone = "+886900001000"

        response = self.client.post(
            self.send_url,
            {"phone_number": phone},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertTrue(PhoneVerification.objects.filter(phone_number=phone).exists())

    def test_send_code_rejects_existing_therapist_phone(self):
        User = get_user_model()
        user = User.objects.create_user(
            username="existingtherapist",
            password="TherapistPass123!",
            phone_number=self.phone,
            email="therapist@example.com",
            first_name="Existing",
            last_name="Therapist",
        )
        Therapist.objects.create(
            user=user,
            nickname="ExistingPro",
            address="123 Massage Road",
            timezone=DEFAULT_THERAPIST_TIMEZONE,
        )

        response = self.client.post(
            self.send_url,
            {"phone_number": self.phone},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("phone_number", response.data)
        self.assertIn("http://testserver/accounts/password-reset/", response.data["phone_number"][0])

    def test_verify_code_returns_token(self):
        self._create_verification()

        response = self.client.post(
            self.verify_url,
            {"phone_number": self.phone, "code": self.code},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertIn("registration_token", response.data)
        self.assertGreater(response.data["expires_in"], 0)

    def test_complete_creates_new_user_and_therapist(self):
        self._create_verification()

        verify_response = self.client.post(
            self.verify_url,
            {"phone_number": self.phone, "code": self.code},
            format="json",
        )
        token = verify_response.data["registration_token"]

        payload = {
            "phone_token": token,
            "password": "StrongPass123!",
            "nickname": "NewTherapist",
            "address": "123 Massage Road",
            "timezone": DEFAULT_THERAPIST_TIMEZONE,
        }

        response = self.client.post(self.complete_url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["success"])
        user = get_user_model().objects.get(phone_number=self.phone)
        self.assertTrue(user.check_password(payload["password"]))
        self.assertEqual(user.first_name, "")
        self.assertEqual(user.last_name, "")
        self.assertEqual(user.email, "")
        self.assertTrue(hasattr(user, "therapist_profile"))
        self.assertEqual(user.therapist_profile.nickname, payload["nickname"])

    def test_complete_requires_existing_password(self):
        User = get_user_model()
        user = User.objects.create_user(
            username="clientuser",
            password="ClientPass123!",
            phone_number=self.phone,
            email="client@example.com",
            first_name="Client",
            last_name="User",
        )
        self._create_verification(verified=True)
        token = signing.dumps(
            {"phone_number": self.phone, "issued_at": timezone.now().isoformat()}
        )

        payload = {
            "phone_token": token,
            "password": "WrongPassword!!!",
            "first_name": "Client",
            "last_name": "User",
            "nickname": "MassagePro",
            "address": "456 Massage Lane",
            "timezone": DEFAULT_THERAPIST_TIMEZONE,
            "email": "client@example.com",
        }

        response = self.client.post(self.complete_url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", response.data)
        self.assertFalse(hasattr(user, "therapist_profile"))

    def test_complete_rejects_existing_therapist(self):
        User = get_user_model()
        user = User.objects.create_user(
            username="existingtherapist",
            password="TherapistPass123!",
            phone_number=self.phone,
            email="therapist@example.com",
            first_name="Existing",
            last_name="Therapist",
        )
        Therapist.objects.create(
            user=user,
            nickname="ExistingPro",
            address="789 Spa Street",
            timezone=DEFAULT_THERAPIST_TIMEZONE,
        )
        self._create_verification(verified=True)
        token = signing.dumps(
            {"phone_number": self.phone, "issued_at": timezone.now().isoformat()}
        )

        payload = {
            "phone_token": token,
            "password": "TherapistPass123!",
            "first_name": "Existing",
            "last_name": "Therapist",
            "nickname": "ExistingPro",
            "address": "789 Spa Street",
            "timezone": DEFAULT_THERAPIST_TIMEZONE,
            "email": "therapist@example.com",
        }

        response = self.client.post(self.complete_url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("phone_token", response.data)
