"""API views for phone verification."""

from __future__ import annotations

import logging

from django.shortcuts import get_object_or_404
from rest_framework import permissions, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from appointments.models import Appointment
from appointments.utils import serialize_public_appointment
from phone_verification import exceptions
from phone_verification.payloads import (
    build_verification_error_payload,
    build_verification_success_payload,
)
from phone_verification.services import PhoneVerificationService

from .serializers import ResendCodeSerializer, VerifyCodeSerializer

logger = logging.getLogger(__name__)


class PhoneVerificationBaseView(APIView):
    """Shared helpers for verification endpoints."""

    permission_classes = [permissions.AllowAny]
    authentication_classes: list = []
    service_class = PhoneVerificationService

    def get_service(self) -> PhoneVerificationService:
        return self.service_class()

    def _exception_status(self, exc: Exception) -> int:
        if isinstance(exc, (exceptions.SendRateLimited, exceptions.SendLimitReached)):
            return status.HTTP_429_TOO_MANY_REQUESTS
        return status.HTTP_400_BAD_REQUEST


class ResendVerificationCodeView(PhoneVerificationBaseView):
    """Trigger a verification code resend."""

    def post(self, request, *args, **kwargs):
        serializer = ResendCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone_number = serializer.validated_data["phone_number"]
        appointment_uuid = serializer.validated_data.get("appointment_uuid")

        if appointment_uuid:
            if not Appointment.objects.filter(
                uuid=appointment_uuid,
                customer_phone=phone_number,
            ).exists():
                raise serializers.ValidationError(
                    {"appointment_uuid": "找不到對應的預約資料或電話不符。"}
                )

        service = self.get_service()

        try:
            result = service.request_code(phone_number)
        except exceptions.VerificationAlreadyConfirmed:
            payload = {
                "status": "verified",
                "phone_number": phone_number,
                "message": "手機已完成驗證。",
            }
            response = {
                "success": True,
                "message": payload["message"],
                "verification": payload,
            }
            if appointment_uuid:
                appointment = Appointment.objects.filter(
                    uuid=appointment_uuid,
                    customer_phone=phone_number,
                ).select_related("therapist", "treatment").first()
                if appointment:
                    response["appointment"] = serialize_public_appointment(appointment)
            return Response(response, status=status.HTTP_200_OK)
        except exceptions.PhoneVerificationError as exc:
            logger.warning("Failed to resend verification code to %s: %s", phone_number, exc)
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
                status=self._exception_status(exc),
            )

        payload = build_verification_success_payload(result=result, service=service)
        return Response(
            {
                "success": True,
                "message": "驗證碼已寄出。",
                "verification": payload,
            },
            status=status.HTTP_200_OK,
        )


class VerifyCodeView(PhoneVerificationBaseView):
    """Validate a verification code and return appointment details."""

    def post(self, request, *args, **kwargs):
        serializer = VerifyCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone_number = serializer.validated_data["phone_number"]
        appointment_uuid = serializer.validated_data["appointment_uuid"]
        code = serializer.validated_data["code"]

        appointment = get_object_or_404(
            Appointment.objects.select_related("therapist", "treatment"),
            uuid=appointment_uuid,
            customer_phone=phone_number,
        )

        service = self.get_service()

        try:
            service.verify_code(phone_number, code)
        except exceptions.VerificationAlreadyConfirmed:
            logger.info("Phone %s already verified when submitting code.", phone_number)
        except exceptions.PhoneVerificationError as exc:
            logger.warning("Phone verification failed for %s: %s", phone_number, exc)
            error_messages = {
                "InvalidVerificationCode": "驗證碼錯誤，請再試一次。",
                "VerificationExpired": "驗證碼已過期，請點擊重新寄送驗證碼。",
                "VerificationAttemptsExceeded": "驗證次數過多，請聯絡客服人員協助。",
            }
            error_code = exc.__class__.__name__
            return Response(
                {
                    "success": False,
                    "message": error_messages.get(error_code, "手機驗證失敗，請尋求客服協助。"),
                    "error_code": error_code,
                    "context": getattr(exc, "context", {}),
                },
                status=self._exception_status(exc),
            )

        return Response(
            {
                "success": True,
                "message": "手機驗證成功，預約已確認。",
                "appointment": serialize_public_appointment(appointment),
            },
            status=status.HTTP_200_OK,
        )
