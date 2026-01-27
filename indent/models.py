from django.db import models, transaction
from django.contrib.auth import get_user_model

from po.models import PurchaseOrder, PurchaseOrderItem, POProcess

User = get_user_model()
INDENT_PROCESS_CODE_MAP = {
    13: "RAW",
    18: "ACC",
    23: "PAC",
}


class Indent(models.Model):
    """
    Production Indent raised during a PO Production process.
    Header contains context only.
    """

    STATUS_CHOICES = [
        ("OPEN", "Open"),
        ("CLOSED", "Closed"),
    ]

    indent_number = models.CharField(
        max_length=50,
        unique=True,
        blank=True,
        editable=False,
        help_text="System generated indent number",
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

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default="OPEN",
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
            
            po_number = self.purchase_order.po_number
            with transaction.atomic():
                last_indent = (
                    Indent.objects.select_for_update()
                    .filter(po_process__department_process_id=process_id)
                    .order_by("-id")
                    .first()
                )

                if last_indent and last_indent.indent_number:
                    last_no = int(last_indent.indent_number.split("/")[-1])
                else:
                    last_no = 0

                self.indent_number = (
                    f"IND/{po_number}/{indent_code}/" f"{str(last_no + 1).zfill(4)}"
                )

        super().save(*args, **kwargs)


class IndentItem(models.Model):
    """
    Line item inside an Indent.
    References PO item directly.
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
        help_text="Unit of Measure (default from PO item)",
    )

    remarks = models.TextField(
        blank=True,
    )

    class Meta:
        ordering = ["id"]
        verbose_name = "Indent Item"
        verbose_name_plural = "Indent Items"

    def __str__(self):
        return f"{self.indent.indent_number} - {self.purchase_order_item}"
