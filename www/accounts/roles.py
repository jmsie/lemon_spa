"""Role helpers for accounts app."""

from django.contrib.auth.models import Group
from django.db import transaction

from accounts.constants import ROLE_CLIENT, ROLE_LABELS, ROLE_THERAPIST


@transaction.atomic
def ensure_default_groups() -> tuple[Group, Group]:
    """Return groups representing client and therapist roles."""

    client_group, _ = Group.objects.get_or_create(name=ROLE_LABELS[ROLE_CLIENT])
    therapist_group, _ = Group.objects.get_or_create(name=ROLE_LABELS[ROLE_THERAPIST])
    return client_group, therapist_group
