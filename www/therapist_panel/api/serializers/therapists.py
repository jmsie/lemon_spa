"""Serializers for therapist resources."""

from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from rest_framework import serializers

from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from therapist_panel.models import Therapist

User = get_user_model()


class TherapistSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
    email = serializers.EmailField(source="user.email", read_only=True)
    first_name = serializers.CharField(source="user.first_name", read_only=True)
    last_name = serializers.CharField(source="user.last_name", read_only=True)
    phone_number = serializers.CharField(source="user.phone_number", read_only=True)

    class Meta:
        model = Therapist
        fields = [
            "uuid",
            "id",
            "user",
            "email",
            "first_name",
            "last_name",
            "nickname",
            "address",
            "timezone",
            "booking_notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "uuid",
            "created_at",
            "updated_at",
            "email",
            "first_name",
            "last_name",
            "phone_number",
        ]

    def validate_user(self, user: User) -> User:
        if self.instance and self.instance.user == user:
            return user

        try:
            user.therapist_profile
        except ObjectDoesNotExist:
            return user

        raise serializers.ValidationError("This user is already linked to a therapist.")

    def validate_timezone(self, value: str) -> str:
        if not value:
            raise serializers.ValidationError("Timezone is required.")
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:  # pragma: no cover - tiny guard
            raise serializers.ValidationError("Invalid timezone identifier.") from exc
        return value
