"""Helpers for working with user roles and session state."""

from __future__ import annotations

from urllib.parse import urlparse

from django.core.exceptions import ObjectDoesNotExist
from django.urls import Resolver404, resolve, reverse
from django.utils.http import url_has_allowed_host_and_scheme

from accounts.constants import ROLE_CLIENT, ROLE_THERAPIST, ROLE_LABELS, SESSION_ACTIVE_ROLE_KEY


def _has_profile(user, accessor: str) -> bool:
    try:
        getattr(user, accessor)
    except (ObjectDoesNotExist, AttributeError):
        return False
    return True


def get_user_roles(user) -> list[str]:
    roles: list[str] = []
    if _has_profile(user, "therapist_profile"):
        roles.append(ROLE_THERAPIST)
    if _has_profile(user, "client_profile"):
        roles.append(ROLE_CLIENT)
    return roles


def user_has_role(user, role: str) -> bool:
    if role == ROLE_THERAPIST:
        return _has_profile(user, "therapist_profile")
    if role == ROLE_CLIENT:
        return _has_profile(user, "client_profile")
    return False


def get_active_role(request) -> str | None:
    return request.session.get(SESSION_ACTIVE_ROLE_KEY)


def set_active_role(request, role: str | None) -> None:
    if role is None:
        request.session.pop(SESSION_ACTIVE_ROLE_KEY, None)
    else:
        request.session[SESSION_ACTIVE_ROLE_KEY] = role


def role_to_label(role: str) -> str:
    return ROLE_LABELS.get(role, role.title())


def ensure_role_is_available(user, role: str) -> None:
    if not user_has_role(user, role):
        raise PermissionError(f"User does not have role: {role}")


def reset_active_role_if_missing(request) -> None:
    active = get_active_role(request)
    if active and not user_has_role(request.user, active):
        set_active_role(request, None)


def resolve_role_from_path(path: str) -> str | None:
    try:
        match = resolve(path)
    except Resolver404:
        return None

    namespaces = set(match.namespaces)
    if "therapist_panel" in namespaces:
        return ROLE_THERAPIST
    if "client_dashboard" in namespaces:
        return ROLE_CLIENT
    return None


def get_role_home_url(role: str) -> str:
    if role == ROLE_THERAPIST:
        return reverse("therapist_panel:index")
    if role == ROLE_CLIENT:
        return reverse("client_dashboard:index")
    raise ValueError(f"Unknown role: {role}")


def get_safe_next_url(request) -> str | None:
    next_param = request.POST.get("next") or request.GET.get("next")
    if not next_param:
        return None
    if url_has_allowed_host_and_scheme(next_param, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        return next_param
    return None


def infer_role_from_next(next_url: str) -> str | None:
    if not next_url:
        return None
    path = urlparse(next_url).path
    return resolve_role_from_path(path)
