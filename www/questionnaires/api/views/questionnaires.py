"""Viewset for questionnaire resources."""

from rest_framework import permissions, viewsets
from rest_framework.exceptions import PermissionDenied

from questionnaires.models import Questionnaire
from questionnaires.api.serializers import QuestionnaireSerializer


class QuestionnaireViewSet(viewsets.ModelViewSet):
    serializer_class = QuestionnaireSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = Questionnaire.objects.select_related("therapist", "therapist__user")
        user = self.request.user
        if user.is_staff:
            return queryset
        therapist = getattr(user, "therapist_profile", None)
        if therapist is None:
            return queryset.none()
        return queryset.filter(therapist=therapist)

    def perform_create(self, serializer):
        # Validation already assigns therapist when appropriate.
        serializer.save()

    def perform_update(self, serializer):
        instance = self.get_object()
        user = self.request.user
        therapist = getattr(user, "therapist_profile", None)
        if therapist is None and not user.is_staff:
            raise PermissionDenied("Only therapists can update questionnaires.")
        if therapist is not None and instance.therapist != therapist:
            raise PermissionDenied("You may only modify your own questionnaires.")
        serializer.save()

    def perform_destroy(self, instance):
        user = self.request.user
        therapist = getattr(user, "therapist_profile", None)
        if therapist is None and not user.is_staff:
            raise PermissionDenied("Only therapists can delete questionnaires.")
        if therapist is not None and instance.therapist != therapist:
            raise PermissionDenied("You may only delete your own questionnaires.")
        instance.delete()
