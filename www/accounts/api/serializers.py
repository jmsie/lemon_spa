"""Serializers supporting phone-based password reset."""

from __future__ import annotations

from django.contrib.auth import get_user_model, password_validation
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from phone_verification.exceptions import InvalidPhoneNumber
from phone_verification.utils import normalize_phone_number

User = get_user_model()


class PasswordResetSendCodeSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=32)

    def validate_phone_number(self, value: str) -> str:
        try:
            return normalize_phone_number(value)
        except InvalidPhoneNumber as exc:
            raise serializers.ValidationError(_("請輸入正確的手機號碼。")) from exc


class PasswordResetConfirmSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=32)
    code = serializers.CharField(max_length=8)
    new_password = serializers.CharField(max_length=128, write_only=True)
    confirm_password = serializers.CharField(max_length=128, write_only=True)

    def validate_phone_number(self, value: str) -> str:
        try:
            return normalize_phone_number(value)
        except InvalidPhoneNumber as exc:
            raise serializers.ValidationError(_("請輸入正確的手機號碼。")) from exc

    def validate(self, attrs):
        password = attrs.get("new_password")
        confirm = attrs.get("confirm_password")
        if password != confirm:
            raise serializers.ValidationError({"confirm_password": _("兩次輸入的密碼不一致。")})

        # Run Django's password validators. If user exists, pass it for contextual checks.
        user = User.objects.filter(phone_number=attrs["phone_number"]).first()
        try:
            password_validation.validate_password(password, user=user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"new_password": list(exc.messages)})
        attrs.pop("confirm_password", None)
        return attrs
