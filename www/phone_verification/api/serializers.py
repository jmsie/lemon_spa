"""Serializers for phone verification API endpoints."""

from __future__ import annotations

from rest_framework import serializers

from phone_verification.exceptions import InvalidPhoneNumber
from phone_verification.utils import normalize_phone_number


class PhoneNumberSerializer(serializers.Serializer):
    """Base serializer that normalizes a phone number."""

    phone_number = serializers.CharField()

    def validate_phone_number(self, value: str) -> str:
        try:
            return normalize_phone_number(value)
        except InvalidPhoneNumber as exc:
            raise serializers.ValidationError("請輸入有效的國際電話號碼。") from exc


class ResendCodeSerializer(PhoneNumberSerializer):
    """Serializer for requesting a new verification code."""

    appointment_uuid = serializers.UUIDField(required=False)


class VerifyCodeSerializer(PhoneNumberSerializer):
    """Serializer for verifying a submitted code."""

    appointment_uuid = serializers.UUIDField()
    code = serializers.CharField(min_length=4, max_length=4)

    def validate_code(self, value: str) -> str:
        if not value.isdigit():
            raise serializers.ValidationError("驗證碼需為 4 位數字。")
        return value
