"""Views for therapist scheduling tools."""

from __future__ import annotations

from django.urls import reverse
from django.views.generic import TemplateView

from accounts.constants import ROLE_CLIENT, ROLE_THERAPIST
from accounts.mixins import TherapistRoleRequiredMixin
from accounts.services import get_active_role, role_to_label, user_has_role


class TherapistScheduleView(TherapistRoleRequiredMixin, TemplateView):
    """Display a weekly calendar of appointments for the therapist."""

    template_name = "scheduling/calendar.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        request = self.request
        therapist = getattr(request.user, "therapist_profile", None)
        active_role = get_active_role(request) or ROLE_THERAPIST
        context.update(
            {
                "therapist_profile": therapist,
                "active_role": active_role,
                "active_role_label": role_to_label(active_role),
                "has_client_role": user_has_role(request.user, ROLE_CLIENT),
                "has_therapist_role": True,
                "current_url_name": getattr(request.resolver_match, "url_name", ""),
                "appointments_api_url": reverse("api:appointments:appointment-list"),
            }
        )
        return context


__all__ = ["TherapistScheduleView"]
