"""Serializers for appointment resources."""

from __future__ import annotations

from typing import Any

from datetime import timedelta

from rest_framework import serializers

from appointments.models import Appointment
from scheduling.models import TherapistTimeOff
from scheduling.utils import to_utc


class AppointmentSerializer(serializers.ModelSerializer):
    """Expose appointment details for API access."""

    therapist_uuid = serializers.UUIDField(source="therapist.uuid", read_only=True)
    therapist_name = serializers.CharField(source="therapist.nickname", read_only=True)
    treatment_name = serializers.CharField(source="treatment.name", read_only=True)

    class Meta:
        model = Appointment
        fields = [
            "id",
            "uuid",
            "therapist",
            "therapist_uuid",
            "therapist_name",
            "treatment",
            "treatment_name",
            "start_time",
            "end_time",
            "customer_name",
            "customer_phone",
            "note",
            "is_cancelled",
        ]
        read_only_fields = [
            "id",
            "uuid",
            "therapist",
            "end_time",
            "therapist_uuid",
            "therapist_name",
            "treatment_name",
        ]

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        therapist = (
            attrs.get("therapist")
            or getattr(self.instance, "therapist", None)
            or getattr(getattr(self.context.get("request"), "user", None), "therapist_profile", None)
        )
        treatment = attrs.get("treatment") or getattr(self.instance, "treatment", None)

        if therapist and treatment and treatment.therapist_id != therapist.id:
            raise serializers.ValidationError(
                {"treatment": "Treatment does not belong to the selected therapist."}
            )

        if therapist is None:
            raise serializers.ValidationError({"therapist": "Therapist context is required."})

        start_time = attrs.get("start_time")
        if start_time is not None:
            attrs["start_time"] = to_utc(start_time, therapist.timezone)

        planned_start = attrs.get("start_time", getattr(self.instance, "start_time", None))

        if planned_start is not None and treatment is not None:
            total_minutes = treatment.duration_minutes + treatment.preparation_minutes
            planned_end = planned_start + timedelta(minutes=total_minutes)

            conflict_exists = TherapistTimeOff.objects.filter(
                therapist=therapist,
                is_skipped=False,
                ends_at__gt=planned_start,
                starts_at__lt=planned_end,
            ).exists()

            if conflict_exists:
                raise serializers.ValidationError(
                    {"start_time": "This appointment overlaps with an existing time off block."}
                )

        return super().validate(attrs)
