"""App configuration for accounts."""

from django.apps import AppConfig
from django.db.utils import OperationalError, ProgrammingError


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "accounts"
    verbose_name = "Accounts"

    def ready(self) -> None:  # noqa: D401 - hook for signals
        """Connect signals and ensure default role groups exist."""

        from accounts.roles import ensure_default_groups
        from . import signals  # noqa: F401  # pylint: disable=unused-import

        try:
            ensure_default_groups()
        except (ProgrammingError, OperationalError):
            # Database tables might not be ready during migrations.
            pass
