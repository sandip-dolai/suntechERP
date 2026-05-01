from django.db import models
from django.contrib.auth import get_user_model
from master.models import CompanyMaster, DepartmentProcessMaster, ProcessStatusMaster

User = get_user_model()


class PurchaseOrder(models.Model):
    """
    PO Header — one record per purchase order.
    """

    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("COMPLETED", "Completed"),
    ]

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
    department = models.CharField(
        max_length=50,
        choices=[
            ("Marketing", "Marketing"),
            ("Design", "Design"),
            ("Production", "Production"),
            ("Quality", "Quality"),
            ("Admin", "Admin"),
            ("Logistics", "Logistics"),
        ],
        blank=True,
        verbose_name="Department",
    )

    created_by = models.ForeignKey(
        get_user_model(),
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_purchase_orders",
    )

    po_status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="PENDING",
        db_index=True,
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
    """

    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("INPROCESS", "In Process"),
        ("COMPLETED", "Completed"),
    ]

    purchase_order = models.ForeignKey(
        PurchaseOrder, on_delete=models.CASCADE, related_name="items"
    )

    material_code = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="Material Code",
    )

    material_description = models.TextField()

    quantity = models.CharField(max_length=100)

    quantity_value = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        null=True,
        blank=True,
        help_text="Numeric quantity (for calculations)",
    )

    uom = models.CharField(
        max_length=20,
        default="SET",
        help_text="Unit of Measure",
    )
    material_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Material Value",
    )

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["id"]
        verbose_name = "PO Item"
        verbose_name_plural = "PO Items"

    def __str__(self):
        return f"Item for PO {self.purchase_order.po_number}"


class POProcess(models.Model):
    """
    Represents the CURRENT state of a department process for a PO.
    One record per (PO × DepartmentProcess).
    """

    purchase_order = models.ForeignKey(
        PurchaseOrder,
        on_delete=models.CASCADE,
        related_name="processes",
    )

    department_process = models.ForeignKey(
        DepartmentProcessMaster,
        on_delete=models.PROTECT,
        related_name="po_processes",
    )

    current_status = models.ForeignKey(
        ProcessStatusMaster,
        on_delete=models.PROTECT,
        related_name="po_processes",
    )

    last_updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="updated_po_processes",
    )

    last_updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("purchase_order", "department_process")
        ordering = ["department_process__department", "department_process__name"]
        verbose_name = "PO Process"
        verbose_name_plural = "PO Processes"

    def __str__(self):
        return (
            f"{self.purchase_order.po_number} | "
            f"{self.department_process.department} - "
            f"{self.department_process.name}"
        )


class POProcessHistory(models.Model):
    """
    Immutable history of status changes for a PO process.
    """

    po_process = models.ForeignKey(
        POProcess,
        on_delete=models.CASCADE,
        related_name="history",
    )

    status = models.ForeignKey(
        ProcessStatusMaster,
        on_delete=models.PROTECT,
        related_name="po_process_history",
    )

    remark = models.TextField(blank=True)

    changed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="po_process_history_changes",
    )

    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-changed_at"]
        verbose_name = "PO Process History"
        verbose_name_plural = "PO Process Histories"

    def __str__(self):
        return f"{self.po_process.purchase_order.po_number} | " f"{self.status.name}"


class POProcessItemStatus(models.Model):
    """
    Tracks status of each PO item within a specific PO process.
    Only created for processes where has_item_tracking=True.
    """

    po_process = models.ForeignKey(
        POProcess,
        on_delete=models.CASCADE,
        related_name="item_statuses",
    )

    po_item = models.ForeignKey(
        PurchaseOrderItem,
        on_delete=models.PROTECT,
        related_name="process_item_statuses",
    )

    status = models.ForeignKey(
        ProcessStatusMaster,
        on_delete=models.PROTECT,
        related_name="process_item_statuses",
    )

    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="po_process_item_status_updates",
    )

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("po_process", "po_item")
        ordering = ["po_item"]
        verbose_name = "PO Process Item Status"
        verbose_name_plural = "PO Process Item Statuses"

    def __str__(self):
        return (
            f"{self.po_process.purchase_order.po_number} | "
            f"{self.po_process.department_process.name} | "
            f"{self.po_item.material_description[:30]}"
        )


MONTH_CHOICES = [
    (1, "January"),
    (2, "February"),
    (3, "March"),
    (4, "April"),
    (5, "May"),
    (6, "June"),
    (7, "July"),
    (8, "August"),
    (9, "September"),
    (10, "October"),
    (11, "November"),
    (12, "December"),
]


class POTarget(models.Model):
    purchase_order = models.ForeignKey(
        PurchaseOrder,
        on_delete=models.CASCADE,
        related_name="targets",
    )
    month = models.PositiveIntegerField(choices=MONTH_CHOICES)
    year = models.PositiveIntegerField()
    target_value = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        help_text="Auto-computed from selected PO items",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("purchase_order", "month", "year")
        ordering = ["-year", "-month"]
        verbose_name = "PO Target"
        verbose_name_plural = "PO Targets"

    def __str__(self):
        month_name = dict(MONTH_CHOICES).get(self.month, self.month)
        return f"PO {self.purchase_order.po_number} | {month_name} {self.year} → {self.target_value}"


class POTargetItem(models.Model):
    po_target = models.ForeignKey(
        POTarget,
        on_delete=models.CASCADE,
        related_name="target_items",
    )
    po_item = models.ForeignKey(
        PurchaseOrderItem,
        on_delete=models.PROTECT,
        related_name="target_entries",
    )

    class Meta:
        unique_together = ("po_target", "po_item")
        ordering = ["po_item"]
        verbose_name = "PO Target Item"
        verbose_name_plural = "PO Target Items"

    def __str__(self):
        return f"{self.po_target} | {self.po_item.material_description[:40]}"


class POComment(models.Model):
    purchase_order = models.ForeignKey(
        PurchaseOrder,
        on_delete=models.CASCADE,
        related_name="comments",
    )
    po_item = models.ForeignKey(
        PurchaseOrderItem,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="comments",
    )
    comment = models.TextField(blank=True)
    commented_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="po_comments",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        verbose_name = "PO Comment"
        verbose_name_plural = "PO Comments"

    def __str__(self):
        return f"{self.purchase_order.po_number} | Item {self.po_item_id} | {self.commented_by}"


class PONote(models.Model):
    purchase_order = models.ForeignKey(
        PurchaseOrder,
        on_delete=models.CASCADE,
        related_name="notes",
    )
    note = models.TextField()
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="po_notes",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "PO Note"
        verbose_name_plural = "PO Notes"

    def __str__(self):
        return f"{self.purchase_order.po_number} | {self.created_by}"


class POTask(models.Model):
    purchase_order = models.ForeignKey(
        PurchaseOrder,
        on_delete=models.CASCADE,
        related_name="tasks",
    )
    task = models.CharField(max_length=500)
    is_completed = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_po_tasks",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "created_at"]
        verbose_name = "PO Task"
        verbose_name_plural = "PO Tasks"

    def __str__(self):
        return f"{self.purchase_order.po_number} | {self.task[:50]}"
