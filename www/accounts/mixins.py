"""Mixins enforcing active role requirements."""

from __future__ import annotations

from urllib.parse import urlencode

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.urls import reverse

from accounts.constants import ROLE_CLIENT, ROLE_THERAPIST
from accounts.services import (
    get_active_role,
    get_user_roles,
    reset_active_role_if_missing,
    set_active_role,
    user_has_role,
)


class RoleRequiredMixin(LoginRequiredMixin):
    """Ensure the user holds and actively selects a specific role."""

    required_role: str | None = None

    def dispatch(self, request, *args, **kwargs):
        if self.required_role is None:
            raise ValueError("RoleRequiredMixin requires `required_role` to be set.")

        if not request.user.is_authenticated:
            return self.handle_no_permission()

        reset_active_role_if_missing(request)

        if not user_has_role(request.user, self.required_role):
            raise PermissionDenied("You do not have access to this area.")

        active_role = get_active_role(request)
        if active_role != self.required_role:
            roles = get_user_roles(request.user)
            if len(roles) == 1 and self.required_role in roles:
                set_active_role(request, self.required_role)
            else:
                selection_url = reverse("accounts:select_role")
                next_url = request.get_full_path()
                if next_url:
                    selection_url = f"{selection_url}?{urlencode({'next': next_url})}"
                return redirect(selection_url)

        return super().dispatch(request, *args, **kwargs)


class TherapistRoleRequiredMixin(RoleRequiredMixin):
    required_role = ROLE_THERAPIST


class ClientRoleRequiredMixin(RoleRequiredMixin):
    required_role = ROLE_CLIENT
