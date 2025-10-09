"""Serializers for therapist time off management."""

from __future__ import annotations

from typing import Any

from rest_framework import serializers

from scheduling.models import TherapistTimeOff
from scheduling.utils import from_utc, to_utc


class TherapistTimeOffSerializer(serializers.ModelSerializer):
    therapist_uuid = serializers.UUIDField(source="therapist.uuid", read_only=True)
    therapist_timezone = serializers.CharField(source="therapist.timezone", read_only=True)

    class Meta:
        model = TherapistTimeOff
        fields = [
            "id",
            "uuid",
            "therapist",
            "therapist_uuid",
            "therapist_timezone",
            "starts_at",
            "ends_at",
            "note",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "uuid",
            "therapist_uuid",
            "therapist_timezone",
            "created_at",
            "updated_at",
        ]
        extra_kwargs = {"therapist": {"required": False}}

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        context_therapist = self.context.get("therapist")
        therapist = attrs.get("therapist") or getattr(self.instance, "therapist", None) or context_therapist
        if therapist is None:
            raise serializers.ValidationError({"therapist": "Therapist is required."})
        attrs.setdefault("therapist", therapist)

        starts_at = attrs.get("starts_at")
        ends_at = attrs.get("ends_at")

        if starts_at is not None:
            attrs["starts_at"] = to_utc(starts_at, therapist.timezone)
        if ends_at is not None:
            attrs["ends_at"] = to_utc(ends_at, therapist.timezone)

        final_start = attrs.get("starts_at", getattr(self.instance, "starts_at", None))
        final_end = attrs.get("ends_at", getattr(self.instance, "ends_at", None))

        if final_start and final_end and final_end <= final_start:
            raise serializers.ValidationError({"ends_at": "End time must be after start time."})

        return super().validate(attrs)

    def to_representation(self, instance: TherapistTimeOff) -> dict[str, Any]:
        data = super().to_representation(instance)
        tz_name = instance.therapist.timezone
        data["starts_at"] = from_utc(instance.starts_at, tz_name).isoformat()
        data["ends_at"] = from_utc(instance.ends_at, tz_name).isoformat()
        return data


__all__ = ["TherapistTimeOffSerializer"]
