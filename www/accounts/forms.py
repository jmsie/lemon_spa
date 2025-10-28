"""Authentication forms for the accounts app."""

from __future__ import annotations

from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.utils.translation import gettext_lazy as _

from phone_verification.exceptions import InvalidPhoneNumber
from phone_verification.utils import normalize_phone_number


class PhoneAuthenticationForm(AuthenticationForm):
    """Login form that accepts a phone number instead of a username."""

    username = forms.CharField(
        label=_("Phone number"),
        max_length=32,
        widget=forms.TextInput(
            attrs={
                "autofocus": True,
                "placeholder": "+886 900 000 000",
                "autocomplete": "tel",
            }
        ),
    )

    def clean(self):
        super().clean()

        phone_input = self.cleaned_data.get(self.username_field)
        password = self.cleaned_data.get("password")

        if phone_input and password:
            try:
                normalized_phone = normalize_phone_number(phone_input)
            except InvalidPhoneNumber:
                raise forms.ValidationError(
                    _("請輸入正確的手機號碼。"),
                    code="invalid_phone_number",
                )

            phone_user = authenticate(
                self.request,
                phone_number=normalized_phone,
                password=password,
            )

            fallback_user = None
            if phone_user is None:
                # Fall back to username authentication in case legacy accounts still exist.
                fallback_user = authenticate(
                    self.request,
                    username=normalized_phone,
                    password=password,
                )

            user = phone_user or fallback_user
            if user is None:
                raise self.get_invalid_login_error()

            self.confirm_login_allowed(user)
            if phone_user is not None:
                user.backend = "accounts.backends.PhoneNumberBackend"
            elif fallback_user is not None and not getattr(user, "backend", None):
                user.backend = fallback_user.backend  # pragma: no cover - mirrors Django's logic
            self.user_cache = user
            self.cleaned_data[self.username_field] = normalized_phone

        return self.cleaned_data
