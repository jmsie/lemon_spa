"""Serializers for therapist treatment resources."""

from rest_framework import serializers

from therapist_panel.models import TherapistTreatment


class TherapistTreatmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = TherapistTreatment
        fields = [
            "id",
            "therapist",
            "name",
            "duration_minutes",
            "price",
            "notes",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "therapist"]
