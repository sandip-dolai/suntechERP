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
            "purchase_order": forms.Select(
                attrs={"class": "form-control po-select select2"}
            ),
            "po_process": forms.Select(
                attrs={"class": "form-control po-process-select select2"}
            ),
            "indent_date": forms.DateInput(
                attrs={"type": "date", "class": "form-control"}
            ),
            "remarks": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["po_process"].queryset = POProcess.objects.none()

        # 🔑 HANDLE POST (CREATE)
        if self.data.get("purchase_order"):
            po_id = self.data.get("purchase_order")
            self.fields["po_process"].queryset = POProcess.objects.filter(
                purchase_order_id=po_id,
                department_process_id__in=INDENT_PROCESS_IDS,
                department_process__department="Production",
            )

        # 🔑 HANDLE EDIT
        elif self.instance.pk:
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
            "purchase_order_item": forms.Select(
                attrs={"class": "form-control po-item-select"}
            ),
            "required_quantity": forms.NumberInput(
                attrs={"step": "0.001", "class": "form-control"}
            ),
            "uom": forms.TextInput(attrs={"class": "form-control"}),
            "remarks": forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        self.purchase_order = kwargs.pop("purchase_order", None)
        super().__init__(*args, **kwargs)

        # 🔑 HANDLE POST (CREATE + UPDATE)
        if self.data.get("purchase_order"):
            po_id = self.data.get("purchase_order")
            qs = PurchaseOrderItem.objects.filter(purchase_order_id=po_id)

        # 🔑 HANDLE EDIT (initial load)
        elif self.purchase_order:
            qs = PurchaseOrderItem.objects.filter(purchase_order=self.purchase_order)

        else:
            qs = PurchaseOrderItem.objects.none()

        self.fields["purchase_order_item"].queryset = qs
        self.fields["purchase_order_item"].label_from_instance = (
            lambda obj: obj.material_description
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
    extra=1,
    can_delete=True,
)
