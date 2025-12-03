from django.db import models
from django.contrib.auth import get_user_model
from master.models import CompanyMaster

class PurchaseOrder(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('INPROCESS', 'In Process'),
        ('COMPLETED', 'Completed'),
    ]
    po_number = models.CharField(max_length=100, unique=True)
    po_date = models.DateField()
    company = models.ForeignKey(
        CompanyMaster,
        on_delete=models.PROTECT,
        related_name='purchase_orders',
        verbose_name="Supplier / Customer",
        default=None,
        null=True,
    )
    material_description = models.TextField()
    quantity = models.CharField(max_length=100)
    delivery_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    created_by = models.ForeignKey(get_user_model(), on_delete=models.SET_NULL, null=True)

    def __str__(self):
        # company can be null, so fall back to "—"
        return f"PO {self.po_number} - {self.company.name if self.company else '—'}"