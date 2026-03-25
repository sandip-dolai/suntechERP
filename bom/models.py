from django.db import models, transaction
from django.contrib.auth import get_user_model

from po.models import PurchaseOrder

User = get_user_model()


class BOM(models.Model):
    """
    BOM Header — linked to a PO.
    Multiple BOMs can exist per PO.
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
        BOM/OA-00123/0001
        Uses po.oa_number as the reference segment.
        """
        with transaction.atomic():
            last_bom = (
                cls.objects.select_for_update()
                .filter(po=po)
                .order_by("-id")
                .first()
            )

            last_no = 0
            if last_bom:
                try:
                    last_no = int(last_bom.bom_no.split("/")[-1])
                except (IndexError, ValueError):
                    last_no = 0

            next_no = str(last_no + 1).zfill(4)
            return f"BOM/{po.oa_number}/{next_no}"


class BOMItem(models.Model):
    """
    BOM Line Items — free-form materials required to complete the PO.
    Not linked to PO items; entered manually per BOM.
    """

    bom = models.ForeignKey(BOM, on_delete=models.CASCADE, related_name="items")
    item = models.CharField(max_length=255)
    size = models.CharField(max_length=100, blank=True)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    material = models.CharField(max_length=255)
    remarks = models.TextField(blank=True)

    class Meta:
        ordering = ["id"]
        indexes = [
            models.Index(fields=["bom"]),
        ]

    def __str__(self):
        return f"{self.bom.bom_no} — {self.item} ({self.material})"