"""Registration flow for therapists using SMS verification."""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core import signing
from django.db import transaction
from django.utils import timezone
from rest_framework import permissions, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from phone_verification import exceptions
from phone_verification.payloads import (
    build_verification_error_payload,
    build_verification_success_payload,
)
from phone_verification.services import PhoneVerificationService
from therapist_panel.api.serializers.registration import (
    TherapistRegistrationCompleteSerializer,
    TherapistRegistrationSendCodeSerializer,
    TherapistRegistrationVerifySerializer,
    _registration_token_ttl_seconds,
)
from therapist_panel.models import Therapist

User = get_user_model()


def _generate_registration_token(phone_number: str) -> str:
    payload = {
        "phone_number": phone_number,
        "issued_at": timezone.now().isoformat(),
    }
    return signing.dumps(payload)


class TherapistRegistrationBaseView(APIView):
    """Shared helpers for registration endpoints."""

    permission_classes = [permissions.AllowAny]
    authentication_classes: list = []
    service_class = PhoneVerificationService

    def get_service(self) -> PhoneVerificationService:
        return self.service_class()


class TherapistRegistrationSendCodeView(TherapistRegistrationBaseView):
    """Send a verification code to start therapist registration."""

    def post(self, request, *args, **kwargs):
        serializer = TherapistRegistrationSendCodeSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        phone_number = serializer.validated_data["phone_number"]
        service = self.get_service()

        try:
            result = service.request_code(phone_number)
        except exceptions.VerificationAlreadyConfirmed:
            payload = service.get_status(phone_number)
            return Response(
                {
                    "success": True,
                    "message": "此手機已完成驗證，可直接登入。",
                    "verification": payload,
                    "user_exists": User.objects.filter(phone_number=phone_number).exists(),
                },
                status=status.HTTP_200_OK,
            )
        except exceptions.PhoneVerificationError as exc:
            payload = build_verification_error_payload(
                phone_number=phone_number,
                status=service.get_status(phone_number),
                error=exc,
                service=service,
            )
            return Response(
                {
                    "success": False,
                    "message": payload.get("message"),
                    "verification": payload,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        payload = build_verification_success_payload(result=result, service=service)
        return Response(
            {
                "success": True,
                "message": "驗證碼已寄出。",
                "verification": payload,
                "user_exists": User.objects.filter(phone_number=phone_number).exists(),
            },
            status=status.HTTP_200_OK,
        )


class TherapistRegistrationVerifyView(TherapistRegistrationBaseView):
    """Verify the SMS code and issue a short-lived registration token."""

    def post(self, request, *args, **kwargs):
        serializer = TherapistRegistrationVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone_number = serializer.validated_data["phone_number"]
        code = serializer.validated_data["code"]

        service = self.get_service()

        try:
            service.verify_code(phone_number, code)
        except exceptions.VerificationAlreadyConfirmed:
            # already verified, continue issuing token
            pass
        except exceptions.PhoneVerificationError as exc:
            error_messages = {
                "InvalidVerificationCode": "驗證碼錯誤，請再試一次。",
                "VerificationExpired": "驗證碼已過期，請重新取得。",
                "VerificationAttemptsExceeded": "嘗試次數過多，請稍後再試或聯絡客服。",
            }
            error_code = exc.__class__.__name__
            return Response(
                {
                    "success": False,
                    "message": error_messages.get(error_code, "手機驗證失敗，請重新嘗試。"),
                    "error_code": error_code,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        token = _generate_registration_token(phone_number)
        return Response(
            {
                "success": True,
                "message": "手機驗證成功，請繼續完成註冊。",
                "registration_token": token,
                "expires_in": _registration_token_ttl_seconds(),
            },
            status=status.HTTP_200_OK,
        )


class TherapistRegistrationCompleteView(APIView):
    """Finalize therapist account creation after successful phone verification."""

    permission_classes = [permissions.AllowAny]
    authentication_classes: list = []

    def post(self, request, *args, **kwargs):
        serializer = TherapistRegistrationCompleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        phone_number = data["phone_number"]
        password = data["password"]
        first_name = data.get("first_name", "").strip()
        last_name = data.get("last_name", "").strip()
        email = data.get("email", "").strip()
        nickname = data["nickname"]
        address = data["address"]
        timezone_value = data["timezone"]

        with transaction.atomic():
            defaults: dict[str, str] = {}
            if first_name:
                defaults["first_name"] = first_name
            if last_name:
                defaults["last_name"] = last_name
            if email:
                defaults["email"] = email

            user, created = User.objects.get_or_create(
                phone_number=phone_number,
                defaults=defaults,
            )

            if not created:
                if hasattr(user, "therapist_profile"):
                    raise serializers.ValidationError(
                        {"phone_token": "此手機已註冊為按摩師，請直接登入。"}
                    )
                if not user.check_password(password):
                    raise serializers.ValidationError(
                        {"password": "密碼不正確，請使用既有帳號登入後再新增按摩師角色。"}
                    )
                # Update basic info if provided.
                updates = []
                if first_name and first_name != user.first_name:
                    user.first_name = first_name
                    updates.append("first_name")
                if last_name and last_name != user.last_name:
                    user.last_name = last_name
                    updates.append("last_name")
                if email and email != user.email:
                    user.email = email
                    updates.append("email")
                if updates:
                    user.save(update_fields=updates)
            else:
                user.username = phone_number
                user.set_password(password)
                if email and user.email != email:
                    user.email = email
                if first_name and user.first_name != first_name:
                    user.first_name = first_name
                if last_name and user.last_name != last_name:
                    user.last_name = last_name
                user.save()

            therapist, therapist_created = Therapist.objects.get_or_create(
                user=user,
                defaults={
                    "nickname": nickname,
                    "address": address,
                    "timezone": timezone_value,
                },
            )

            if not therapist_created:
                raise serializers.ValidationError(
                    {"phone_token": "此帳號已具備按摩師資料，如需更新請登入後調整。"}
                )

            therapist.nickname = nickname
            therapist.address = address
            therapist.timezone = timezone_value
            therapist.save(update_fields=["nickname", "address", "timezone"])

        return Response(
            {
                "success": True,
                "message": "註冊完成，請使用手機號碼登入。",
                "therapist_uuid": str(therapist.uuid),
            },
            status=status.HTTP_201_CREATED,
        )
