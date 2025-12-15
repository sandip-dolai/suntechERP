from django import forms
from .models import ItemMaster, CompanyMaster, ProcessStatusMaster, DepartmentProcessMaster


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


class DepartmentProcessMasterForm(forms.ModelForm):
    class Meta:
        model = DepartmentProcessMaster
        fields = ["department", "name", "is_active"]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "Enter process name"}),
        }