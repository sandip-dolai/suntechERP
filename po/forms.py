from django import forms
from django.forms import inlineformset_factory
from .models import PurchaseOrder, PurchaseOrderItem, POProcess, POProcessHistory
from master.models import CompanyMaster, ProcessStatusMaster
import datetime
from django.forms import BaseInlineFormSet


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
            "department",
            "po_status",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["company"].queryset = CompanyMaster.objects.order_by("name")
        self.fields["company"].empty_label = "— Select Company —"

        if not self.instance.pk:
            self.fields["po_date"].initial = datetime.date.today()
            self.fields["po_status"].required = False
            self.fields["po_status"].widget = forms.HiddenInput()


# ------------------------------
# PURCHASE ORDER ITEM FORM
# ------------------------------
class PurchaseOrderItemForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrderItem
        fields = [
            "material_code",
            "material_description",
            "quantity_value",
            "uom",
            "material_value",
        ]
        widgets = {
            "material_code": forms.TextInput(attrs={"class": "form-control"}),
            "material_description": forms.Textarea(
                attrs={"class": "form-control", "rows": 2}
            ),
            "quantity_value": forms.TextInput(attrs={"class": "form-control"}),
            "material_value": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
        }


# ------------------------------
# PURCHASE ORDER ITEM FORMSET
# ------------------------------
class BasePurchaseOrderItemFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()

        non_deleted_forms = [
            form
            for form in self.forms
            if form.cleaned_data and not form.cleaned_data.get("DELETE", False)
        ]

        if not non_deleted_forms:
            raise forms.ValidationError("At least one PO item is required.")


PurchaseOrderItemFormSet = inlineformset_factory(
    PurchaseOrder,
    PurchaseOrderItem,
    form=PurchaseOrderItemForm,
    formset=BasePurchaseOrderItemFormSet,
    extra=0,
    can_delete=True,
)


# ------------------------------
# PO COMPLETION LOGIC
# ------------------------------
def check_and_update_po_status(po):
    """
    Checks all processes for a PO (excluding excluded ones).
    If all are completed → set PO to COMPLETED.
    If any is not completed → set PO back to PENDING.
    Saves silently with no messages.
    """
    # Get all processes that count towards completion
    relevant_processes = po.processes.filter(
        department_process__excludes_from_completion=False
    )

    # Check if any relevant process is NOT completed
    all_completed = not relevant_processes.exclude(
        current_status__is_completed=True
    ).exists()

    # Update PO status accordingly
    new_status = "COMPLETED" if all_completed else "PENDING"

    if po.po_status != new_status:
        po.po_status = new_status
        po.save(update_fields=["po_status"])


# ------------------------------
# AUTO SET PROCESS STATUS BASED ON ITEMS
# ------------------------------
def auto_set_process_status(po_process):
    """
    For has_item_tracking=True processes only.
    If ALL PO items have is_completed=True status → set process status to COMPLETED.
    If ANY item is missing or non-completed → set process status to most recent item status.
    """
    from .models import POProcessItemStatus

    po_items = po_process.purchase_order.items.all()
    total_items = po_items.count()

    if total_items == 0:
        return

    item_statuses = POProcessItemStatus.objects.filter(
        po_process=po_process
    ).select_related("status")

    tracked_count = item_statuses.count()

    # Not all items tracked yet
    if tracked_count < total_items:
        latest = item_statuses.order_by("-updated_at").first()
        if latest:
            po_process.current_status = latest.status
            po_process.save(update_fields=["current_status"])
        return

    # Check if ALL items have completed status
    all_completed = not item_statuses.exclude(status__is_completed=True).exists()

    if all_completed:
        completed_status = ProcessStatusMaster.objects.filter(
            is_completed=True,
            is_active=True,
        ).first()
        if completed_status:
            po_process.current_status = completed_status
            po_process.save(update_fields=["current_status"])
    else:
        latest = item_statuses.order_by("-updated_at").first()
        if latest:
            po_process.current_status = latest.status
            po_process.save(update_fields=["current_status"])


# ------------------------------
# PO PROCESS UPDATE FORM
# ------------------------------
class POProcessUpdateForm(forms.ModelForm):
    """
    Form used by department users to update process status.
    Removed all hardcoded department_process_id logic.
    PO completion is now handled automatically via check_and_update_po_status().
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

        self.fields["current_status"].queryset = ProcessStatusMaster.objects.filter(
            is_active=True
        )

        if self.instance.pk:
            self.fields["current_status"].initial = self.instance.current_status

            # 👇 HIDE status dropdown if item tracking is enabled
            if self.instance.department_process.has_item_tracking:
                self.fields["current_status"].required = False
                self.fields["current_status"].widget = forms.HiddenInput()

    def save(self, commit=True):
        if not self.user:
            raise ValueError("POProcessUpdateForm requires a user")

        po_process = super().save(commit=False)

        if commit:
            po_process.last_updated_by = self.user

            # 👇 Only save status directly if NOT item tracking
            if not po_process.department_process.has_item_tracking:
                po_process.save()

                # Save history
                POProcessHistory.objects.create(
                    po_process=po_process,
                    status=po_process.current_status,
                    remark=self.cleaned_data.get("remark", ""),
                    changed_by=self.user,
                )

                # Auto check and update PO status
                check_and_update_po_status(po_process.purchase_order)
            else:
                # For item tracking processes just save last_updated_by
                po_process.save(update_fields=["last_updated_by"])

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
