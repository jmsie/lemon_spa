"""Views for therapist panel web interface and legacy API imports."""

from datetime import datetime, time, timedelta

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Exists, OuterRef
from django.http import Http404
from django.shortcuts import redirect
from django.utils import timezone
from django.urls import reverse, reverse_lazy
from django.views.generic import FormView, TemplateView

from accounts.constants import ROLE_CLIENT, ROLE_THERAPIST
from accounts.mixins import TherapistRoleRequiredMixin
from accounts.services import get_active_role, role_to_label, user_has_role
from appointments.models import Appointment, AppointmentQuestionnaireLog
from scheduling.utils import to_utc
from therapist_panel.api.views import TherapistViewSet
from therapist_panel.forms import AppointmentSearchForm, TherapistProfileForm
from therapist_panel.services import (
    get_onboarding_status,
    get_today_appointments,
    needs_onboarding,
)


class TherapistPanelContextMixin(TherapistRoleRequiredMixin):
    """Inject common context needed across therapist panel pages."""

    skip_onboarding_redirect = False

    def get_therapist_profile(self):
        profile = getattr(self.request.user, "therapist_profile", None)
        if profile and profile.user_id != self.request.user.id:
            return None
        return profile

    def dispatch(self, request, *args, **kwargs):
        therapist = self.get_therapist_profile()
        if (
            therapist
            and not self.skip_onboarding_redirect
            and needs_onboarding(therapist)
        ):
            onboarding_url = reverse("therapist_panel:onboarding")
            if request.path != onboarding_url:
                return redirect(onboarding_url)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        request = self.request
        active_role = get_active_role(request) or ROLE_THERAPIST
        has_therapist_role = user_has_role(request.user, ROLE_THERAPIST)
        context.update(
            {
                "current_url_name": getattr(request.resolver_match, "url_name", ""),
                "active_role": active_role,
                "active_role_label": role_to_label(active_role),
                "has_client_role": user_has_role(request.user, ROLE_CLIENT),
                "has_therapist_role": has_therapist_role,
                "therapist_profile": self.get_therapist_profile() if has_therapist_role else None,
            }
        )
        profile = context.get("therapist_profile")
        if profile:
            booking_path = reverse("appointments:book_with_therapist", args=[profile.uuid])
            context["appointment_booking_url"] = request.build_absolute_uri(booking_path)
            context["today_appointments"] = get_today_appointments(profile)
        else:
            context["appointment_booking_url"] = None
            context["today_appointments"] = []
        context["current_time"] = timezone.now()
        return context


class TherapistPanelIndexView(TherapistPanelContextMixin, TemplateView):
    """Simple landing page after successful login."""

    template_name = "therapist_panel/index.html"


class TherapistOnboardingView(TherapistPanelContextMixin, TemplateView):
    """Step-by-step onboarding guide for therapists without initial data."""

    template_name = "therapist_panel/onboarding.html"
    skip_onboarding_redirect = True

    def dispatch(self, request, *args, **kwargs):
        therapist = self.get_therapist_profile()
        if therapist is None:
            raise Http404("Therapist profile not found.")
        if not needs_onboarding(therapist):
            return redirect("therapist_panel:index")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        therapist = self.get_therapist_profile()
        if therapist is None:
            raise Http404("Therapist profile not found.")

        onboarding_status = get_onboarding_status(therapist)
        context.update(
            {
                "onboarding_status": onboarding_status,
                "treatments_api_url": reverse(
                    "therapist_panel:api:treatments:treatment-list"
                ),
                "working_hours_api_url": reverse(
                    "therapist_panel:api:working_hours:working-hours-list"
                ),
                "time_off_api_url": reverse(
                    "therapist_panel:api:time_off:time-off-list"
                ),
                "therapist_uuid": therapist.uuid,
                "appointments_booking_path": reverse(
                    "appointments:book_with_therapist", args=[therapist.uuid]
                ),
            }
        )
        return context


