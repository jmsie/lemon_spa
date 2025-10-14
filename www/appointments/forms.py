"""Forms for public appointment booking."""

from __future__ import annotations

from functools import lru_cache
from typing import Iterable

import phonenumbers
from django import forms
from phonenumbers import PhoneNumberFormat
from phonenumbers.phonenumberutil import NumberParseException

from appointments.models import Appointment
from therapist_panel.models import Therapist, TherapistTreatment


@lru_cache(maxsize=1)
def _country_choices() -> list[tuple[str, str]]:
    """Return a list of (region, label) tuples for all supported regions."""

    regions: Iterable[str] = sorted(phonenumbers.SUPPORTED_REGIONS)
    choices: list[tuple[str, str]] = []
    for region in regions:
        country_code = phonenumbers.country_code_for_region(region)
        if not country_code:
            continue
        label = f"+{country_code} ({region})"
        choices.append((region, label))
    return choices


class AppointmentForm(forms.ModelForm):
    """Collect appointment details from public visitors."""

    EXCLUDED_VISIBLE_FIELDS = {
        "start_time",
        "treatment",
        "customer_phone",
        "customer_phone_region",
        "customer_phone_national",
    }

    start_time = forms.DateTimeField(
        label="開始時間",
        widget=forms.HiddenInput(),
        input_formats=[
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M",
            "%Y-%m-%dT%H:%M:%S",
        ],
    )
    customer_phone_region = forms.ChoiceField(
        label="國家/地區",
        choices=_country_choices(),
        initial="TW",
    )
    customer_phone_national = forms.CharField(
        label="電話號碼",
        max_length=32,
    )

    class Meta:
        model = Appointment
        fields = [
            "therapist",
            "treatment",
            "start_time",
            "customer_name",
            "customer_phone",
            "customer_phone_region",
            "customer_phone_national",
            "note",
        ]
        labels = {
            "therapist": "按摩師",
            "treatment": "療程",
            "customer_name": "顧客姓名",
            "customer_phone": "顧客電話",
            "note": "備註",
        }
        widgets = {
            "note": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["therapist"].queryset = Therapist.objects.order_by("nickname", "first_name", "last_name")
        self.fields["treatment"].queryset = (
            TherapistTreatment.objects.filter(is_active=True).select_related("therapist").order_by("name")
        )
        self.fields["customer_name"].widget.attrs.setdefault("placeholder", "您的大名")
        self.fields["customer_phone"].widget = forms.HiddenInput()
        self.fields["customer_phone"].required = False
        self.fields["customer_phone_region"].widget.attrs.setdefault("aria-label", "國碼")
        self.fields["customer_phone_national"].widget.attrs.setdefault("placeholder", "手機號碼")

        if not self.is_bound:
            existing = self.initial.get("customer_phone") or getattr(self.instance, "customer_phone", "")
            if existing:
                try:
                    parsed = phonenumbers.parse(existing, None)
                except NumberParseException:
                    parsed = None
                if parsed and phonenumbers.is_valid_number(parsed):
                    region = phonenumbers.region_code_for_number(parsed) or self.fields["customer_phone_region"].initial
                    national_number = str(parsed.national_number)
                    self.initial.setdefault("customer_phone_region", region)
                    self.fields["customer_phone_region"].initial = region
                    self.initial.setdefault("customer_phone_national", national_number)
                    self.fields["customer_phone_national"].initial = national_number

    def clean(self):
        cleaned_data = super().clean()
        therapist = cleaned_data.get("therapist")
        treatment = cleaned_data.get("treatment")
        if therapist and treatment and treatment.therapist_id != therapist.id:
            self.add_error("treatment", "選擇的療程不屬於此按摩師。")

        region = cleaned_data.get("customer_phone_region")
        national = (cleaned_data.get("customer_phone_national") or "").strip()

        if region and national:
            try:
                parsed = phonenumbers.parse(national, region)
            except NumberParseException as exc:
                self.add_error("customer_phone_national", "請輸入正確的電話號碼。")
            else:
                if not phonenumbers.is_valid_number(parsed):
                    self.add_error("customer_phone_national", "請輸入正確的電話號碼。")
                else:
                    cleaned_data["customer_phone"] = phonenumbers.format_number(parsed, PhoneNumberFormat.E164)
        elif not national and "customer_phone_national" not in self.errors:
            self.add_error("customer_phone_national", "請輸入電話號碼。")

        return cleaned_data

    def remaining_visible_fields(self):
        """Yield visible fields that are not rendered manually."""

        for bound_field in self.visible_fields():
            if bound_field.name in self.EXCLUDED_VISIBLE_FIELDS:
                continue
            yield bound_field
