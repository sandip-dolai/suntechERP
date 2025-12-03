from django.db import models
from django.contrib.auth import get_user_model
from bom.models import BillOfMaterials

class Indent(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ]
    bom = models.ForeignKey(BillOfMaterials, on_delete=models.CASCADE, related_name='indents')
    indent_number = models.CharField(max_length=100, unique=True)
    indent_date = models.DateField()
    required_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    created_by = models.ForeignKey(get_user_model(), on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f"Indent {self.indent_number} for BOM {self.bom.item_name}"