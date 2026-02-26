"""Forms for reviewing and editing Hansard mention AI analysis."""

from django import forms

from hansard.models import HansardMention

MENTION_TYPE_CHOICES = [
    ("BUDGET", "Budget / Funding"),
    ("QUESTION", "Parliamentary Question"),
    ("POLICY", "Policy Discussion"),
    ("COMMITMENT", "Commitment / Pledge"),
    ("THROWAWAY", "Throwaway / Passing"),
    ("OTHER", "Other"),
]

SENTIMENT_CHOICES = [
    ("ADVOCATING", "Advocating"),
    ("DEFLECTING", "Deflecting"),
    ("PROMISING", "Promising"),
    ("NEUTRAL", "Neutral"),
    ("CRITICAL", "Critical"),
]

CHANGE_INDICATOR_CHOICES = [
    ("NEW", "New"),
    ("REPEAT", "Repeat"),
    ("ESCALATION", "Escalation"),
    ("REVERSAL", "Reversal"),
]

SIGNIFICANCE_CHOICES = [(i, str(i)) for i in range(1, 6)]


class MentionReviewForm(forms.ModelForm):
    """Form for editing AI analysis fields on a HansardMention."""

    mention_type = forms.ChoiceField(
        choices=[("", "---")] + MENTION_TYPE_CHOICES, required=False,
    )
    sentiment = forms.ChoiceField(
        choices=[("", "---")] + SENTIMENT_CHOICES, required=False,
    )
    change_indicator = forms.ChoiceField(
        choices=[("", "---")] + CHANGE_INDICATOR_CHOICES, required=False,
    )
    significance = forms.TypedChoiceField(
        choices=[("", "---")] + SIGNIFICANCE_CHOICES,
        coerce=int, empty_value=None, required=False,
    )

    class Meta:
        model = HansardMention
        fields = [
            "mp_name", "mp_constituency", "mp_party",
            "mention_type", "significance", "sentiment",
            "change_indicator", "ai_summary", "review_notes",
        ]
        widgets = {
            "mp_name": forms.TextInput(attrs={"class": "form-input"}),
            "mp_constituency": forms.TextInput(attrs={"class": "form-input"}),
            "mp_party": forms.TextInput(attrs={"class": "form-input"}),
            "ai_summary": forms.Textarea(attrs={"class": "form-input", "rows": 3}),
            "review_notes": forms.Textarea(attrs={"class": "form-input", "rows": 2}),
        }
