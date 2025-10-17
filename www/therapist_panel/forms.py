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
