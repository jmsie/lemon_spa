"""App configuration for phone verification."""

from django.apps import AppConfig


class PhoneVerificationConfig(AppConfig):
    """Configure the phone_verification Django app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "phone_verification"
    verbose_name = "Phone Verification"

