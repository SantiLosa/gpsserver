from django import forms


class BulkUploadForm(forms.Form):
    data = forms.CharField(
        widget=forms.Textarea(
            attrs={
                "rows": 15,
                "cols": 120,
                "placeholder": "Paste your $IGX frames here, one per line",
            }
        ),
        label="Frames",
    )
