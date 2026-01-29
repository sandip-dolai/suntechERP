from django import forms
from django.forms import inlineformset_factory, BaseInlineFormSet

from .models import Indent, IndentItem
from po.models import PurchaseOrder, PurchaseOrderItem, POProcess

INDENT_PROCESS_IDS = [13, 18, 23]


class IndentForm(forms.ModelForm):
    class Meta:
        model = Indent
        fields = [
            "purchase_order",
            "po_process",
            "indent_date",
            "remarks",
        ]
        widgets = {
            "indent_date": forms.DateInput(
                attrs={"type": "date", "class": "form-control"}
            ),
            "remarks": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # UI consistency
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")

        # Default empty querysets (will be filtered via PO)
        self.fields["po_process"].queryset = POProcess.objects.filter(
            department_process_id__in=INDENT_PROCESS_IDS,
            department_process__department="Production",
        )

        if self.instance.pk:
            # Editing existing indent
            po = self.instance.purchase_order
            self.fields["po_process"].queryset = POProcess.objects.filter(
                purchase_order=po,
                department_process_id__in=INDENT_PROCESS_IDS,
                department_process__department="Production",
            )

    def clean(self):
        cleaned_data = super().clean()

        po = cleaned_data.get("purchase_order")
        po_process = cleaned_data.get("po_process")

        # 🔒 Block edits if indent is closed
        if self.instance.pk and self.instance.status == "CLOSED":
            raise forms.ValidationError("This indent is closed and cannot be modified.")

        # Validate PO Process belongs to PO
        if po and po_process:
            if po_process.purchase_order_id != po.id:
                raise forms.ValidationError(
                    "Selected process does not belong to the selected PO."
                )

            # Ensure Production-only process
            if po_process.department_process.department != "Production":
                raise forms.ValidationError(
                    "Indent can only be created for Production processes."
                )

        return cleaned_data


class IndentItemForm(forms.ModelForm):
    class Meta:
        model = IndentItem
        fields = [
            "purchase_order_item",
            "required_quantity",
            "uom",
            "remarks",
        ]
        widgets = {
            "purchase_order_item": forms.Select(attrs={"class": "form-control"}),
            "required_quantity": forms.NumberInput(
                attrs={"step": "0.001", "class": "form-control"}
            ),
            "uom": forms.TextInput(attrs={"class": "form-control"}),
            "remarks": forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        self.purchase_order = kwargs.pop("purchase_order", None)
        super().__init__(*args, **kwargs)

        if self.purchase_order:
            qs = PurchaseOrderItem.objects.filter(purchase_order=self.purchase_order)
            self.fields["purchase_order_item"].queryset = qs

            self.fields["purchase_order_item"].label_from_instance = (
                lambda obj: obj.material_description
            )
        else:
            self.fields["purchase_order_item"].queryset = (
                PurchaseOrderItem.objects.none()
            )

    def clean_required_quantity(self):
        qty = self.cleaned_data.get("required_quantity")

        if qty is None or qty <= 0:
            raise forms.ValidationError("Required quantity must be greater than zero.")

        return qty


class BaseIndentItemFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()

        valid_forms = [
            form
            for form in self.forms
            if form.cleaned_data and not form.cleaned_data.get("DELETE", False)
        ]

        if not valid_forms:
            raise forms.ValidationError("At least one indent item is required.")


IndentItemFormSet = inlineformset_factory(
    Indent,
    IndentItem,
    form=IndentItemForm,
    formset=BaseIndentItemFormSet,
    extra=0,
    can_delete=True,
)
