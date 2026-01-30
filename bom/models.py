from django.db import models, transaction
from django.contrib.auth import get_user_model

from po.models import PurchaseOrder, PurchaseOrderItem

User = get_user_model()


class BOM(models.Model):
    """
    BOM Header (Indent-style)
    One BOM per PO
    """

    bom_no = models.CharField(max_length=50, unique=True)
    po = models.ForeignKey(PurchaseOrder, on_delete=models.PROTECT, related_name="boms")
    bom_date = models.DateField()
    created_by = models.ForeignKey(User, on_delete=models.PROTECT)

    class Meta:
        ordering = ["-id"]

    def __str__(self):
        return self.bom_no

    @classmethod
    def generate_bom_no(cls, po):
        """
        Generates BOM number like:
        BOM/PO-00123/0001
        """
        with transaction.atomic():
            last_bom = (
                cls.objects.select_for_update().filter(po=po).order_by("-id").first()
            )

            last_no = 0
            if last_bom:
                try:
                    last_no = int(last_bom.bom_no.split("/")[-1])
                except (IndexError, ValueError):
                    last_no = 0

            next_no = str(last_no + 1).zfill(4)
            return f"BOM/{po.po_number}/{next_no}"


class BOMItem(models.Model):
    """
    BOM Items
    - Item & UOM come from PO item
    - Quantity is editable
    """

    bom = models.ForeignKey(BOM, on_delete=models.CASCADE, related_name="items")

    po_item = models.ForeignKey(PurchaseOrderItem, on_delete=models.PROTECT)

    quantity = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(
                fields=["bom", "po_item"], name="unique_po_item_per_bom"
            )
        ]
        indexes = [
            models.Index(fields=["bom"]),
        ]

    def __str__(self):
        return f"{self.bom.bom_no} - {self.po_item}"