class TherapistProfileUpdateView(TherapistPanelContextMixin, FormView):
    """Allow therapists to update their own contact information."""

    form_class = TherapistProfileForm
    template_name = "therapist_panel/profile_edit.html"
    success_url = reverse_lazy("therapist_panel:profile_edit")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        profile = self.get_therapist_profile()
        if profile is None:
            raise Http404("Therapist profile not found.")
        kwargs.update({"instance": profile, "user": self.request.user})
        return kwargs

    def form_valid(self, form):
        form.save()
        messages.success(self.request, "Your contact information has been updated.")
        return super().form_valid(form)


class TherapistTreatmentManagementView(TherapistPanelContextMixin, TemplateView):
    """Interface for managing therapist treatments via the API."""

    template_name = "therapist_panel/treatments.html"


class TherapistQuestionnaireListView(TherapistPanelContextMixin, TemplateView):
    """Display questionnaires submitted for the logged-in therapist."""

    template_name = "therapist_panel/reviews.html"


class TherapistAppointmentSearchView(TherapistPanelContextMixin, TemplateView):
    """Allow therapists to search over their appointment history."""

    template_name = "therapist_panel/appointments.html"
    form_class = AppointmentSearchForm
    paginate_by = 10

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        therapist = self.get_therapist_profile()
        if therapist is None:
            raise Http404("Therapist profile not found.")

        form = self.form_class(self.request.GET or None)
        queryset = self._build_queryset(therapist)

        if form.is_bound and form.is_valid():
            queryset = self._apply_filters(queryset, therapist, form.cleaned_data)
        elif form.is_bound and not form.is_valid():
            queryset = queryset.none()

        paginator = Paginator(queryset, self.paginate_by)
        page_number = self.request.GET.get("page")
        page_obj = paginator.get_page(page_number)
        query_params = self.request.GET.copy()
        query_params.pop("page", None)
        query_string = query_params.urlencode()

        context.update(
            {
                "form": form,
                "appointments": page_obj.object_list,
                "page_obj": page_obj,
                "paginator": paginator,
                "has_filters": self._has_active_filters(form),
                "therapist_timezone": therapist.timezone,
                "query_string": query_string,
                "appointments_api_url": reverse("api:appointments:appointment-list"),
            }
        )
        return context

    def _build_queryset(self, therapist):
        sent_exists = AppointmentQuestionnaireLog.objects.filter(
            appointment=OuterRef("pk"),
            status=AppointmentQuestionnaireLog.STATUS_SENT,
        )
        return (
            Appointment.objects.filter(therapist=therapist)
            .select_related("treatment")
            .annotate(questionnaire_sent=Exists(sent_exists))
            .order_by("-start_time")
        )

    def _apply_filters(self, queryset, therapist, cleaned_data):
        phone = cleaned_data.get("customer_phone")
        name = cleaned_data.get("customer_name")
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")

        if phone:
            queryset = queryset.filter(customer_phone__icontains=phone.strip())
        if name:
            queryset = queryset.filter(customer_name__icontains=name.strip())

        if start_date:
            start_local = datetime.combine(start_date, time.min)
            queryset = queryset.filter(
                start_time__gte=to_utc(start_local, therapist.timezone),
            )

        if end_date:
            end_local = datetime.combine(end_date + timedelta(days=1), time.min)
            queryset = queryset.filter(
                start_time__lt=to_utc(end_local, therapist.timezone),
            )

        return queryset

    @staticmethod
    def _has_active_filters(form):
        if not form.is_bound:
            return False
        if form.is_valid():
            return any(value not in (None, "") for value in form.cleaned_data.values())
        for name in form.fields:
            value = form.data.get(name)
            if value not in (None, ""):
                return True
        return False


__all__ = [
    "TherapistViewSet",
    "TherapistPanelIndexView",
    "TherapistProfileUpdateView",
    "TherapistTreatmentManagementView",
    "TherapistQuestionnaireListView",
    "TherapistAppointmentSearchView",
    "TherapistOnboardingView",
]
