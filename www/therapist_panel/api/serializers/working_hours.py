"""Serializers for therapist working hours management."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Optional

from django.utils import timezone
from rest_framework import serializers

from scheduling.models import TherapistWorkingHours, TherapistWorkingHoursSeries
from scheduling.utils import ensure_timezone, from_utc, to_utc


@dataclass
class _WorkingHoursRepeatPayload:
    weekday: int
    repeat_interval: int
    repeat_until: Optional[date]


class TherapistWorkingHoursSerializer(serializers.ModelSerializer):
    therapist_uuid = serializers.UUIDField(source="therapist.uuid", read_only=True)
    therapist_timezone = serializers.CharField(source="therapist.timezone", read_only=True)
    series_uuid = serializers.UUIDField(source="series.uuid", read_only=True)
    is_recurring = serializers.SerializerMethodField()
    weekday = serializers.IntegerField(min_value=0, max_value=6, required=False)
    repeat_interval = serializers.IntegerField(min_value=1, required=False, write_only=True)
    repeat_until = serializers.DateField(required=False, allow_null=True, write_only=True)

    class Meta:
        model = TherapistWorkingHours
        fields = [
            "id",
            "uuid",
            "therapist",
            "therapist_uuid",
            "therapist_timezone",
            "series_uuid",
            "is_recurring",
            "is_generated",
            "weekday",
            "starts_at",
            "ends_at",
            "note",
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
            "is_generated",
            "created_at",
            "updated_at",
        ]
        extra_kwargs = {"therapist": {"required": False}}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._local_starts_at: Optional[datetime] = None
        self._local_ends_at: Optional[datetime] = None
        self._repeat_payload: Optional[_WorkingHoursRepeatPayload] = None

    def get_is_recurring(self, instance: TherapistWorkingHours) -> bool:
        return bool(instance.series_id)

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

        has_repeat_fields = any(
            key in attrs for key in ("weekday", "repeat_interval", "repeat_until")
        ) or "weekday" in self.initial_data

        if has_repeat_fields:
            if self.instance is not None:
                raise serializers.ValidationError(
                    {"weekday": "Recurring settings cannot be changed for existing working hours entries."}
                )
            weekday = attrs.get("weekday")
            if weekday is None:
                raise serializers.ValidationError({"weekday": "Weekday is required for recurring working hours."})
            if self._local_starts_at is None or self._local_ends_at is None:
                raise serializers.ValidationError(
                    {"starts_at": "Recurring rules require start and end times in therapist timezone."}
                )

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

            if start_local.weekday() != weekday:
                raise serializers.ValidationError(
                    {"weekday": "Weekday must match the provided start time."}
                )

            repeat_until = attrs.get("repeat_until")
            if repeat_until and repeat_until < start_local.date():
                raise serializers.ValidationError(
                    {"repeat_until": "Repeat end date must be after the first occurrence."}
                )

            interval = attrs.get("repeat_interval") or 1
            self._repeat_payload = _WorkingHoursRepeatPayload(
                weekday=int(weekday),
                repeat_interval=int(interval),
                repeat_until=repeat_until,
            )

        return super().validate(attrs)

    def create(self, validated_data: dict[str, Any]) -> TherapistWorkingHours:
        validated_data.pop("repeat_interval", None)
        validated_data.pop("repeat_until", None)
        weekday = validated_data.pop("weekday", None)

        therapist = validated_data["therapist"]

        if self._repeat_payload:
            if self._local_starts_at is None or self._local_ends_at is None:
                raise serializers.ValidationError({"weekday": "Recurring configuration is incomplete."})

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

            series = TherapistWorkingHoursSeries.objects.create(
                therapist=therapist,
                weekday=self._repeat_payload.weekday,
                repeat_interval=self._repeat_payload.repeat_interval,
                start_date=start_local.date(),
                start_time=start_local.time().replace(tzinfo=None),
                end_time=end_local.time().replace(tzinfo=None),
                repeat_until=self._repeat_payload.repeat_until,
            )
            validated_data["series"] = series
        elif weekday is not None:
            # Non-recurring entries do not store weekday; guard to avoid silent ignore.
            if self._local_starts_at:
                therapist_zone = ensure_timezone(therapist.timezone)
                start_local = (
                    self._local_starts_at
                    if timezone.is_naive(self._local_starts_at)
                    else self._local_starts_at.astimezone(therapist_zone)
                )
                if start_local.weekday() != weekday:
                    raise serializers.ValidationError(
                        {"weekday": "Weekday must match the provided start time."}
                    )

        return super().create(validated_data)

    def update(self, instance: TherapistWorkingHours, validated_data: dict[str, Any]) -> TherapistWorkingHours:
        validated_data.pop("repeat_interval", None)
        validated_data.pop("repeat_until", None)
        validated_data.pop("weekday", None)
        return super().update(instance, validated_data)

    def to_representation(self, instance: TherapistWorkingHours) -> dict[str, Any]:
        data = super().to_representation(instance)
        tz_name = instance.therapist.timezone
        starts_local = from_utc(instance.starts_at, tz_name)
        ends_local = from_utc(instance.ends_at, tz_name)
        data["starts_at"] = starts_local.isoformat()
        data["ends_at"] = ends_local.isoformat()
        if instance.series_id:
            data["weekday"] = instance.series.weekday
        else:
            data["weekday"] = starts_local.weekday()
        return data


__all__ = ["TherapistWorkingHoursSerializer"]
