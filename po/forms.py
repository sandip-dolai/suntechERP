from django import forms
from django.forms import inlineformset_factory
from .models import PurchaseOrder, PurchaseOrderItem
from master.models import CompanyMaster
import datetime


# ------------------------------
# PURCHASE ORDER HEADER FORM
# ------------------------------
class PurchaseOrderForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrder
        fields = [
            'po_number',
            'po_date',
            'oa_number',
            'company',
            'delivery_date',
        ]
        widgets = {
            'po_number': forms.TextInput(attrs={'class': 'form-control'}),
            'po_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'oa_number': forms.TextInput(attrs={'class': 'form-control'}),
            'company': forms.Select(attrs={'class': 'form-select'}),
            'delivery_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['company'].queryset = CompanyMaster.objects.order_by('name')
        self.fields['company'].empty_label = "— Select Company —"

        if not self.instance.pk:
            self.fields['po_date'].initial = datetime.date.today()


# ------------------------------
# PURCHASE ORDER ITEM FORM
# ------------------------------
class PurchaseOrderItemForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrderItem
        fields = ['material_description', 'quantity', 'status']
        widgets = {
            'material_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'quantity': forms.TextInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-select'})
        }


# ------------------------------
# PURCHASE ORDER ITEM FORMSET
# ------------------------------
PurchaseOrderItemFormSet = inlineformset_factory(
    PurchaseOrder,
    PurchaseOrderItem,
    form=PurchaseOrderItemForm,
    extra=1,
    can_delete=True
)
