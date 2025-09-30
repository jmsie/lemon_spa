"""Serializers for appointment resources."""

from __future__ import annotations

from typing import Any

from rest_framework import serializers

from appointments.models import Appointment


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
            "end_time",
            "therapist_uuid",
            "therapist_name",
            "treatment_name",
        ]

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        therapist = attrs.get("therapist") or getattr(self.instance, "therapist", None)
        treatment = attrs.get("treatment") or getattr(self.instance, "treatment", None)

        if therapist and treatment and treatment.therapist_id != therapist.id:
            raise serializers.ValidationError(
                {"treatment": "Treatment does not belong to the selected therapist."}
            )

        return super().validate(attrs)
