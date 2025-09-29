"""Views for therapist panel web interface and legacy API imports."""

from django.views.generic import TemplateView

from accounts.constants import ROLE_CLIENT, ROLE_THERAPIST
from accounts.mixins import TherapistRoleRequiredMixin
from accounts.services import get_active_role, role_to_label, user_has_role
from therapist_panel.api.views import TherapistViewSet


class TherapistPanelIndexView(TherapistRoleRequiredMixin, TemplateView):
    """Simple landing page after successful login."""

    template_name = "therapist_panel/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        request = self.request
        active_role = get_active_role(request) or ROLE_THERAPIST
        has_therapist_role = user_has_role(request.user, ROLE_THERAPIST)
        therapist_profile = None
        if has_therapist_role:
            therapist_profile = getattr(request.user, "therapist_profile", None)
        context.update(
            {
                "active_role": active_role,
                "active_role_label": role_to_label(active_role),
                "has_client_role": user_has_role(request.user, ROLE_CLIENT),
                "has_therapist_role": has_therapist_role,
                "therapist_profile": therapist_profile,
            }
        )
        return context


__all__ = [
    "TherapistViewSet",
    "TherapistPanelIndexView",
]
