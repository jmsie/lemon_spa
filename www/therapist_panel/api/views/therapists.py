"""Viewset for therapist resources."""

from rest_framework import viewsets

from therapist_panel.models import Therapist
from therapist_panel.api.serializers import TherapistSerializer


class TherapistViewSet(viewsets.ModelViewSet):
    queryset = Therapist.objects.all()
    serializer_class = TherapistSerializer
