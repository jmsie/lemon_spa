"""Views for client dashboard."""

from django.views.generic import TemplateView

from accounts.constants import ROLE_CLIENT, ROLE_THERAPIST
from accounts.mixins import ClientRoleRequiredMixin
from accounts.services import get_active_role, role_to_label, user_has_role


class ClientDashboardView(ClientRoleRequiredMixin, TemplateView):
    """Minimal dashboard for clients."""

    template_name = "client_dashboard/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        request = self.request
        active_role = get_active_role(request) or ROLE_CLIENT
        context.update(
            {
                "active_role": active_role,
                "active_role_label": role_to_label(active_role),
                "has_therapist_role": user_has_role(request.user, ROLE_THERAPIST),
            }
        )
        return context
