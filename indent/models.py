from django.db import models, transaction
from django.contrib.auth import get_user_model

from po.models import PurchaseOrder, PurchaseOrderItem, POProcess
from bom.models import BOMItem

User = get_user_model()

INDENT_PROCESS_CODE_MAP = {
    13: "RAW",
    18: "ACC",
    23: "PAC",
}


class Indent(models.Model):
    """
    Production Indent raised during a PO Production process.
    One indent per PO + process combination (can have multiple items).
    """

    indent_number = models.CharField(
        max_length=50,
        unique=True,
        blank=True,
        editable=False,
        help_text="System generated: IND/{oa_number}/{CODE}/{0001}",
    )

    indent_date = models.DateField(
        help_text="Date when indent is raised",
    )

    purchase_order = models.ForeignKey(
        PurchaseOrder,
        on_delete=models.PROTECT,
        related_name="indents",
    )

    po_process = models.ForeignKey(
        POProcess,
        on_delete=models.PROTECT,
        related_name="indents",
        help_text="Production process during which indent is raised",
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_indents",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    remarks = models.TextField(
        blank=True,
    )

    class Meta:
        ordering = ["-id"]
        verbose_name = "Indent"
        verbose_name_plural = "Indents"

    def __str__(self):
        return self.indent_number

    def save(self, *args, **kwargs):
        if not self.indent_number:
            process_id = self.po_process.department_process_id

            indent_code = INDENT_PROCESS_CODE_MAP.get(process_id)
            if not indent_code:
                raise ValueError("Invalid production process for indent numbering.")

            oa_number = self.purchase_order.oa_number

            with transaction.atomic():
                last_indent = (
                    Indent.objects.select_for_update()
                    .filter(po_process__department_process_id=process_id)
                    .order_by("-id")
                    .first()
                )

                if last_indent and last_indent.indent_number:
                    try:
                        last_no = int(last_indent.indent_number.split("/")[-1])
                    except (IndexError, ValueError):
                        last_no = 0
                else:
                    last_no = 0

                self.indent_number = (
                    f"IND/{oa_number}/{indent_code}/{str(last_no + 1).zfill(4)}"
                )

        super().save(*args, **kwargs)


class IndentItem(models.Model):
    """
    One line per PO item inside an Indent.
    Captures how much of that PO item is being indented.
    """

    indent = models.ForeignKey(
        Indent,
        on_delete=models.CASCADE,
        related_name="items",
    )

    purchase_order_item = models.ForeignKey(
        PurchaseOrderItem,
        on_delete=models.PROTECT,
        related_name="indent_items",
    )

    required_quantity = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        help_text="Quantity required for this PO item",
    )

    uom = models.CharField(
        max_length=20,
        help_text="Unit of Measure (carried from PO item)",
    )

    remarks = models.TextField(
        blank=True,
    )

    class Meta:
        ordering = ["id"]
        verbose_name = "Indent Item"
        verbose_name_plural = "Indent Items"

    def __str__(self):
        return f"{self.indent.indent_number} — {self.purchase_order_item}"


class IndentSubItem(models.Model):
    """
    Raw materials / components needed to fulfil one IndentItem.

    - If bom_item is set   → this row was pulled from a BOM (BOM-linked)
    - If bom_item is null  → this row was entered manually (free-form)

    Fields mirror BOMItem so BOM-pulled rows auto-fill cleanly,
    but every field remains editable after selection.
    """

    indent_item = models.ForeignKey(
        IndentItem,
        on_delete=models.CASCADE,
        related_name="sub_items",
    )

    # Optional link to a BOMItem — null means manually entered
    bom_item = models.ForeignKey(
        BOMItem,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="indent_sub_items",
        help_text="Set when sub-item was pulled from a BOM; null for manual entries",
    )

    item = models.CharField(
        max_length=255,
        help_text="Material / component name",
    )

    size = models.CharField(
        max_length=100,
        blank=True,
    )

    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )

    material = models.CharField(
        max_length=255,
    )

    remarks = models.TextField(
        blank=True,
    )

    class Meta:
        ordering = ["id"]
        verbose_name = "Indent Sub-Item"
        verbose_name_plural = "Indent Sub-Items"
        indexes = [
            models.Index(fields=["indent_item"]),
        ]

    def __str__(self):
        source = f"BOM#{self.bom_item_id}" if self.bom_item_id else "Manual"
        return f"{self.indent_item} — {self.item} [{source}]"

    @property
    def is_bom_linked(self):
        return self.bom_item_id is not None