"""Admin configuration for the custom AccountUser model."""

from __future__ import annotations

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _

from accounts.models import AccountUser


@admin.register(AccountUser)
class AccountUserAdmin(UserAdmin):
    """Expose AccountUser fields in the Django admin."""

    fieldsets = (
        (None, {"fields": ("username", "password")}),
        (_("Personal info"), {"fields": ("first_name", "last_name", "email", "phone_number")}),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "username",
                    "phone_number",
                    "password1",
                    "password2",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
    )
    list_display = ("username", "phone_number", "email", "first_name", "last_name", "is_staff")
    search_fields = ("username", "phone_number", "first_name", "last_name", "email")
    ordering = ("username",)
