from django import forms
from django.utils import timezone

from .serializers import APPLICATION_STATUSES


class ApplicationForm(forms.Form):
    company = forms.CharField(max_length=120)
    role = forms.CharField(max_length=120)
    job_link = forms.URLField(required=False)
    notes = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': 4}))
    job_description = forms.CharField(
        required=False,
        max_length=20000,
        widget=forms.Textarea(attrs={'rows': 8, 'placeholder': 'Paste the job description here'}),
    )
    date_applied = forms.DateField(
        initial=timezone.localdate,
        widget=forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
    )
    status = forms.ChoiceField(choices=[(value, value) for value in APPLICATION_STATUSES])

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-select' if isinstance(field.widget, forms.Select) else 'form-control'
