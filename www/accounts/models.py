"""Custom user model for phone-based authentication."""

from __future__ import annotations

from typing import Any

from django.contrib.auth.models import AbstractUser, UserManager
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from phone_verification.exceptions import InvalidPhoneNumber
from phone_verification.utils import normalize_phone_number


class AccountUserManager(UserManager):
    """Manager that normalizes phone numbers during user creation and updates."""

    def normalize_phone(self, phone_number: str) -> str:
        if not phone_number:
            raise ValueError("The phone_number must be provided.")
        try:
            return normalize_phone_number(phone_number)
        except InvalidPhoneNumber as exc:  # pragma: no cover - defensive validation
            raise ValidationError({"phone_number": str(exc)}) from exc

    def _prepare_extra_fields(self, extra_fields: dict[str, Any]) -> dict[str, Any]:
        fields = extra_fields.copy()
        if "phone_number" in fields and fields["phone_number"]:
            fields["phone_number"] = self.normalize_phone(fields["phone_number"])
        return fields

    def _create_user(self, username: str, email: str | None, password: str | None, **extra_fields: Any):
        fields = self._prepare_extra_fields(extra_fields)
        phone_number = fields.get("phone_number")
        is_superuser = fields.get("is_superuser")
        if not phone_number and not is_superuser:
            raise ValueError("The phone_number must be provided.")
        if not username:
            username = phone_number
        if not username:
            raise ValueError("A username or phone_number must be provided.")
        return super()._create_user(username, email, password, **fields)

    def create_user(self, username: str | None = None, email: str | None = None, password: str | None = None, **extra_fields: Any):
        fields = self._prepare_extra_fields(extra_fields)
        return super().create_user(username or fields.get("phone_number"), email, password, **fields)

    def create_superuser(self, username: str | None = None, email: str | None = None, password: str | None = None, **extra_fields: Any):
        fields = self._prepare_extra_fields(extra_fields)
        return super().create_superuser(username or fields.get("phone_number"), email, password, **fields)


class AccountUser(AbstractUser):
    """User model that enforces globally unique phone numbers."""

    phone_number = models.CharField(
        max_length=32,
        unique=True,
        blank=True,
        null=True,
        help_text=_("Normalized phone number stored in E.164 format."),
    )

    objects = AccountUserManager()

    class Meta(AbstractUser.Meta):
        verbose_name = _("user")
        verbose_name_plural = _("users")

    def clean(self) -> None:
        super().clean()
        if self.phone_number:
            try:
                self.phone_number = normalize_phone_number(self.phone_number)
            except InvalidPhoneNumber as exc:
                raise ValidationError({"phone_number": str(exc)}) from exc

    def save(self, *args: Any, **kwargs: Any) -> None:
        if self.phone_number:
            try:
                self.phone_number = normalize_phone_number(self.phone_number)
            except InvalidPhoneNumber as exc:
                raise ValidationError({"phone_number": str(exc)}) from exc
        if not self.username and self.phone_number:
            self.username = self.phone_number
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.get_username()
