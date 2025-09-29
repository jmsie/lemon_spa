"""Serializers for questionnaire resources."""

from rest_framework import serializers

from therapist_panel.models import Therapist
from questionnaires.models import Questionnaire


class QuestionnaireSerializer(serializers.ModelSerializer):
    therapist = serializers.PrimaryKeyRelatedField(
        queryset=Therapist.objects.all(),
        required=False,
    )
    therapist_name = serializers.CharField(
        source="therapist.nickname",
        read_only=True,
    )

    class Meta:
        model = Questionnaire
        fields = ["id", "therapist", "therapist_name", "rating", "comment", "created_at"]
        read_only_fields = ["id", "created_at", "therapist_name"]

    def validate(self, attrs):
        request = self.context.get("request")
        if request is None:
            return attrs

        user = request.user
        therapist = getattr(user, "therapist_profile", None)

        if therapist is not None:
            attrs["therapist"] = therapist
            return attrs

        if user.is_staff:
            if "therapist" not in attrs or attrs["therapist"] is None:
                raise serializers.ValidationError({
                    "therapist": "Staff users must specify the therapist for this questionnaire.",
                })
            return attrs

        raise serializers.ValidationError("Only therapists or staff can submit questionnaires.")
