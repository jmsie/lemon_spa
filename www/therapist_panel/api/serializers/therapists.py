"""Serializers for therapist resources."""

from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from rest_framework import serializers

from therapist_panel.models import Therapist

User = get_user_model()


class TherapistSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
    email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = Therapist
        fields = [
            "uuid",
            "id",
            "user",
            "email",
            "last_name",
            "first_name",
            "nickname",
            "phone_number",
            "address",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "uuid", "created_at", "updated_at", "email"]

    def validate_user(self, user: User) -> User:
        if self.instance and self.instance.user == user:
            return user

        try:
            user.therapist_profile
        except ObjectDoesNotExist:
            return user

        raise serializers.ValidationError("This user is already linked to a therapist.")
