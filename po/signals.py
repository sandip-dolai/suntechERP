from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db import transaction

from .models import PurchaseOrder, POProcess, POProcessHistory
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

    pending_status = (
        ProcessStatusMaster.objects
        .filter(name__iexact="PENDING", is_active=True)
        .first()
    )

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
    POProcessHistory.objects.filter(
        po_process__purchase_order=instance
    ).delete()
