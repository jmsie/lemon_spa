"""Forms for public appointment booking."""

from __future__ import annotations

from django import forms

from appointments.models import Appointment
from therapist_panel.models import Therapist, TherapistTreatment


class AppointmentForm(forms.ModelForm):
    """Collect appointment details from public visitors."""

    start_time = forms.DateTimeField(
        label="開始時間",
        widget=forms.HiddenInput(),
        input_formats=[
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M",
            "%Y-%m-%dT%H:%M:%S",
        ],
    )

    class Meta:
        model = Appointment
        fields = [
            "therapist",
            "treatment",
            "start_time",
            "customer_name",
            "customer_phone",
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
        self.fields["customer_phone"].widget.attrs.setdefault("placeholder", "聯絡電話")

    def clean(self):
        cleaned_data = super().clean()
        therapist = cleaned_data.get("therapist")
        treatment = cleaned_data.get("treatment")
        if therapist and treatment and treatment.therapist_id != therapist.id:
            self.add_error("treatment", "選擇的療程不屬於此按摩師。")

        return cleaned_data
