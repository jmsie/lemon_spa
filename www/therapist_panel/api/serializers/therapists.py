"""Serializers for therapist resources."""

from rest_framework import serializers

from therapist_panel.models import Therapist


class TherapistSerializer(serializers.ModelSerializer):
    class Meta:
        model = Therapist
        fields = [
            "id",
            "last_name",
            "first_name",
            "nickname",
            "phone_number",
            "address",
            "email",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
