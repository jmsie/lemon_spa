"""Viewsets for appointment resources."""

from __future__ import annotations

from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import viewsets

from appointments.models import Appointment
from appointments.api.serializers import AppointmentSerializer


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

    def perform_update(self, serializer):
        therapist = getattr(self.request.user, "therapist_profile", None)
        if therapist is None:
            serializer.save()
        else:
            serializer.save(therapist=therapist)
