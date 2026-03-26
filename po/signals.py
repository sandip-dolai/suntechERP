from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db import transaction

from .models import (
    POProcessItemStatus,
    PurchaseOrder,
    POProcess,
    POProcessHistory,
    PurchaseOrderItem,
)
from master.models import DepartmentProcessMaster, ProcessStatusMaster


@receiver(post_save, sender=PurchaseOrder)
def create_po_processes(sender, instance, created, **kwargs):
    """
    Auto-create POProcess and POProcessHistory rows
    when a new PurchaseOrder is created.
    Production-safe.
    """

    if not created:
        return

    pending_status = ProcessStatusMaster.objects.filter(
        name__iexact="PENDING", is_active=True
    ).first()

    # Do not crash production if master data is missing
    if not pending_status:
        return

    department_processes = DepartmentProcessMaster.objects.filter(is_active=True)
    if not department_processes.exists():
        return

    with transaction.atomic():
        for dp in department_processes:
            po_process = POProcess.objects.create(
                purchase_order=instance,
                department_process=dp,
                current_status=pending_status,
                last_updated_by=instance.created_by,
            )

            POProcessHistory.objects.create(
                po_process=po_process,
                status=pending_status,
                remark="Auto-created on PO creation",
                changed_by=instance.created_by,
            )


@receiver(post_delete, sender=PurchaseOrder)
def cleanup_po_process_history(sender, instance, **kwargs):
    """
    Cleanup POProcessHistory when a PO is deleted.
    Safe operation.
    """
    POProcessHistory.objects.filter(po_process__purchase_order=instance).delete()


def _update_po_item_status(po_item):
    """
    Recalculates PurchaseOrderItem.status based on all
    POProcessItemStatus records across all item-tracking processes.

    Rules:
      No tracking processes exist        → leave untouched (stay PENDING)
      No POProcessItemStatus for item    → PENDING
      At least one exists, not all done  → INPROCESS
      ALL tracking processes completed   → COMPLETED
    """
    tracking_processes = po_item.purchase_order.processes.filter(
        department_process__has_item_tracking=True
    )

    if not tracking_processes.exists():
        return

    item_statuses = POProcessItemStatus.objects.filter(
        po_item=po_item,
        po_process__in=tracking_processes,
    ).select_related("status")

    if not item_statuses.exists():
        new_status = "PENDING"
    else:
        tracking_process_ids = set(tracking_processes.values_list("id", flat=True))
        completed_process_ids = set(
            item_statuses.filter(status__is_completed=True).values_list(
                "po_process_id", flat=True
            )
        )

        if tracking_process_ids == completed_process_ids:
            new_status = "COMPLETED"
        else:
            new_status = "INPROCESS"

    if po_item.status != new_status:
        PurchaseOrderItem.objects.filter(pk=po_item.pk).update(status=new_status)


@receiver(post_save, sender=POProcessItemStatus)
def on_process_item_status_save(sender, instance, **kwargs):
    _update_po_item_status(instance.po_item)


@receiver(post_delete, sender=POProcessItemStatus)
def on_process_item_status_delete(sender, instance, **kwargs):
    _update_po_item_status(instance.po_item)
