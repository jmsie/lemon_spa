"""SMS provider factory for phone verification."""

from __future__ import annotations

from importlib import import_module

from django.conf import settings

from phone_verification.sms.base import SmsProvider


def get_sms_provider() -> SmsProvider:
    """Instantiate the configured SMS provider."""

    path = getattr(settings, "PHONE_VERIFICATION_SMS_BACKEND", "phone_verification.sms.dummy.DummySmsProvider")
    module_path, _, class_name = path.rpartition(".")
    module = import_module(module_path)
    backend_class = getattr(module, class_name)
    return backend_class()


__all__ = ["get_sms_provider", "SmsProvider"]

