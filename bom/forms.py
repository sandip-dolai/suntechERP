from django import forms
from .models import BillOfMaterials
from master.models import ItemMaster
from po.models import PurchaseOrder


class BillOfMaterialsForm(forms.ModelForm):
    class Meta:
        model = BillOfMaterials
        fields = ['po', 'item', 'quantity']

        widgets = {
            'po': forms.Select(attrs={'class': 'form-select'}),
            'item': forms.Select(attrs={'class': 'form-select'}),
            'quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.001',
                'min': '0.001',
                'placeholder': 'e.g. 12.5'
            }),
        }

    def __init__(self, *args, po=None, **kwargs):
        super().__init__(*args, **kwargs)

        # Lock PO if passed
        if po:
            self.fields['po'].queryset = PurchaseOrder.objects.filter(pk=po.pk)
            self.fields['po'].initial = po
            self.fields['po'].widget.attrs['disabled'] = True
            self.fields['po'].widget.attrs['style'] = 'display:none;'

        # Item dropdown
        self.fields['item'].queryset = ItemMaster.objects.order_by('code')
        self.fields['item'].empty_label = "— Select Item —"

        # Optional: Show current unit (read-only) when editing
        if self.instance.pk and self.instance.item:
            self.fields['item'].widget.attrs['data-unit'] = self.instance.item.uom

    def clean(self):
        cleaned_data = super().clean()
        item = cleaned_data.get('item')
        if item:
            cleaned_data['unit'] = item.uom  # Auto-fill
        return cleaned_data