from django import forms
from .models import ItemMaster, CompanyMaster, ProcessStatusMaster


class ItemMasterForm(forms.ModelForm):
    class Meta:
        model = ItemMaster
        fields = "__all__"
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
        }


class CompanyMasterForm(forms.ModelForm):
    class Meta:
        model = CompanyMaster
        fields = "__all__"
        widgets = {
            "address": forms.Textarea(attrs={"rows": 3}),
        }


class ProcessStatusMasterForm(forms.ModelForm):
    class Meta:
        model = ProcessStatusMaster
        fields = "__all__"
