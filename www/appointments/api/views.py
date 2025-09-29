"""Viewsets for appointment resources."""

from rest_framework import viewsets

from appointments.models import Appointment
from appointments.api.serializers import AppointmentSerializer


class AppointmentViewSet(viewsets.ModelViewSet):
    """CRUD operations for appointments."""

    queryset = Appointment.objects.select_related("therapist", "treatment").all()
    serializer_class = AppointmentSerializer
    lookup_field = "uuid"
