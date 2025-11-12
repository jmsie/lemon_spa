"""Public views for booking appointments."""

from __future__ import annotations

import logging
from typing import Any

from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views.generic import CreateView

from appointments.forms import AppointmentForm
from appointments.models import Appointment
from appointments.notifications import notify_new_public_booking
from appointments.utils import serialize_public_appointment
from phone_verification.exceptions import (
    PhoneVerificationError,
    SendLimitReached,
    SendRateLimited,
)
from phone_verification.payloads import (
    build_verification_error_payload,
    build_verification_success_payload,
)
from phone_verification.services import PhoneVerificationService
from therapist_panel.models import Therapist

logger = logging.getLogger(__name__)


class AppointmentCreateView(SuccessMessageMixin, CreateView):
    """Allow visitors to book a massage without authentication."""

    model = Appointment
    form_class = AppointmentForm
    template_name = "appointments/appointment_form.html"
    success_message = "預約已成立"

    selected_therapist: Therapist | None = None
    verification_service_class = PhoneVerificationService
    _verification_service: PhoneVerificationService | None = None

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

        self.object = form.save()
        appointment = self.object

        notify_new_public_booking(appointment)

        verification_required = False
        verification_payload: dict[str, Any] | None = None
        verification_message: str | None = None
        verification_status_code = 202

        phone_number = appointment.customer_phone
        service = self.get_verification_service() if phone_number else None

        if service and phone_number:
            status = service.get_status(phone_number)
            if not status.get("is_verified", False):
                verification_required = True
                try:
                    result = service.request_code(phone_number)
                except PhoneVerificationError as exc:
                    logger.warning("Phone verification failed for %s: %s", phone_number, exc)
                    verification_payload = build_verification_error_payload(
                        phone_number=phone_number,
                        status=status,
                        error=exc,
                        service=service,
                    )
                    verification_message = verification_payload.get(
                        "message", "手機驗證失敗，請稍後再試或聯絡客服。"
                    )
                    verification_status_code = (
                        429
                        if isinstance(exc, (SendRateLimited, SendLimitReached))
                        else 400
                    )
                else:
                    verification_payload = build_verification_success_payload(
                        result=result,
                        service=service,
                    )
                    verification_message = "手機尚未驗證，請輸入收到的驗證碼完成預約。"
                    verification_status_code = 202

        if self._wants_json():
            if verification_required:
                payload = {
                    "success": False,
                    "verification_required": True,
                    "message": verification_message
                    or "手機尚未驗證，請輸入收到的驗證碼完成預約。",
                    "appointment": {"uuid": str(appointment.uuid)},
                    "verification": verification_payload or {},
                }
                return JsonResponse(payload, status=verification_status_code)

            payload = {
                "success": True,
                "message": self.get_success_message(form.cleaned_data),
                "appointment": self._serialize_appointment(appointment),
            }
            return JsonResponse(payload, status=201)

        if verification_required:
            messages.warning(
                self.request,
                verification_message
                or "手機尚未驗證，請輸入收到的驗證碼完成預約。",
            )
            return HttpResponseRedirect(self.get_success_url())

        messages.success(self.request, self.get_success_message(form.cleaned_data))
        return HttpResponseRedirect(self.get_success_url())

    def form_invalid(self, form: AppointmentForm):
        if self._wants_json():
            errors_json = form.errors.get_json_data()
            errors = {
                field: [entry["message"] for entry in messages]
                for field, messages in errors_json.items()
            }
            return JsonResponse({"success": False, "errors": errors}, status=400)
        return super().form_invalid(form)

    def get_success_url(self) -> str:
        if self.selected_therapist:
            return reverse("appointments:book_with_therapist", args=[self.selected_therapist.uuid])
        return reverse("appointments:book")

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["selected_therapist"] = self.selected_therapist
        form: AppointmentForm | None = context.get("form")
        placeholder_uuid = "00000000-0000-0000-0000-000000000000"
        appointment_config: dict[str, Any] = {
            "availabilityUrlTemplate": reverse("api:appointments:availability", args=[placeholder_uuid]),
            "availabilityPlaceholder": placeholder_uuid,
            "selectedTherapist": None,
            "therapists": {},
            "treatments": {},
        }

        if form:
            therapist_field = form.fields.get("therapist")
            treatment_field = form.fields.get("treatment")

            if therapist_field:
                therapists_qs = therapist_field.queryset
                appointment_config["therapists"] = {
                    str(therapist.pk): {
                        "uuid": str(therapist.uuid),
                        "timezone": therapist.timezone,
                        "display_name": therapist.nickname,
                    }
                    for therapist in therapists_qs
                }

            if treatment_field:
                treatments_qs = treatment_field.queryset.select_related("therapist")
                appointment_config["treatments"] = {
                    str(treatment.pk): {
                        "duration_minutes": treatment.duration_minutes,
                        "therapist_id": treatment.therapist_id,
                        "notes": treatment.notes,
                    }
                    for treatment in treatments_qs
                }

            if self.selected_therapist:
                appointment_config["selectedTherapist"] = {
                    "uuid": str(self.selected_therapist.uuid),
                    "timezone": self.selected_therapist.timezone,
                    "pk": str(self.selected_therapist.pk),
                }

        context["appointment_config"] = appointment_config
        if self.request.method == "POST":
            context["appointment_selected_date"] = self.request.POST.get("appointment-date", "")
        else:
            context["appointment_selected_date"] = ""
        today = timezone.localdate()
        context["appointment_min_date"] = today.isoformat()
        return context

    def _wants_json(self) -> bool:
        accept_header = self.request.headers.get("Accept", "")
        requested_with = self.request.headers.get("X-Requested-With", "")
        return requested_with.lower() == "xmlhttprequest" or "application/json" in accept_header.lower()

    def get_verification_service(self) -> PhoneVerificationService:
        if self._verification_service is None:
            self._verification_service = self.verification_service_class()
        return self._verification_service

    def _serialize_appointment(self, appointment: Appointment) -> dict[str, Any]:
        return serialize_public_appointment(appointment)
