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
        fields = ["department", "name", "sequence", "is_active"]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "Enter process name"}),
            "sequence": forms.NumberInput(
                attrs={
                    "min": 1,
                    "placeholder": "Execution order (1, 2, 3...)",
                }
            ),
        }

    def clean_sequence(self):
        sequence = self.cleaned_data.get("sequence")

        if sequence is None:
            raise forms.ValidationError("Sequence is required.")

        if sequence <= 0:
            raise forms.ValidationError("Sequence must be a positive number.")

        qs = DepartmentProcessMaster.objects.filter(sequence=sequence)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise forms.ValidationError(
                f"Sequence {sequence} already exists. Choose a unique value."
            )

        return sequence
