"""Forms for therapist panel interactions."""

from django import forms

from therapist_panel.constants import THERAPIST_TIMEZONE_CHOICES
from therapist_panel.models import Therapist


class TherapistProfileForm(forms.ModelForm):
    """Allow therapists to update contact information and email."""

    email = forms.EmailField(label="Email")
    timezone = forms.ChoiceField(label="Timezone", choices=THERAPIST_TIMEZONE_CHOICES)

    class Meta:
        model = Therapist
        fields = ["nickname", "phone_number", "timezone"]
        labels = {
            "nickname": "Nickname",
            "phone_number": "Phone number",
            "timezone": "Timezone",
        }

    def __init__(self, *args, user, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        self.fields["email"].initial = user.email
        for field in self.fields.values():
            css_classes = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = f"{css_classes} form-control".strip()
        self.fields["phone_number"].widget.attrs.setdefault("placeholder", "e.g. +1 555 123 4567")

    def save(self, commit: bool = True):
        therapist = super().save(commit=commit)
        new_email = self.cleaned_data.get("email", "").strip()
        if new_email and new_email != self.user.email:
            self.user.email = new_email
            if commit:
                self.user.save(update_fields=["email"])
        return therapist
