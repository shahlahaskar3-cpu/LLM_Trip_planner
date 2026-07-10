from django import forms


class TripQueryForm(forms.Form):
    question = forms.CharField(
        label="Ask your travel question",
        widget=forms.Textarea(
            attrs={
                "rows": 3,
                "placeholder": "e.g. Plan a 5-day budget trip to Goa for 2 people",
                "class": "trip-input",
            }
        ),
        required=True,
    )