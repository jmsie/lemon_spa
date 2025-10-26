"""Viewsets and endpoints for appointment resources."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from appointments.models import Appointment, AppointmentQuestionnaireLog
from phone_verification.sms import get_sms_provider
from appointments.api.serializers import AppointmentSerializer
from scheduling.models import TherapistTimeOff, TherapistWorkingHours
from scheduling.services import ensure_series_occurrences, ensure_working_hours_occurrences
from scheduling.utils import ensure_timezone, to_local, to_utc
from therapist_panel.models import Therapist
from questionnaires.models import Questionnaire


class AppointmentViewSet(viewsets.ModelViewSet):
    """CRUD operations for appointments."""

    queryset = Appointment.objects.select_related("therapist", "treatment").all()
    serializer_class = AppointmentSerializer
    lookup_field = "uuid"

    def _parse_datetime(self, value: str | None):
        if not value:
            return None
        parsed = parse_datetime(value)
        if parsed is None:
            return None
        if timezone.is_naive(parsed):
            return timezone.make_aware(parsed, timezone.get_current_timezone())
        return parsed

    def get_queryset(self):
        queryset = super().get_queryset()
        request = self.request
        user = getattr(request, "user", None)

        therapist = getattr(user, "therapist_profile", None)
        if therapist is not None:
            queryset = queryset.filter(therapist=therapist)

        start = self._parse_datetime(request.query_params.get("start"))
        end = self._parse_datetime(request.query_params.get("end"))

        if start:
            queryset = queryset.filter(end_time__gte=start)
        if end:
            queryset = queryset.filter(start_time__lt=end)

        return queryset

    def perform_create(self, serializer):
        therapist = getattr(self.request.user, "therapist_profile", None)
        if therapist is None:
            serializer.save()
        else:
            serializer.save(therapist=therapist)

    @action(detail=True, methods=["post"], url_path="send-questionnaire")
    def send_questionnaire(self, request, *args, **kwargs):
        """Send questionnaire invitation SMS for this appointment."""

        appointment: Appointment = self.get_object()

        try:
            appointment.questionnaire  # type: ignore[attr-defined]
        except Questionnaire.DoesNotExist:
            questionnaire_completed = False
        else:
            questionnaire_completed = True

        if questionnaire_completed:
            return Response(
                {"detail": "問卷已填寫，無需再次發送。"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if appointment.is_cancelled:
            return Response(
                {"detail": "已取消的預約無法發送問卷。"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not appointment.customer_phone:
            return Response(
                {"detail": "此預約缺少客戶手機，無法發送問卷。"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        already_sent = appointment.questionnaire_logs.filter(
            status=AppointmentQuestionnaireLog.STATUS_SENT
        ).exists()
        if already_sent:
            return Response(
                {"detail": "問卷已發送過，無法重複發送。"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        questionnaire_url = request.build_absolute_uri(
            reverse("questionnaires:fill", kwargs={"appointment_uuid": appointment.uuid})
        )
        message = f"您好，請協助填寫按摩服務滿意度問卷：{questionnaire_url}"

        sms_provider = get_sms_provider()

        try:
            sms_provider.send(phone_number=appointment.customer_phone, message=message)
        except Exception as exc:  # pragma: no cover - defensive fallback
            AppointmentQuestionnaireLog.objects.create(
                appointment=appointment,
                therapist=appointment.therapist,
                phone_number=appointment.customer_phone,
                message=message,
                status=AppointmentQuestionnaireLog.STATUS_FAILED,
                error_message=str(exc),
            )
            return Response(
                {"detail": "問卷發送失敗，請稍後再試。"},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        AppointmentQuestionnaireLog.objects.create(
            appointment=appointment,
            therapist=appointment.therapist,
            phone_number=appointment.customer_phone,
            message=message,
            status=AppointmentQuestionnaireLog.STATUS_SENT,
            sent_at=timezone.now(),
        )

        return Response({"detail": "問卷已成功發送。"}, status=status.HTTP_200_OK)


class TherapistAvailabilityView(APIView):
    """Expose therapist availability windows for public booking flow."""

    permission_classes = [permissions.AllowAny]
    authentication_classes: list = []
    MAX_RANGE = timedelta(days=31)

    def get(self, request, therapist_uuid):
        therapist = get_object_or_404(Therapist, uuid=therapist_uuid)
        tz = ensure_timezone(therapist.timezone)

        start_raw = request.query_params.get("start")
        end_raw = request.query_params.get("end")

        if not start_raw or not end_raw:
            return Response(
                {"detail": "Query parameters 'start' and 'end' are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        start_local = self._parse_local_datetime(start_raw, tz)
        end_local = self._parse_local_datetime(end_raw, tz)

        if start_local is None or end_local is None:
            return Response(
                {"detail": "Invalid datetime format. Use ISO 8601 strings (e.g. 2024-03-01T09:00)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if end_local <= start_local:
            return Response(
                {"detail": "'end' must be after 'start'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if end_local - start_local > self.MAX_RANGE:
            return Response(
                {"detail": "Requested range cannot exceed 31 days."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        start_utc = to_utc(start_local, therapist.timezone)
        end_utc = to_utc(end_local, therapist.timezone)

        ensure_working_hours_occurrences(therapist, range_start=start_utc, range_end=end_utc)
        ensure_series_occurrences(therapist, range_start=start_utc, range_end=end_utc)

        available = self._collect_working_windows(
            therapist, start_local, end_local, start_utc, end_utc
        )
        blocked = self._collect_blocked_windows(
            therapist, start_local, end_local, start_utc, end_utc
        )

        payload = {
            "therapist_uuid": str(therapist.uuid),
            "timezone": therapist.timezone,
            "range": {
                "start": start_local.isoformat(),
                "end": end_local.isoformat(),
            },
            "available": available,
            "blocked": blocked,
        }
        return Response(payload, status=status.HTTP_200_OK)

    def _parse_local_datetime(self, value: str, tz) -> Optional[datetime]:
        parsed = parse_datetime(value)
        if parsed is None:
            return None
        if timezone.is_naive(parsed):
            return parsed.replace(tzinfo=tz)
        return parsed.astimezone(tz)

    def _collect_working_windows(
        self,
        therapist: Therapist,
        range_start_local,
        range_end_local,
        range_start_utc,
        range_end_utc,
    ) -> list[dict[str, str]]:
        working_qs = (
            TherapistWorkingHours.objects.filter(
                therapist=therapist,
                starts_at__lt=range_end_utc,
                ends_at__gt=range_start_utc,
                is_skipped=False,
            )
            .order_by("starts_at")
            .only("starts_at", "ends_at")
        )

        windows: list[dict[str, str]] = []
        for record in working_qs:
            clipped = self._clip_interval(
                to_local(record.starts_at, therapist.timezone),
                to_local(record.ends_at, therapist.timezone),
                range_start_local,
                range_end_local,
            )
            if clipped:
                windows.append(
                    {"start": clipped[0].isoformat(), "end": clipped[1].isoformat()}
                )
        windows.sort(key=lambda item: item["start"])
        return windows

    def _collect_blocked_windows(
        self,
        therapist: Therapist,
        range_start_local,
        range_end_local,
        range_start_utc,
        range_end_utc,
    ) -> list[dict[str, str]]:
        blocked_intervals: list[dict[str, str]] = []

        time_off_qs = (
            TherapistTimeOff.objects.filter(
                therapist=therapist,
                is_skipped=False,
                starts_at__lt=range_end_utc,
                ends_at__gt=range_start_utc,
            )
            .order_by("starts_at")
            .only("starts_at", "ends_at")
        )

        for record in time_off_qs:
            clipped = self._clip_interval(
                to_local(record.starts_at, therapist.timezone),
                to_local(record.ends_at, therapist.timezone),
                range_start_local,
                range_end_local,
            )
            if clipped:
                blocked_intervals.append(
                    {"start": clipped[0].isoformat(), "end": clipped[1].isoformat()}
                )

        appointment_qs = (
            Appointment.objects.filter(
                therapist=therapist,
                is_cancelled=False,
                start_time__lt=range_end_utc,
                end_time__gt=range_start_utc,
            )
            .order_by("start_time")
            .only("start_time", "end_time")
        )

        for appointment in appointment_qs:
            clipped = self._clip_interval(
                to_local(appointment.start_time, therapist.timezone),
                to_local(appointment.end_time, therapist.timezone),
                range_start_local,
                range_end_local,
            )
            if clipped:
                blocked_intervals.append(
                    {"start": clipped[0].isoformat(), "end": clipped[1].isoformat()}
                )

        blocked_intervals.sort(key=lambda item: item["start"])
        return blocked_intervals

    @staticmethod
    def _clip_interval(start_dt, end_dt, range_start, range_end):
        clipped_start = max(start_dt, range_start)
        clipped_end = min(end_dt, range_end)
        if clipped_start >= clipped_end:
            return None
        return clipped_start, clipped_end


    def perform_update(self, serializer):
        therapist = getattr(self.request.user, "therapist_profile", None)
        if therapist is None:
            serializer.save()
        else:
            serializer.save(therapist=therapist)
