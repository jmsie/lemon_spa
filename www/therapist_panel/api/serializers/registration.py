"""Serializers handling therapist registration workflow."""

from __future__ import annotations

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import signing
from django.utils import timezone
from rest_framework import serializers

from phone_verification.models import PhoneVerification
from phone_verification.utils import normalize_phone_number
from therapist_panel.constants import THERAPIST_TIMEZONE_CHOICES

User = get_user_model()


def _registration_token_ttl_seconds() -> int:
    config = getattr(settings, "THERAPIST_REGISTRATION", {})
    return int(config.get("TOKEN_TTL_SECONDS", 10 * 60))


class TherapistRegistrationSendCodeSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=32)

    def validate_phone_number(self, value: str) -> str:
        return normalize_phone_number(value)


class TherapistRegistrationVerifySerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=32)
    code = serializers.CharField(max_length=8)

    def validate_phone_number(self, value: str) -> str:
        return normalize_phone_number(value)


class TherapistRegistrationCompleteSerializer(serializers.Serializer):
    phone_token = serializers.CharField()
    password = serializers.CharField(write_only=True, min_length=8, max_length=128)
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    nickname = serializers.CharField(max_length=150)
    address = serializers.CharField(max_length=255)
    timezone = serializers.ChoiceField(choices=THERAPIST_TIMEZONE_CHOICES)
    email = serializers.EmailField(required=False, allow_blank=True)

    phone_number: str | None = None

    def validate_phone_token(self, value: str) -> str:
        try:
            payload = signing.loads(value, max_age=_registration_token_ttl_seconds())
        except signing.BadSignature as exc:
            raise serializers.ValidationError("Token 已過期或無效，請重新驗證手機。") from exc

        phone = payload.get("phone_number")
        if not phone:
            raise serializers.ValidationError("Token 缺少手機資訊，請重新驗證。")

        self.phone_number = phone
        return value

    def validate(self, attrs):
        phone = self.phone_number
        if not phone:
            raise serializers.ValidationError("Token 無效，請重新驗證手機。")

        try:
            verification = PhoneVerification.objects.get(phone_number=phone)
        except PhoneVerification.DoesNotExist as exc:
            raise serializers.ValidationError({"phone_token": "尚未取得驗證碼，請先驗證手機。"}) from exc

        if not verification.is_verified:
            raise serializers.ValidationError({"phone_token": "手機尚未完成驗證。"})

        attrs["phone_number"] = phone
        return attrs

    def create(self, validated_data):
        raise NotImplementedError("Creation handled in the view.")
