"""Tests for the Twilio SMS provider."""

from __future__ import annotations

from unittest.mock import patch

from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase, override_settings

from phone_verification.sms.twilio import TwilioSmsProvider


class TwilioSmsProviderTests(SimpleTestCase):
    """Verify Twilio provider configuration and send behaviour."""

    @override_settings(
        PHONE_VERIFICATION_TWILIO={
            "ACCOUNT_SID": "AC123",
            "AUTH_TOKEN": "secret",
            "FROM_NUMBER": "+15005550006",
        }
    )
    def test_send_invokes_twilio_client(self):
        with self.assertLogs("phone_verification.sms.twilio", level="DEBUG"), patch(
            "phone_verification.sms.twilio.Client"
        ) as mock_client:
            provider = TwilioSmsProvider()
            provider.send(phone_number="+886987654321", message="Hello")

        mock_client.assert_called_once_with("AC123", "secret")
        mock_client.return_value.messages.create.assert_called_once_with(
            body="Hello",
            from_="+15005550006",
            to="+886987654321",
        )

    @override_settings(
        PHONE_VERIFICATION_TWILIO={
            "ACCOUNT_SID": None,
            "AUTH_TOKEN": "secret",
            "FROM_NUMBER": "+15005550006",
        }
    )
    def test_missing_config_raises(self):
        with self.assertRaises(ImproperlyConfigured):
            TwilioSmsProvider()
