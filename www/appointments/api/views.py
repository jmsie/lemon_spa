"""Viewsets and endpoints for appointment resources."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import permissions, status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from appointments.models import Appointment
from appointments.api.serializers import AppointmentSerializer
from scheduling.models import TherapistTimeOff, TherapistWorkingHours
from scheduling.services import ensure_series_occurrences, ensure_working_hours_occurrences
from scheduling.utils import ensure_timezone, to_local, to_utc
from therapist_panel.models import Therapist


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
