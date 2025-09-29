"""Public views for booking appointments."""

from __future__ import annotations

from typing import Any

from django.contrib.messages.views import SuccessMessageMixin
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.generic import CreateView

from appointments.forms import AppointmentForm
from appointments.models import Appointment
from therapist_panel.models import Therapist


class AppointmentCreateView(SuccessMessageMixin, CreateView):
    """Allow visitors to book a massage without authentication."""

    model = Appointment
    form_class = AppointmentForm
    template_name = "appointments/appointment_form.html"
    success_message = "預約已送出，我們會儘快與您聯繫確認。"

    selected_therapist: Therapist | None = None

    def dispatch(self, request, *args, **kwargs):
        therapist_uuid = kwargs.get("therapist_uuid")
        if therapist_uuid:
            self.selected_therapist = get_object_or_404(Therapist, uuid=therapist_uuid)
        else:
            self.selected_therapist = None
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self) -> dict[str, Any]:
        initial = super().get_initial()
        if self.selected_therapist:
            initial["therapist"] = self.selected_therapist
        return initial

    def get_form(self, form_class: type[AppointmentForm] | None = None) -> AppointmentForm:
        form = super().get_form(form_class)
        if self.selected_therapist:
            form.fields["therapist"].initial = self.selected_therapist
            form.fields["therapist"].widget = form.fields["therapist"].hidden_widget()
            form.fields["treatment"].queryset = form.fields["treatment"].queryset.filter(
                therapist=self.selected_therapist
            )
        return form

    def form_valid(self, form: AppointmentForm):
        if self.selected_therapist:
            form.instance.therapist = self.selected_therapist
        return super().form_valid(form)

    def get_success_url(self) -> str:
        if self.selected_therapist:
            return reverse("appointments:book_with_therapist", args=[self.selected_therapist.uuid])
        return reverse("appointments:book")

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["selected_therapist"] = self.selected_therapist
        return context
