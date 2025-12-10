from django.db import models
from django.contrib.auth import get_user_model
from master.models import CompanyMaster


class PurchaseOrder(models.Model):
    """
    PO Header — one record per purchase order.
    """

    po_number = models.CharField(max_length=100, unique=True)
    po_date = models.DateField()

    oa_number = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="OA Number",
        help_text="Order Acceptance Number (Unique & Mandatory)",
    )

    company = models.ForeignKey(
        CompanyMaster,
        on_delete=models.PROTECT,
        related_name="purchase_orders",
        verbose_name="Supplier / Customer",
    )

    delivery_date = models.DateField(null=True, blank=True)

    created_by = models.ForeignKey(
        get_user_model(),
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_purchase_orders",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-id"]
        verbose_name = "Purchase Order"
        verbose_name_plural = "Purchase Orders"

    def __str__(self):
        return f"PO {self.po_number} - {self.company.name if self.company else '—'}"

    @property
    def item_count(self):
        return self.items.count()


class PurchaseOrderItem(models.Model):
    """
    PO Line Item — one record per material row inside a PO.
    Multiple items belong to one PurchaseOrder.
    """

    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("INPROCESS", "In Process"),
        ("COMPLETED", "Completed"),
    ]

    purchase_order = models.ForeignKey(
        PurchaseOrder, on_delete=models.CASCADE, related_name="items"
    )

    material_description = models.TextField()
    quantity = models.CharField(max_length=100)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["id"]
        verbose_name = "PO Item"
        verbose_name_plural = "PO Items"

    def __str__(self):
        return f"Item for PO {self.purchase_order.po_number}"
