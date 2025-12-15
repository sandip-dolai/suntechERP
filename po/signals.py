from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from .models import PurchaseOrder, POProcess, POProcessHistory
from master.models import DepartmentProcessMaster, ProcessStatusMaster


@receiver(post_save, sender=PurchaseOrder)
def create_po_processes(sender, instance, created, **kwargs):
    """
    Auto-create POProcess rows when a new PO is created.
    """

    if not created:
        return

    # Get default status (PENDING)
    try:
        pending_status = ProcessStatusMaster.objects.get(name="PENDING", is_active=True)
    except ProcessStatusMaster.DoesNotExist:
        raise RuntimeError("ProcessStatusMaster with name='PENDING' must exist")

    department_processes = DepartmentProcessMaster.objects.filter(is_active=True)

    po_process_list = []
    history_list = []

    for dp in department_processes:
        po_process = POProcess(
            purchase_order=instance,
            department_process=dp,
            current_status=pending_status,
            last_updated_by=instance.created_by,
        )
        po_process_list.append(po_process)

    # Bulk create POProcess
    created_processes = POProcess.objects.bulk_create(po_process_list)

    # Initial history entries
    for po_process in created_processes:
        history_list.append(
            POProcessHistory(
                po_process=po_process,
                status=pending_status,
                remark="Auto-created on PO creation",
                changed_by=instance.created_by,
            )
        )

    POProcessHistory.objects.bulk_create(history_list)


@receiver(post_delete, sender=PurchaseOrder)
def cleanup_po_process_history(sender, instance, **kwargs):
    """
    Cleanup POProcessHistory when a PO is deleted.
    """

    POProcessHistory.objects.filter(po_process__purchase_order=instance).delete()
