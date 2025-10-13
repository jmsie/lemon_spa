"""Tests for the phone verification service."""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone as dt_timezone
from unittest.mock import patch

from django.test import TestCase

from phone_verification import exceptions
from phone_verification.models import PhoneVerification, PhoneVerificationAuditLog
from phone_verification.services import PhoneVerificationService


class MemorySmsProvider:
    """Collect SMS payloads for assertions."""

    def __init__(self):
        self.sent_messages: list[dict[str, str]] = []

    def send(self, *, phone_number: str, message: str) -> None:
        self.sent_messages.append({"phone_number": phone_number, "message": message})


class PhoneVerificationServiceTests(TestCase):
    """Verify key behaviours of the verification service."""

    def setUp(self):
        self.provider = MemorySmsProvider()
        self.service = PhoneVerificationService(sms_provider=self.provider)
        self.base_time = datetime(2024, 1, 1, 10, 0, tzinfo=dt_timezone.utc)
        self.phone_number = "+886987654321"

    def test_request_code_creates_record_and_sends_sms(self):
        result = self._request_code(self.base_time)

        self.assertTrue(result.sent)
        self.assertEqual(PhoneVerification.objects.count(), 1)
        verification = PhoneVerification.objects.first()
        assert verification is not None
        self.assertEqual(verification.phone_number, self.phone_number)
        self.assertEqual(len(self.provider.sent_messages), 1)
        self.assertEqual(self.provider.sent_messages[0]["phone_number"], self.phone_number)
        self.assertEqual(
            PhoneVerificationAuditLog.objects.filter(event_type=PhoneVerificationAuditLog.EVENT_SEND).count(),
            1,
        )

    def test_request_code_rate_limited_within_one_minute(self):
        self._request_code(self.base_time)
        with self.assertRaises(exceptions.SendRateLimited):
            self._request_code(self.base_time + timedelta(seconds=30))

    def test_request_code_enforces_max_send_count(self):
        # First send
        self._request_code(self.base_time)
        # Second send after interval
        self._request_code(self.base_time + timedelta(minutes=2))
        # Third send after interval
        self._request_code(self.base_time + timedelta(minutes=4))
        with self.assertRaises(exceptions.SendLimitReached):
            self._request_code(self.base_time + timedelta(minutes=6))

    def test_verify_code_success(self):
        result = self._request_code(self.base_time)
        code = self._extract_code_from_latest_sms()

        with patch("phone_verification.services.verification.timezone.now", return_value=self.base_time + timedelta(minutes=1)):
            verify_result = self.service.verify_code(self.phone_number, code)

        self.assertTrue(verify_result.verified)
        verification = PhoneVerification.objects.get(phone_number=self.phone_number)
        self.assertTrue(verification.is_verified)
        self.assertEqual(
            PhoneVerificationAuditLog.objects.filter(event_type=PhoneVerificationAuditLog.EVENT_CODE_VERIFIED).count(),
            1,
        )

    def test_verify_code_invalid_increments_attempts(self):
        self._request_code(self.base_time)
        wrong_code = "0000"

        with patch("phone_verification.services.verification.timezone.now", return_value=self.base_time + timedelta(minutes=1)):
            with self.assertRaises(exceptions.InvalidVerificationCode):
                self.service.verify_code(self.phone_number, wrong_code)

        verification = PhoneVerification.objects.get(phone_number=self.phone_number)
        self.assertEqual(verification.attempt_count, 1)
        self.assertEqual(
            PhoneVerificationAuditLog.objects.filter(event_type=PhoneVerificationAuditLog.EVENT_CODE_INVALID).count(),
            1,
        )

        # Exhaust remaining attempts to trigger the limit.
        with patch("phone_verification.services.verification.timezone.now", return_value=self.base_time + timedelta(minutes=1, seconds=10)):
            with self.assertRaises(exceptions.InvalidVerificationCode):
                self.service.verify_code(self.phone_number, wrong_code)

        with patch("phone_verification.services.verification.timezone.now", return_value=self.base_time + timedelta(minutes=1, seconds=20)):
            with self.assertRaises(exceptions.VerificationAttemptsExceeded):
                self.service.verify_code(self.phone_number, wrong_code)

        verification.refresh_from_db()
        self.assertEqual(verification.attempt_count, self.service.max_attempts)
        self.assertEqual(
            PhoneVerificationAuditLog.objects.filter(event_type=PhoneVerificationAuditLog.EVENT_ATTEMPTS_EXCEEDED).count(),
            1,
        )

    def _request_code(self, current_time: datetime):
        with patch("phone_verification.services.verification.timezone.now", return_value=current_time), patch(
            "phone_verification.services.verification.transaction.on_commit"
        ) as on_commit:
            on_commit.side_effect = lambda func: func()
            return self.service.request_code(self.phone_number)

    def _extract_code_from_latest_sms(self) -> str:
        self.assertTrue(self.provider.sent_messages, "Expected at least one SMS to be sent.")
        message = self.provider.sent_messages[-1]["message"]
        match = re.search(r"\b(\d{4})\b", message)
        self.assertIsNotNone(match, "Verification SMS did not contain a 4-digit code.")
        return match.group(1)

