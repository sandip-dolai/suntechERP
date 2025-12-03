from django import forms
from .models import BillOfMaterials

class BillOfMaterialsForm(forms.ModelForm):
    class Meta:
        model = BillOfMaterials
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.item:
            self.fields['unit'].initial = self.instance.item.uom