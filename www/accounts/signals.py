"""Signal handlers for synchronising user role groups."""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from accounts.constants import ROLE_CLIENT, ROLE_THERAPIST
from accounts.roles import ensure_default_groups
from accounts.services import user_has_role
from client_dashboard.models import Client
from therapist_panel.models import Therapist

User = get_user_model()


def _sync_role_groups(user: User) -> None:
    client_group, therapist_group = ensure_default_groups()

    if user_has_role(user, ROLE_CLIENT):
        user.groups.add(client_group)
    else:
        user.groups.remove(client_group)

    if user_has_role(user, ROLE_THERAPIST):
        user.groups.add(therapist_group)
    else:
        user.groups.remove(therapist_group)


@receiver(post_save, sender=Therapist)
def therapist_saved(sender, instance: Therapist, **_: object) -> None:
    _sync_role_groups(instance.user)


@receiver(post_delete, sender=Therapist)
def therapist_deleted(sender, instance: Therapist, **_: object) -> None:
    user = User.objects.filter(pk=instance.user_id).first()
    if user:
        _sync_role_groups(user)


@receiver(post_save, sender=Client)
def client_saved(sender, instance: Client, **_: object) -> None:
    _sync_role_groups(instance.user)


@receiver(post_delete, sender=Client)
def client_deleted(sender, instance: Client, **_: object) -> None:
    user = User.objects.filter(pk=instance.user_id).first()
    if user:
        _sync_role_groups(user)
