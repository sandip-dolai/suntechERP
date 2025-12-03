from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from po.models import PurchaseOrder
from master.models import ItemMaster
from django.core.validators import MinValueValidator
from decimal import Decimal


class BillOfMaterials(models.Model):
    """
    BOM Line Item: Links a Purchase Order to specific Items from ItemMaster.
    One PO → Many BOM lines.
    """
    po = models.ForeignKey(
        PurchaseOrder,
        on_delete=models.CASCADE,
        related_name='boms',
        verbose_name="Purchase Order"
    )
    item = models.ForeignKey(
        ItemMaster,
        on_delete=models.PROTECT,
        related_name='bom_lines',
        verbose_name="Item"
    )
    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Required quantity of the item"
    )
    unit = models.CharField(
        max_length=20,
        blank=False,
        editable=False,
        help_text="Auto-filled from ItemMaster.uom"
    )
    created_by = models.ForeignKey(
        get_user_model(),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        editable=False
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('po', 'item')
        ordering = ['-created_at']
        verbose_name = "BOM Line"
        verbose_name_plural = "BOM Lines"
        indexes = [
            models.Index(fields=['po']),
            models.Index(fields=['item']),
        ]

    def __str__(self):
        return f"{self.item.code} × {self.quantity} {self.unit} | PO: {self.po.po_number}"

    def clean(self):
        if self.item and self.unit and self.item.uom != self.unit:
            raise ValidationError("Unit must match the item's UOM.")

    def save(self, *args, **kwargs):
        # Auto-fill unit from ItemMaster
        if self.item and not self.unit:
            self.unit = self.item.uom
        if not self.unit:
            raise ValidationError("Item must have a valid UOM.")
        self.full_clean()  # Ensures clean() is called
        super().save(*args, **kwargs)