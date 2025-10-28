"""API views for phone-based password reset."""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from phone_verification import exceptions as verification_exceptions
from phone_verification.models import PhoneVerification
from phone_verification.payloads import build_verification_success_payload
from phone_verification.services import PhoneVerificationService

from .serializers import PasswordResetConfirmSerializer, PasswordResetSendCodeSerializer

User = get_user_model()


class PasswordResetBaseView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes: list = []
    service_class = PhoneVerificationService

    def get_service(self) -> PhoneVerificationService:
        return self.service_class()


class PasswordResetSendCodeView(PasswordResetBaseView):
    """Send an OTP to initiate password reset."""

    def post(self, request, *args, **kwargs):
        serializer = PasswordResetSendCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone_number = serializer.validated_data["phone_number"]
        user_exists = User.objects.filter(phone_number=phone_number).exists()

        # Never reveal whether the account exists.
        if not user_exists:
            return Response(
                {
                    "success": True,
                    "message": _("若手機號碼已註冊，我們已發送一組驗證碼。"),
                },
                status=status.HTTP_200_OK,
            )

        service = self.get_service()
        try:
            result = service.request_code(phone_number)
        except verification_exceptions.VerificationAlreadyConfirmed:
            # Reset verification status and retry.
            PhoneVerification.objects.filter(phone_number=phone_number).update(
                is_verified=False,
                verified_at=None,
            )
            result = service.request_code(phone_number)
        except verification_exceptions.PhoneVerificationError as exc:
            return Response(
                {
                    "success": False,
                    "message": str(exc),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        payload = build_verification_success_payload(result=result, service=service)
        return Response(
            {
                "success": True,
                "message": _("驗證碼已寄出。"),
                "verification": payload,
            },
            status=status.HTTP_200_OK,
        )


class PasswordResetConfirmView(PasswordResetBaseView):
    """Verify the OTP and update the user's password."""

    def post(self, request, *args, **kwargs):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone_number = serializer.validated_data["phone_number"]
        code = serializer.validated_data["code"]
        new_password = serializer.validated_data["new_password"]

        user = User.objects.filter(phone_number=phone_number).first()
        if user is None:
            # Obfuscate account existence.
            return Response(
                {
                    "success": False,
                    "message": _("驗證碼無效或已過期，請重新申請。"),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        service = self.get_service()
        try:
            service.verify_code(phone_number, code)
        except verification_exceptions.VerificationAlreadyConfirmed:
            # Treat as success, proceed to password update.
            pass
        except verification_exceptions.PhoneVerificationError as exc:
            return Response(
                {
                    "success": False,
                    "message": _("驗證碼錯誤或已失效，請重新申請。"),
                    "error_code": exc.__class__.__name__,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            user.set_password(new_password)
            user.save(update_fields=["password"])

            PhoneVerification.objects.filter(phone_number=phone_number).update(
                is_verified=False,
                verified_at=None,
            )

        return Response(
            {
                "success": True,
                "message": _("密碼已更新，請使用新密碼登入。"),
            },
            status=status.HTTP_200_OK,
        )
