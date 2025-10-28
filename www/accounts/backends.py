"""Authentication backends for accounts."""

from __future__ import annotations

from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

from phone_verification.exceptions import InvalidPhoneNumber
from phone_verification.utils import normalize_phone_number


class PhoneNumberBackend(ModelBackend):
    """Authenticate users by their normalized phone number."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        phone_number = kwargs.get("phone_number") or username
        if phone_number is None or password is None:
            return None

        UserModel = get_user_model()

        normalized = None
        try:
            normalized = normalize_phone_number(phone_number)
        except InvalidPhoneNumber:
            # Allow fallback to raw input if normalization fails.
            normalized = phone_number

        try:
            user = UserModel.objects.get(phone_number=normalized)
        except UserModel.DoesNotExist:
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
