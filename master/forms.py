from django import forms
from .models import (
    # ItemMaster,
    CompanyMaster,
    ProcessStatusMaster,
    DepartmentProcessMaster,
)


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
        fields = ["name", "color_code", "is_active"]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter status name (e.g. COMPLETED)",
                }
            ),
            "color_code": forms.TextInput(
                attrs={
                    "type": "color",
                    "class": "form-control",
                    "title": "Choose status color",
                }
            ),
            "is_active": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input",
                }
            ),
        }


class DepartmentProcessMasterForm(forms.ModelForm):
    class Meta:
        model = DepartmentProcessMaster
        fields = ["department", "name", "is_active"]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "Enter process name"}),
        }
