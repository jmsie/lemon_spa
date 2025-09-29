"""Views for the questionnaires app."""

from __future__ import annotations

from typing import Any

from django.contrib.messages.views import SuccessMessageMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import CreateView, TemplateView

from appointments.models import Appointment
from questionnaires.forms import QuestionnaireForm
from questionnaires.models import Questionnaire


class AppointmentContextMixin:
    """Provide the appointment based on the UUID in the URL."""

    appointment: Appointment | None = None

    def get_appointment(self) -> Appointment:
        if self.appointment is None:
            appointment_uuid = self.kwargs.get("appointment_uuid")
            queryset = Appointment.objects.select_related("therapist")
            self.appointment = get_object_or_404(queryset, uuid=appointment_uuid)
        return self.appointment

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["appointment"] = self.get_appointment()
        context["therapist"] = self.get_appointment().therapist
        return context


class QuestionnaireCreateView(AppointmentContextMixin, SuccessMessageMixin, CreateView):
    """Allow clients to submit feedback for a specific appointment."""

    model = Questionnaire
    form_class = QuestionnaireForm
    template_name = "questionnaires/questionnaire_form.html"
    success_message = "感謝您的回饋！"

    def dispatch(self, request, *args, **kwargs):
        appointment = self.get_appointment()
        try:
            appointment.questionnaire
        except Questionnaire.DoesNotExist:
            pass
        else:
            return redirect("questionnaires:already_submitted", appointment_uuid=appointment.uuid)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form: QuestionnaireForm):
        appointment = self.get_appointment()
        form.instance.appointment = appointment
        form.instance.therapist = appointment.therapist
        return super().form_valid(form)

    def get_success_url(self) -> str:
        appointment = self.get_appointment()
        return reverse("questionnaires:thank_you", kwargs={"appointment_uuid": appointment.uuid})


class QuestionnaireThankYouView(AppointmentContextMixin, TemplateView):
    """Simple confirmation page shown after questionnaire submission."""

    template_name = "questionnaires/questionnaire_submitted.html"

    def dispatch(self, request, *args, **kwargs):
        appointment = self.get_appointment()
        try:
            appointment.questionnaire
        except Questionnaire.DoesNotExist:
            return redirect("questionnaires:fill", appointment_uuid=appointment.uuid)
        return super().dispatch(request, *args, **kwargs)


class QuestionnaireAlreadySubmittedView(AppointmentContextMixin, TemplateView):
    """Inform guests that the questionnaire for this appointment is already completed."""

    template_name = "questionnaires/questionnaire_already_submitted.html"

    def dispatch(self, request, *args, **kwargs):
        appointment = self.get_appointment()
        try:
            appointment.questionnaire
        except Questionnaire.DoesNotExist:
            return redirect("questionnaires:fill", appointment_uuid=appointment.uuid)
        return super().dispatch(request, *args, **kwargs)


__all__ = [
    "QuestionnaireCreateView",
    "QuestionnaireThankYouView",
    "QuestionnaireAlreadySubmittedView",
]
