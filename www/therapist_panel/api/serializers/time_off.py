"""Serializers for therapist time off management."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Optional

from django.utils import timezone
from rest_framework import serializers

from scheduling.models import TherapistTimeOff, TherapistTimeOffSeries
from scheduling.utils import ensure_timezone, from_utc, to_utc


@dataclass
class _RepeatPayload:
    repeat_type: str
    repeat_interval: int
    repeat_until: Optional[date]


class TherapistTimeOffSerializer(serializers.ModelSerializer):
    therapist_uuid = serializers.UUIDField(source="therapist.uuid", read_only=True)
    therapist_timezone = serializers.CharField(source="therapist.timezone", read_only=True)
    series_uuid = serializers.UUIDField(source="series.uuid", read_only=True)
    is_recurring = serializers.SerializerMethodField()

    repeat_type = serializers.ChoiceField(
        choices=TherapistTimeOffSeries.REPEAT_CHOICES, required=False, write_only=True
    )
    repeat_interval = serializers.IntegerField(min_value=1, required=False, write_only=True)
    repeat_until = serializers.DateField(required=False, allow_null=True, write_only=True)

    class Meta:
        model = TherapistTimeOff
        fields = [
            "id",
            "uuid",
            "therapist",
            "therapist_uuid",
            "therapist_timezone",
            "series_uuid",
            "is_recurring",
            "starts_at",
            "ends_at",
            "note",
            "repeat_type",
            "repeat_interval",
            "repeat_until",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "uuid",
            "therapist_uuid",
            "therapist_timezone",
            "series_uuid",
            "is_recurring",
            "created_at",
            "updated_at",
        ]
        extra_kwargs = {"therapist": {"required": False}}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._local_starts_at: Optional[datetime] = None
        self._local_ends_at: Optional[datetime] = None
        self._repeat_payload: Optional[_RepeatPayload] = None

    def get_is_recurring(self, instance: TherapistTimeOff) -> bool:
        return bool(instance.series_id and not instance.is_skipped)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        context_therapist = self.context.get("therapist")
        therapist = attrs.get("therapist") or getattr(self.instance, "therapist", None) or context_therapist
        if therapist is None:
            raise serializers.ValidationError({"therapist": "Therapist is required."})
        attrs.setdefault("therapist", therapist)

        starts_at = attrs.get("starts_at")
        ends_at = attrs.get("ends_at")
        if starts_at is not None:
            self._local_starts_at = starts_at
            attrs["starts_at"] = to_utc(starts_at, therapist.timezone)
        if ends_at is not None:
            self._local_ends_at = ends_at
            attrs["ends_at"] = to_utc(ends_at, therapist.timezone)

        final_start = attrs.get("starts_at", getattr(self.instance, "starts_at", None))
        final_end = attrs.get("ends_at", getattr(self.instance, "ends_at", None))
        if final_start and final_end and final_end <= final_start:
            raise serializers.ValidationError({"ends_at": "End time must be after start time."})

        repeat_type = attrs.get("repeat_type")
        if repeat_type is not None:
            if self.instance is not None:
                raise serializers.ValidationError(
                    {"repeat_type": "Recurring settings cannot be changed for existing time off entries."}
                )
            interval = attrs.get("repeat_interval") or 1
            repeat_until = attrs.get("repeat_until")

            if not self._local_starts_at or not self._local_ends_at:
                raise serializers.ValidationError({"repeat_type": "Recurring rules require start and end times."})

            therapist_zone = ensure_timezone(therapist.timezone)
            local_start = (
                self._local_starts_at
                if timezone.is_naive(self._local_starts_at)
                else self._local_starts_at.astimezone(therapist_zone)
            )
            local_end = (
                self._local_ends_at
                if timezone.is_naive(self._local_ends_at)
                else self._local_ends_at.astimezone(therapist_zone)
            )

            if repeat_until and repeat_until < local_start.date():
                raise serializers.ValidationError({"repeat_until": "Repeat end date must be after the first start date."})

            self._repeat_payload = _RepeatPayload(
                repeat_type=repeat_type,
                repeat_interval=int(interval),
                repeat_until=repeat_until,
            )

        return super().validate(attrs)

    def create(self, validated_data: dict[str, Any]) -> TherapistTimeOff:
        repeat_type = validated_data.pop("repeat_type", None)
        validated_data.pop("repeat_interval", None)
        validated_data.pop("repeat_until", None)

        therapist = validated_data["therapist"]

        if repeat_type:
            if not self._repeat_payload or not self._local_starts_at or not self._local_ends_at:
                raise serializers.ValidationError({"repeat_type": "Recurring configuration is incomplete."})

            therapist_zone = ensure_timezone(therapist.timezone)
            start_local = (
                self._local_starts_at
                if timezone.is_naive(self._local_starts_at)
                else self._local_starts_at.astimezone(therapist_zone)
            )
            end_local = (
                self._local_ends_at
                if timezone.is_naive(self._local_ends_at)
                else self._local_ends_at.astimezone(therapist_zone)
            )

            series = TherapistTimeOffSeries.objects.create(
                therapist=therapist,
                repeat_type=self._repeat_payload.repeat_type,
                repeat_interval=self._repeat_payload.repeat_interval,
                start_date=start_local.date(),
                start_time=start_local.time().replace(tzinfo=None),
                end_time=end_local.time().replace(tzinfo=None),
                repeat_until=self._repeat_payload.repeat_until,
                note=validated_data.get("note", ""),
            )
            validated_data["series"] = series

        return super().create(validated_data)

    def update(self, instance: TherapistTimeOff, validated_data: dict[str, Any]) -> TherapistTimeOff:
        validated_data.pop("repeat_type", None)
        validated_data.pop("repeat_interval", None)
        validated_data.pop("repeat_until", None)
        return super().update(instance, validated_data)

    def to_representation(self, instance: TherapistTimeOff) -> dict[str, Any]:
        data = super().to_representation(instance)
        tz_name = instance.therapist.timezone
        data["starts_at"] = from_utc(instance.starts_at, tz_name).isoformat()
        data["ends_at"] = from_utc(instance.ends_at, tz_name).isoformat()
        return data


__all__ = ["TherapistTimeOffSerializer"]
