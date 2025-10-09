"""Viewset for therapist working hours management."""

from __future__ import annotations

from datetime import datetime, timezone as dt_timezone
from typing import Optional

from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import permissions, viewsets
from rest_framework.exceptions import PermissionDenied, ValidationError

from scheduling.models import TherapistWorkingHours
from scheduling.services import ensure_working_hours_occurrences
from therapist_panel.api.serializers import TherapistWorkingHoursSerializer


def _parse_to_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    parsed = parse_datetime(value)
    if parsed is None:
        return None
    return parsed


def _as_utc(value: Optional[datetime]) -> Optional[datetime]:
    if value is None:
        return None
    if timezone.is_naive(value):
        return timezone.make_aware(value, dt_timezone.utc)
    return value.astimezone(dt_timezone.utc)


class TherapistWorkingHoursViewSet(viewsets.ModelViewSet):
    serializer_class = TherapistWorkingHoursSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "uuid"

    def get_serializer_context(self):
        context = super().get_serializer_context()
        therapist = getattr(self.request.user, "therapist_profile", None)
        if therapist is not None:
            context["therapist"] = therapist
        return context

    def list(self, request, *args, **kwargs):
        therapist = getattr(request.user, "therapist_profile", None)
        start_raw = _parse_to_datetime(request.query_params.get("start"))
        end_raw = _parse_to_datetime(request.query_params.get("end"))
        if therapist is not None:
            ensure_working_hours_occurrences(therapist, range_start=start_raw, range_end=end_raw)
        return super().list(request, *args, **kwargs)

    def get_queryset(self):
        queryset = (
            TherapistWorkingHours.objects.select_related("therapist", "therapist__user", "series")
            .order_by("starts_at")
        )
        user = self.request.user
        if user.is_staff:
            qs = queryset
        else:
            therapist = getattr(user, "therapist_profile", None)
            if therapist is None:
                return queryset.none()
            qs = queryset.filter(therapist=therapist)

        start_param = _parse_to_datetime(self.request.query_params.get("start"))
        end_param = _parse_to_datetime(self.request.query_params.get("end"))
        start_utc = _as_utc(start_param)
        end_utc = _as_utc(end_param)
        if start_utc is not None:
            qs = qs.filter(ends_at__gt=start_utc)
        if end_utc is not None:
            qs = qs.filter(starts_at__lt=end_utc)
        return qs

    def perform_create(self, serializer):
        therapist = getattr(self.request.user, "therapist_profile", None)
        if therapist is None and not self.request.user.is_staff:
            raise PermissionDenied("Only therapists can create working hours records.")
        if therapist is not None:
            serializer.save(therapist=therapist)
        else:
            serializer.save()

    def perform_update(self, serializer):
        therapist = getattr(self.request.user, "therapist_profile", None)
        instance = serializer.instance
        if therapist is None and not self.request.user.is_staff:
            raise PermissionDenied("Only therapists can update working hours records.")
        if therapist is not None and instance.therapist_id != therapist.id:
            raise PermissionDenied("You cannot modify another therapist's working hours record.")
        serializer.save()

    def perform_destroy(self, instance):
        therapist = getattr(self.request.user, "therapist_profile", None)
        if therapist is None and not self.request.user.is_staff:
            raise PermissionDenied("Only therapists can delete working hours records.")
        if therapist is not None and instance.therapist_id != therapist.id:
            raise PermissionDenied("You cannot delete another therapist's working hours record.")

        scope = self.request.query_params.get("scope")
        if scope == "series":
            if not instance.series_id:
                raise ValidationError({"scope": "This working hours entry is not part of a recurring series."})
            series = instance.series
            series.is_active = False
            series.save(update_fields=["is_active", "updated_at"])
            series.occurrences.all().delete()
            return

        if instance.series_id:
            raise ValidationError(
                {
                    "detail": "Single occurrences from recurring working hours cannot be removed. "
                    "Create a time off entry instead."
                }
            )

        instance.delete()


__all__ = ["TherapistWorkingHoursViewSet"]
