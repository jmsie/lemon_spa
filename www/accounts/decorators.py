"""Decorators for enforcing active role requirements."""

from __future__ import annotations

from functools import wraps
from urllib.parse import urlencode

from django.contrib.auth.decorators import login_required
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


def _redirect_to_role_selection(request, role: str):
    selection_url = reverse("accounts:select_role")
    next_url = request.get_full_path()
    if next_url:
        selection_url = f"{selection_url}?{urlencode({'next': next_url})}"
    return redirect(selection_url)


def role_required(role: str):
    """Ensure the user owns the specified role and has it active."""

    def decorator(view_func):
        @login_required
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            reset_active_role_if_missing(request)
            if not user_has_role(request.user, role):
                raise PermissionDenied("You do not have access to this area.")
            active_role = get_active_role(request)
            if active_role != role:
                roles = get_user_roles(request.user)
                if len(roles) == 1 and role in roles:
                    set_active_role(request, role)
                else:
                    return _redirect_to_role_selection(request, role)
            return view_func(request, *args, **kwargs)

        return _wrapped

    return decorator


therapist_role_required = role_required(ROLE_THERAPIST)
client_role_required = role_required(ROLE_CLIENT)
