# po/forms.py
from django import forms
from .models import PurchaseOrder
from master.models import CompanyMaster
import datetime

class PurchaseOrderForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrder
        fields = [
            'po_number',
            'po_date',
            'company',
            'material_description',
            'quantity',
            'delivery_date',
            'status',
        ]
        widgets = {
            'po_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. PO-2025-001'
            }),
            'po_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),

            'company': forms.Select(attrs={
                'class': 'form-control',
            }),
            'material_description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'e.g. 50 units of 2-inch steel pipes, grade A'
            }),
            'quantity': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. 10 pcs, 5 kg, 2 boxes'
            }),
            'delivery_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
            'status': forms.Select(attrs={
                'class': 'form-select'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # 1. Order companies by code/name
        self.fields['company'].queryset = CompanyMaster.objects.order_by('name')
        self.fields['company'].empty_label = "— Select Company —"

        # 2. Use readable status choices
        self.fields['status'].choices = PurchaseOrder.STATUS_CHOICES

        # 3. Add help text
        self.fields['quantity'].help_text = "Include unit (e.g. pcs, kg, boxes)"
        self.fields['material_description'].help_text = "Describe what is being purchased"
        
        # 4. Set default date to today
        self.fields['po_date'].initial = datetime.date.today()