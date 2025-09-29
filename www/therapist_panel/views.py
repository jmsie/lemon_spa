"""Views for therapist panel web interface and legacy API imports."""

from django.contrib import messages
from django.http import Http404
from django.urls import reverse, reverse_lazy
from django.views.generic import FormView, TemplateView

from accounts.constants import ROLE_CLIENT, ROLE_THERAPIST
from accounts.mixins import TherapistRoleRequiredMixin
from accounts.services import get_active_role, role_to_label, user_has_role
from therapist_panel.api.views import TherapistViewSet
from therapist_panel.forms import TherapistProfileForm


class TherapistPanelContextMixin(TherapistRoleRequiredMixin):
    """Inject common context needed across therapist panel pages."""

    def get_therapist_profile(self):
        profile = getattr(self.request.user, "therapist_profile", None)
        if profile and profile.user_id != self.request.user.id:
            return None
        return profile

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
        else:
            context["appointment_booking_url"] = None
        return context


class TherapistPanelIndexView(TherapistPanelContextMixin, TemplateView):
    """Simple landing page after successful login."""

    template_name = "therapist_panel/index.html"


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


__all__ = [
    "TherapistViewSet",
    "TherapistPanelIndexView",
    "TherapistProfileUpdateView",
    "TherapistTreatmentManagementView",
    "TherapistQuestionnaireListView",
]
