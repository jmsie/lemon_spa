"""Viewset for therapist treatment resources."""

from rest_framework import permissions, viewsets
from rest_framework.exceptions import PermissionDenied

from therapist_panel.models import TherapistTreatment
from therapist_panel.api.serializers import TherapistTreatmentSerializer


class TherapistTreatmentViewSet(viewsets.ModelViewSet):
    serializer_class = TherapistTreatmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = TherapistTreatment.objects.select_related("therapist", "therapist__user")
        user = self.request.user
        if user.is_staff:
            return queryset
        therapist = getattr(user, "therapist_profile", None)
        if therapist is None:
            return queryset.none()
        return queryset.filter(therapist=therapist)

    def perform_create(self, serializer):
        therapist = getattr(self.request.user, "therapist_profile", None)
        if therapist is None:
            raise PermissionDenied("Only therapists can create treatments.")
        serializer.save(therapist=therapist)

    def perform_update(self, serializer):
        therapist = getattr(self.request.user, "therapist_profile", None)
        if therapist is None and not self.request.user.is_staff:
            raise PermissionDenied("Only therapists can update treatments.")
        serializer.save()
