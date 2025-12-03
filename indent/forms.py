from django import forms
from .models import Indent

class IndentForm(forms.ModelForm):
    class Meta:
        model = Indent
        fields = ['bom', 'indent_number', 'indent_date', 'required_date', 'status']
        widgets = {
            'bom': forms.Select(attrs={'class': 'form-control'}),
            'indent_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter indent number'}),
            'indent_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'required_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'status': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter status'}),
        }
