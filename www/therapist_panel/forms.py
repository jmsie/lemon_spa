"""Forms for therapist panel interactions."""

from django import forms

from therapist_panel.constants import THERAPIST_TIMEZONE_CHOICES
from therapist_panel.models import Therapist


class TherapistProfileForm(forms.ModelForm):
    """Allow therapists to update contact information and email."""

    email = forms.EmailField(label="Email")
    phone_number = forms.CharField(label="Phone number", max_length=32)
    timezone = forms.ChoiceField(label="Timezone", choices=THERAPIST_TIMEZONE_CHOICES)

    class Meta:
        model = Therapist
        fields = ["nickname", "address", "timezone"]
        labels = {
            "nickname": "Nickname",
            "address": "Address",
            "timezone": "Timezone",
        }

    def __init__(self, *args, user, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        self.fields["email"].initial = user.email
        self.fields["phone_number"].initial = user.phone_number
        self.fields["nickname"].widget.attrs.setdefault("placeholder", "Preferred display name")
        self.fields["address"].widget.attrs.setdefault("placeholder", "Mailing address")
        for field in self.fields.values():
            css_classes = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = f"{css_classes} form-control".strip()
        self.fields["phone_number"].widget.attrs.setdefault("placeholder", "e.g. +1 555 123 4567")

    def save(self, commit: bool = True):
        therapist = super().save(commit=commit)
        new_email = self.cleaned_data.get("email", "").strip()
        new_phone = self.cleaned_data.get("phone_number", "").strip()
        changed_fields: list[str] = []

        if new_email and new_email != self.user.email:
            self.user.email = new_email
            changed_fields.append("email")

        if new_phone and new_phone != self.user.phone_number:
            self.user.phone_number = new_phone
            changed_fields.append("phone_number")

        if not self.user.first_name and not self.user.last_name:
            nickname = self.cleaned_data.get("nickname", "").strip()
            if nickname:
                self.user.first_name = nickname
                self.user.last_name = ""
                changed_fields.extend(["first_name", "last_name"])

        if commit and changed_fields:
            # Remove duplicates while preserving order for update_fields.
            deduped: list[str] = []
            seen: set[str] = set()
            for field in changed_fields:
                if field not in seen:
                    deduped.append(field)
                    seen.add(field)
            self.user.save(update_fields=deduped)
        return therapist


class AppointmentSearchForm(forms.Form):
    """Filter appointments by customer information and date range."""

    customer_phone = forms.CharField(label="手機", required=False, max_length=32)
    customer_name = forms.CharField(label="姓名", required=False, max_length=150)
    start_date = forms.DateField(
        label="開始日期",
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    end_date = forms.DateField(
        label="結束日期",
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        placeholders = {
            "customer_phone": "輸入客戶手機",
            "customer_name": "輸入客戶姓名",
        }
        for name, field in self.fields.items():
            css_classes = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = f"{css_classes} form-control".strip()
            if name in placeholders:
                field.widget.attrs.setdefault("placeholder", placeholders[name])

    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get("start_date")
        end = cleaned_data.get("end_date")
        if start and end and end < start:
            self.add_error("end_date", "結束日期需在開始日期之後")
        return cleaned_data
