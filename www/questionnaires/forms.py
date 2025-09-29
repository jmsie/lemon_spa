"""Forms for collecting service questionnaires."""

from __future__ import annotations

from django import forms

from questionnaires.models import Questionnaire


class QuestionnaireForm(forms.ModelForm):
    """Allow clients to provide feedback for a completed appointment."""

    class Meta:
        model = Questionnaire
        fields = ["rating", "comment"]
        labels = {
            "rating": "本次服務滿意度",
            "comment": "其他建議或回饋",
        }
        widgets = {
            "rating": forms.RadioSelect(),
            "comment": forms.Textarea(attrs={"rows": 4, "placeholder": "歡迎留下您對療程的建議。"}),
        }
        help_texts = {
            "rating": "1 星為最不滿意，5 星為最滿意。",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["rating"].widget.attrs.setdefault("class", "rating-field")
        self.fields["comment"].widget.attrs.setdefault("class", "form-control")
