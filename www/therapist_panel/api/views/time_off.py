"""Viewset for therapist time off management."""

from __future__ import annotations

from rest_framework import permissions, viewsets
from rest_framework.exceptions import PermissionDenied

from scheduling.models import TherapistTimeOff
from therapist_panel.api.serializers import TherapistTimeOffSerializer


class TherapistTimeOffViewSet(viewsets.ModelViewSet):
    serializer_class = TherapistTimeOffSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "uuid"

    def get_serializer_context(self):
        context = super().get_serializer_context()
        therapist = getattr(self.request.user, "therapist_profile", None)
        if therapist is not None:
            context["therapist"] = therapist
        return context

    def get_queryset(self):
        queryset = TherapistTimeOff.objects.select_related("therapist", "therapist__user")
        user = self.request.user
        if user.is_staff:
            return queryset
        therapist = getattr(user, "therapist_profile", None)
        if therapist is None:
            return queryset.none()
        return queryset.filter(therapist=therapist)

    def perform_create(self, serializer):
        therapist = getattr(self.request.user, "therapist_profile", None)
        if therapist is None and not self.request.user.is_staff:
            raise PermissionDenied("Only therapists can create time off records.")
        if therapist is not None:
            serializer.save(therapist=therapist)
        else:
            serializer.save()

    def perform_update(self, serializer):
        therapist = getattr(self.request.user, "therapist_profile", None)
        instance = serializer.instance
        if therapist is None and not self.request.user.is_staff:
            raise PermissionDenied("Only therapists can update time off records.")
        if therapist is not None and instance.therapist_id != therapist.id:
            raise PermissionDenied("You cannot modify another therapist's time off record.")
        serializer.save()

    def perform_destroy(self, instance):
        therapist = getattr(self.request.user, "therapist_profile", None)
        if therapist is None and not self.request.user.is_staff:
            raise PermissionDenied("Only therapists can delete time off records.")
        if therapist is not None and instance.therapist_id != therapist.id:
            raise PermissionDenied("You cannot delete another therapist's time off record.")
        instance.delete()


__all__ = ["TherapistTimeOffViewSet"]
