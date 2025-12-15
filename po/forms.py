from django import forms
from django.forms import inlineformset_factory
from .models import PurchaseOrder, PurchaseOrderItem, POProcess, POProcessHistory
from master.models import CompanyMaster, ProcessStatusMaster
import datetime


# ------------------------------
# PURCHASE ORDER HEADER FORM
# ------------------------------
class PurchaseOrderForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrder
        fields = [
            "po_number",
            "po_date",
            "oa_number",
            "company",
            "delivery_date",
        ]
        widgets = {
            "po_number": forms.TextInput(attrs={"class": "form-control"}),
            "po_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "oa_number": forms.TextInput(attrs={"class": "form-control"}),
            "company": forms.Select(attrs={"class": "form-select"}),
            "delivery_date": forms.DateInput(
                attrs={"type": "date", "class": "form-control"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["company"].queryset = CompanyMaster.objects.order_by("name")
        self.fields["company"].empty_label = "— Select Company —"

        if not self.instance.pk:
            self.fields["po_date"].initial = datetime.date.today()


# ------------------------------
# PURCHASE ORDER ITEM FORM
# ------------------------------
class PurchaseOrderItemForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrderItem
        fields = ["material_description", "quantity", "status"]
        widgets = {
            "material_description": forms.Textarea(
                attrs={"class": "form-control", "rows": 2}
            ),
            "quantity": forms.TextInput(attrs={"class": "form-control"}),
            "status": forms.Select(attrs={"class": "form-select"}),
        }


# ------------------------------
# PURCHASE ORDER ITEM FORMSET
# ------------------------------
PurchaseOrderItemFormSet = inlineformset_factory(
    PurchaseOrder,
    PurchaseOrderItem,
    form=PurchaseOrderItemForm,
    extra=1,
    can_delete=True,
)


# ------------------------------
# PO PROCESS UPDATE FORM
# ------------------------------
class POProcessUpdateForm(forms.ModelForm):
    """
    Form used by department users to update process status.
    """

    remark = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 2,
                "placeholder": "Add remark (optional)",
            }
        ),
        label="Remark",
    )

    class Meta:
        model = POProcess
        fields = ["current_status"]
        widgets = {
            "current_status": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        self.fields["current_status"].queryset = (
            ProcessStatusMaster.objects.filter(is_active=True)
        )

        if self.instance.pk:
            self.fields["current_status"].initial = self.instance.current_status


    def save(self, commit=True):
        if not self.user:
            raise ValueError("POProcessUpdateForm requires a user")

        po_process = super().save(commit=False)

        if commit:
            po_process.last_updated_by = self.user
            po_process.save()

            POProcessHistory.objects.create(
                po_process=po_process,
                status=po_process.current_status,
                remark=self.cleaned_data.get("remark", ""),
                changed_by=self.user,
            )

        return po_process


# ------------------------------
# PO PROCESS READONLY FORM
# ------------------------------
class POProcessReadonlyForm(forms.ModelForm):
    class Meta:
        model = POProcess
        fields = ["current_status"]
        widgets = {
            "current_status": forms.Select(
                attrs={"class": "form-select", "disabled": True}
            )
        }
