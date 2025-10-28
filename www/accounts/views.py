"""Authentication and role selection views for the portal."""

from __future__ import annotations

from urllib.parse import urlencode

from django.contrib.auth import get_backends, login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import reverse
from django.views import View
from django.views.generic import TemplateView

from accounts.constants import ROLE_CLIENT, ROLE_THERAPIST
from accounts.forms import PhoneAuthenticationForm
from accounts.services import (
    get_role_home_url,
    get_safe_next_url,
    get_user_roles,
    infer_role_from_next,
    role_to_label,
    set_active_role,
    user_has_role,
)
from therapist_panel.constants import THERAPIST_TIMEZONE_CHOICES


class RoleAwareLoginView(LoginView):
    """Single login entry for all users with role-aware redirects."""

    template_name = "accounts/login.html"
    authentication_form = PhoneAuthenticationForm

    def form_valid(self, form):
        user = form.get_user()
        backend = getattr(user, "backend", None)
        if backend is None:
            backends = list(get_backends())
            if not backends:
                raise ValueError("No authentication backends are configured.")
            backend = f"{backends[0].__module__}.{backends[0].__class__.__name__}"
        login(self.request, user, backend=backend)
        self.request.user = user
        self.user = user
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        request = self.request
        user = getattr(self, "user", request.user)
        next_url = get_safe_next_url(request)
        roles = get_user_roles(user)

        inferred_role = infer_role_from_next(next_url) if next_url else None
        if inferred_role and user_has_role(user, inferred_role):
            set_active_role(request, inferred_role)
            return next_url

        if len(roles) == 1:
            role = roles[0]
            set_active_role(request, role)
            if next_url and inferred_role not in (None, role):
                next_url = None
            return next_url or get_role_home_url(role)

        if len(roles) > 1:
            set_active_role(request, None)
            selection_url = reverse("accounts:select_role")
            if next_url:
                selection_url = f"{selection_url}?{urlencode({'next': next_url})}"
            return selection_url

        # No roles associated; fall back to default redirect
        set_active_role(request, None)
        return next_url or super().get_success_url()


class RoleSelectionView(LoginRequiredMixin, TemplateView):
    """Allow users with multiple roles to choose the active one."""

    template_name = "accounts/select_role.html"

    def dispatch(self, request, *args, **kwargs):
        roles = get_user_roles(request.user)
        next_url = get_safe_next_url(request)

        if len(roles) <= 1:
            role = roles[0] if roles else None
            if role:
                set_active_role(request, role)
                target = next_url or get_role_home_url(role)
                return redirect(target)

            set_active_role(request, None)
            return redirect("accounts:login")

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        request = self.request
        roles = get_user_roles(request.user)
        context.update(
            {
                "roles": [
                    {
                        "key": role,
                        "label": role_to_label(role),
                    }
                    for role in roles
                ],
                "next": get_safe_next_url(request),
            }
        )
        return context

    def post(self, request, *args, **kwargs):
        role = request.POST.get("role")
        if role not in (ROLE_CLIENT, ROLE_THERAPIST):
            raise Http404("Unknown role")
        if not user_has_role(request.user, role):
            raise PermissionDenied("You do not have this role.")

        set_active_role(request, role)
        next_url = get_safe_next_url(request)
        inferred_role = infer_role_from_next(next_url) if next_url else None

        if next_url and (inferred_role in (None, role)):
            return redirect(next_url)

        return redirect(get_role_home_url(role))


class SwitchRoleView(LoginRequiredMixin, View):
    """Switch the active role and redirect to an appropriate destination."""

    def post(self, request, role: str):
        if role not in (ROLE_CLIENT, ROLE_THERAPIST):
            raise Http404("Unknown role")
        if not user_has_role(request.user, role):
            raise PermissionDenied("You do not have this role.")

        set_active_role(request, role)
        next_url = get_safe_next_url(request)
        inferred_role = infer_role_from_next(next_url) if next_url else None

        if next_url and (inferred_role in (None, role)):
            return redirect(next_url)

        return redirect(get_role_home_url(role))


class TherapistRegistrationView(TemplateView):
    """Render the SMS-based therapist registration flow."""

    template_name = "accounts/register.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "send_code_url": reverse("therapist_panel:api:registration:send_code"),
                "verify_code_url": reverse("therapist_panel:api:registration:verify_code"),
                "complete_url": reverse("therapist_panel:api:registration:complete"),
                "timezone_choices": THERAPIST_TIMEZONE_CHOICES,
            }
        )
        return context


__all__ = [
    "RoleAwareLoginView",
    "RoleSelectionView",
    "SwitchRoleView",
    "TherapistRegistrationView",
]
