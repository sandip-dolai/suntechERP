from django import forms
from django.forms import inlineformset_factory
from .models import (
    PurchaseOrder,
    PurchaseOrderItem,
    POProcess,
    POProcessHistory,
    POTarget,
    POTargetItem,
    MONTH_CHOICES,
)
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
        widgets = {
            "po_number": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g. PO-0001",
                }
            ),
            "oa_number": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g. OA-0001",
                }
            ),
            "po_date": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                }
            ),
            "delivery_date": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                }
            ),
            # company rendered as select — select2 applied via JS
            "company": forms.Select(
                attrs={
                    "class": "form-control",
                    "id": "id_company",
                }
            ),
            "department": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),
            "po_status": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),
        }

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
            "material_code": forms.TextInput(
                attrs={
                    "class": "form-control form-control-sm",
                    "placeholder": "Code",
                }
            ),
            "material_description": forms.Textarea(
                attrs={
                    "class": "form-control form-control-sm",
                    "rows": 2,
                    "placeholder": "Material description",
                }
            ),
            "quantity_value": forms.NumberInput(
                attrs={
                    "class": "form-control form-control-sm",
                    "step": "0.001",
                    "placeholder": "0.000",
                }
            ),
            "uom": forms.TextInput(
                attrs={
                    "class": "form-control form-control-sm",
                    "placeholder": "SET",
                }
            ),
            "material_value": forms.NumberInput(
                attrs={
                    "class": "form-control form-control-sm",
                    "step": "0.01",
                    "placeholder": "0.00",
                }
            ),
        }

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.quantity = (
            str(instance.quantity_value) if instance.quantity_value is not None else "0"
        )
        if commit:
            instance.save()
        return instance


# ------------------------------
# PURCHASE ORDER ITEM FORMSET
# ------------------------------
class BasePurchaseOrderItemFormSet(BaseInlineFormSet):

    def save_new(self, form, commit=True):
        """Called when saving a brand new item (not an existing one)."""
        instance = super().save_new(form, commit=False)
        instance.quantity = (
            str(instance.quantity_value) if instance.quantity_value else "0"
        )
        if commit:
            instance.save()
        return instance

    def save_existing(self, form, instance, commit=True):
        """Called when saving an existing item."""
        instance = super().save_existing(form, instance, commit=False)
        instance.quantity = (
            str(instance.quantity_value) if instance.quantity_value else "0"
        )
        if commit:
            instance.save()
        return instance

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
    from master.models import DepartmentProcessMaster

    processes = po.processes.select_related(
        "department_process", "current_status"
    ).filter(department_process__excludes_from_completion=False)

    if not processes.exists():
        return

    all_completed = all(p.current_status.is_completed for p in processes)

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
        required=True,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 2,
                "placeholder": "Add remark (required)",
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


# ------------------------------
# PO TARGET FORM
# ------------------------------
class POTargetForm(forms.Form):
    purchase_order = forms.ModelChoiceField(
        queryset=PurchaseOrder.objects.order_by("-id"),
        empty_label="— Select PO —",
        widget=forms.Select(attrs={"class": "form-control", "id": "id_po_select"}),
    )
    month = forms.ChoiceField(
        choices=[("", "— Select Month —")] + list(MONTH_CHOICES),
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    year = forms.IntegerField(
        widget=forms.NumberInput(attrs={
            "class": "form-control",
            "placeholder": "e.g. 2026",
            "min": 2020,
            "max": 2099,
        }),
    )
    selected_items = forms.CharField(
        widget=forms.HiddenInput(),
        required=False,
    )

    def __init__(self, *args, **kwargs):
        self.instance = kwargs.pop("instance", None)
        super().__init__(*args, **kwargs)

        # On edit — make PO readonly
        if self.instance:
            self.fields["purchase_order"].widget.attrs["disabled"] = True
            self.fields["purchase_order"].required = False
            self.fields["purchase_order"].initial = self.instance.purchase_order

    def clean_month(self):
        value = self.cleaned_data.get("month")
        if not value:
            raise forms.ValidationError("Please select a month.")
        return int(value)

    def clean(self):
        cleaned_data = super().clean()
        month = cleaned_data.get("month")
        year = cleaned_data.get("year")
        selected_items_raw = cleaned_data.get("selected_items", "")

        # On edit, use instance PO; on create, use form PO
        po = self.instance.purchase_order if self.instance else cleaned_data.get("purchase_order")

        try:
            item_ids = [int(i) for i in selected_items_raw.split(",") if i.strip()]
        except ValueError:
            item_ids = []

        if not item_ids:
            raise forms.ValidationError("Please select at least one PO item.")

        cleaned_data["item_ids"] = item_ids
        cleaned_data["purchase_order"] = po

        # Duplicate check (exclude self on edit)
        if po and month and year:
            qs = POTarget.objects.filter(purchase_order=po, month=month, year=year)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError(
                    f"A target for PO {po.po_number} in this month/year already exists."
                )

        return cleaned_data