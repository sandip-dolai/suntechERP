from decimal import Decimal
from urllib import request
from django.db.models import (
    F,
    Q,
    Count,
    Value,
    CharField,
    OuterRef,
    Subquery,
    Sum,
    DecimalField,
)
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from suntech_erp.permissions import admin_required, can_view_value, is_admin
from django.contrib.auth.decorators import login_required as login_required_view
from django.db import transaction, IntegrityError

from django.db.models.functions import Concat, Coalesce, TruncMonth
from .models import (
    PurchaseOrder,
    PurchaseOrderItem,
    POProcess,
    POProcessHistory,
    POProcessItemStatus,
    POTarget,
    POTargetItem,
    POComment,
)
from .forms import (
    PurchaseOrderForm,
    PurchaseOrderItemFormSet,
    POProcessUpdateForm,
    POTargetForm,
)
from master.models import CompanyMaster, ProcessStatusMaster, DepartmentProcessMaster
from datetime import datetime
from django.http import HttpResponseForbidden, HttpResponse, JsonResponse
from django.template.loader import render_to_string
import json
from django.core.paginator import Paginator
from notifications.models import Notification
from django.contrib.auth import get_user_model

User = get_user_model()


# ------------------------------
# PO CREATE (header + items)
# ------------------------------
@admin_required
def po_create(request):
    if request.method == "POST":
        form = PurchaseOrderForm(request.POST)
        formset = PurchaseOrderItemFormSet(request.POST)
        if form.is_valid() and formset.is_valid():
            try:
                with transaction.atomic():
                    po = form.save(commit=False)
                    po.created_by = request.user
                    po.save()
                    formset.instance = po
                    formset.save()
                messages.success(request, "Purchase Order created successfully.")
                users = User.objects.filter(is_active=True).exclude(id=request.user.id)

                Notification.objects.bulk_create(
                    [
                        Notification(
                            user=user,
                            title="New Purchase Order Created",
                            message=f"PO {po.po_number} has been created.",
                            url=f"/po/{po.id}/processes/",
                        )
                        for user in users
                    ]
                )
                return redirect("po:po_list")
            except IntegrityError:
                form.add_error(None, "Database error: possible duplicate PO/OA number.")
    else:
        form = PurchaseOrderForm()
        formset = PurchaseOrderItemFormSet()

    context = {
        "form": form,
        "formset": formset,
        "title": "Create Purchase Order",
        "companies": CompanyMaster.objects.order_by("name"),
    }
    return render(request, "po/po_form.html", context)


# ------------------------------
# PO EDIT (header + items)
# ------------------------------
@admin_required
def po_edit(request, pk):
    po = get_object_or_404(PurchaseOrder, pk=pk)

    if request.method == "POST":
        form = PurchaseOrderForm(request.POST, instance=po)
        formset = PurchaseOrderItemFormSet(request.POST, instance=po)
        if form.is_valid() and formset.is_valid():
            try:
                with transaction.atomic():
                    form.save()
                    formset.save()
                messages.success(request, "Purchase Order updated successfully.")
                return redirect("po:po_list")
            except IntegrityError:
                form.add_error(None, "Database error: possible duplicate PO/OA number.")
    else:
        form = PurchaseOrderForm(instance=po)
        formset = PurchaseOrderItemFormSet(instance=po)

    context = {
        "form": form,
        "formset": formset,
        "title": f"Edit PO {po.po_number}",
        "po": po,
        "companies": CompanyMaster.objects.order_by("name"),
    }

    return render(request, "po/po_form.html", context)


# detele po


@admin_required
def po_delete(request, pk):
    if not is_admin(request.user):
        messages.error(request, "Permission denied.")
        return redirect("po:po_list")

    po = get_object_or_404(PurchaseOrder, pk=pk)

    if request.method == "POST":
        po_number = po.po_number
        po.delete()
        messages.success(request, f"PO {po_number} deleted successfully.")
        return redirect("po:po_list")

    # GET request — just redirect back (no delete page needed)
    return redirect("po:po_list")


# ==============================================================
# PO REPORT VIEW (MAIN)
# ==============================================================
@login_required_view
def po_report(request):
    # ------------------------------
    # VIEW MODE
    # ------------------------------
    view_mode = request.GET.get("view", "summary").lower()

    # ------------------------------
    # 🔹 GLOBAL SUMMARY (NOT FILTERED — always shows overall picture)
    # ------------------------------
    all_pos = PurchaseOrder.objects.all()

    total_po_count = all_pos.count()
    completed_po_count = all_pos.filter(po_status="COMPLETED").count()
    pending_po_count = total_po_count - completed_po_count

    total_po_value = all_pos.aggregate(
        total=Coalesce(
            Sum("items__material_value"),
            Value(0),
            output_field=DecimalField(max_digits=12, decimal_places=2),
        )
    )["total"]

    dispatched_po_value = all_pos.filter(po_status="COMPLETED").aggregate(
        total=Coalesce(
            Sum("items__material_value"),
            Value(0),
            output_field=DecimalField(max_digits=12, decimal_places=2),
        )
    )["total"]

    pending_po_value = total_po_value - dispatched_po_value

    dispatch_percentage = (
        (dispatched_po_value / total_po_value) * 100 if total_po_value > 0 else 0
    )

    # ------------------------------
    # FILTERS
    # ------------------------------
    today = datetime.today().date()
    date_from = request.GET.get("date_from") or today.strftime("%Y-%m-%d")
    date_to = request.GET.get("date_to") or today.strftime("%Y-%m-%d")

    filter_used = any(
        key in request.GET
        for key in [
            "po_number",
            "oa_number",
            "company",
            "date_from",
            "po_status",
            "department",
        ]
    )

    # Build PO-level filters
    base_filters = {"po_date__range": [date_from, date_to]}

    if request.GET.get("po_number"):
        base_filters["po_number"] = request.GET["po_number"]

    if request.GET.get("oa_number"):
        base_filters["oa_number"] = request.GET["oa_number"]

    if request.GET.get("company"):
        base_filters["company_id"] = request.GET["company"]

    if request.GET.get("po_status"):
        base_filters["po_status"] = request.GET["po_status"]

    if request.GET.get("department"):
        base_filters["department"] = request.GET["department"]

    # ------------------------------
    # FILTERED PO QUERYSET
    # ------------------------------
    po_qs = PurchaseOrder.objects.none()

    if filter_used:
        po_qs = (
            PurchaseOrder.objects.select_related("created_by", "company")
            .prefetch_related("items")
            .filter(**base_filters)
            .annotate(
                total_quantity=Coalesce(
                    Sum("items__quantity_value"),
                    Value(0),
                    output_field=DecimalField(max_digits=12, decimal_places=3),
                ),
                total_value=Coalesce(
                    Sum("items__material_value"),
                    Value(0),
                    output_field=DecimalField(max_digits=12, decimal_places=2),
                ),
                has_bom=Count("boms", distinct=True),
                has_indent=Count("indents", distinct=True),
            )
            .order_by("id")
        )

    # ------------------------------
    # 🔹 FILTERED SUMMARY (shows stats for current filter selection)
    # ------------------------------
    filtered_summary = None

    if filter_used:
        total_count = po_qs.count()
        completed_count = po_qs.filter(po_status="COMPLETED").count()
        pending_count = total_count - completed_count

        agg = PurchaseOrder.objects.filter(**base_filters).aggregate(
            total_value=Coalesce(
                Sum("items__material_value"),
                Value(0),
                output_field=DecimalField(max_digits=12, decimal_places=2),
            ),
            dispatched_value=Coalesce(
                Sum(
                    "items__material_value",
                    filter=Q(po_status="COMPLETED"),
                ),
                Value(0),
                output_field=DecimalField(max_digits=12, decimal_places=2),
            ),
        )

        total_value = agg["total_value"]
        dispatched_value = agg["dispatched_value"]
        pending_value = total_value - dispatched_value

        dispatch_pct = (dispatched_value / total_value) * 100 if total_value > 0 else 0

        filtered_summary = {
            "total_count": total_count,
            "completed_count": completed_count,
            "pending_count": pending_count,
            "total_value": total_value,
            "dispatched_value": dispatched_value,
            "pending_value": pending_value,
            "dispatch_percentage": round(dispatch_pct, 2),
        }

    # ------------------------------
    # PAGINATION (Summary view — paginate POs)
    # ------------------------------
    page_obj = None
    if filter_used and view_mode == "summary":
        paginator = Paginator(po_qs, 10)
        page_obj = paginator.get_page(request.GET.get("page"))

    # ------------------------------
    # ITEM VIEW (FILTERED)
    # ------------------------------
    items = None
    grand_totals = None
    items_page_obj = None

    if view_mode == "items" and filter_used:
        items_qs = (
            PurchaseOrderItem.objects.select_related(
                "purchase_order",
                "purchase_order__company",
                "purchase_order__created_by",
            )
            .filter(purchase_order__in=po_qs)
            .order_by("purchase_order__id")
        )

        grand_totals = items_qs.aggregate(
            total_quantity=Coalesce(
                Sum("quantity_value"),
                Value(0),
                output_field=DecimalField(max_digits=12, decimal_places=3),
            ),
            total_value=Coalesce(
                Sum("material_value"),
                Value(0),
                output_field=DecimalField(max_digits=12, decimal_places=2),
            ),
        )

        paginator = Paginator(items_qs, 30)
        items_page_obj = paginator.get_page(request.GET.get("page"))

    # ------------------------------
    # CONTEXT
    # ------------------------------
    context = {
        # View mode
        "view": view_mode,
        # Global Summary (unfiltered)
        "summary": {
            "total_po_count": total_po_count,
            "completed_po_count": completed_po_count,
            "pending_po_count": pending_po_count,
            "total_po_value": total_po_value,
            "dispatched_po_value": dispatched_po_value,
            "pending_po_value": pending_po_value,
            "dispatch_percentage": round(dispatch_percentage, 2),
        },
        # Filtered Summary
        "filtered_summary": filtered_summary,
        # Data
        "pos": po_qs,
        "page_obj": page_obj,
        "items_page_obj": items_page_obj,
        "grand_totals": grand_totals,
        # Filter state
        "filter_used": filter_used,
        "companies": CompanyMaster.objects.order_by("name"),
        "po_list": PurchaseOrder.objects.order_by("-id"),
        "departments": [
            "Marketing",
            "Design",
            "Production",
            "Quality",
            "Admin",
            "Logistics",
        ],
        "filters": {
            "po_number": request.GET.get("po_number", ""),
            "oa_number": request.GET.get("oa_number", ""),
            "company": request.GET.get("company", ""),
            "po_status": request.GET.get("po_status", ""),
            "date_from": date_from,
            "date_to": date_to,
            "department": request.GET.get("department", ""),
        },
        # Permissions
        "can_view_value": can_view_value(request.user),
    }

    return render(request, "po/po_report.html", context)


# ==============================================================
# PO REPORT SUMMARY EXCEL (updated with department filter)
# ==============================================================
@login_required_view
def po_report_summary_excel(request):
    today = datetime.today().date()
    date_from = request.GET.get("date_from") or today.strftime("%Y-%m-%d")
    date_to = request.GET.get("date_to") or today.strftime("%Y-%m-%d")

    base_filters = {"po_date__range": [date_from, date_to]}

    if request.GET.get("po_number"):
        base_filters["po_number"] = request.GET["po_number"]
    if request.GET.get("oa_number"):
        base_filters["oa_number"] = request.GET["oa_number"]
    if request.GET.get("company"):
        base_filters["company_id"] = request.GET["company"]
    if request.GET.get("po_status"):
        base_filters["po_status"] = request.GET["po_status"]
    if request.GET.get("department"):
        base_filters["department"] = request.GET["department"]

    pos = (
        PurchaseOrder.objects.select_related("company", "created_by")
        .prefetch_related("items")
        .filter(**base_filters)
        .annotate(
            total_quantity=Coalesce(
                Sum("items__quantity_value"),
                Value(0),
                output_field=DecimalField(max_digits=12, decimal_places=3),
            ),
            total_value=Coalesce(
                Sum("items__material_value"),
                Value(0),
                output_field=DecimalField(max_digits=12, decimal_places=2),
            ),
        )
        .order_by("id")
    )

    # Compute grand totals for template
    agg = pos.aggregate(
        total_qty=Coalesce(
            Sum("items__quantity_value"),
            Value(0),
            output_field=DecimalField(max_digits=12, decimal_places=3),
        ),
        total_value=Coalesce(
            Sum("items__material_value"),
            Value(0),
            output_field=DecimalField(max_digits=12, decimal_places=2),
        ),
    )

    html = render_to_string(
        "po/po_report_summary_excel.html",
        {
            "pos": pos,
            "total_qty": agg["total_qty"],
            "total_value": agg["total_value"],
            "can_view_value": can_view_value(request.user),
        },
    )

    response = HttpResponse(html)
    response["Content-Type"] = "application/vnd.ms-excel"
    response["Content-Disposition"] = (
        f'attachment; filename="PO_Summary_{date_from}_to_{date_to}.xls"'
    )
    response["Pragma"] = "no-cache"
    response["Expires"] = "0"
    return response


# ==============================================================
# PO REPORT ITEM EXCEL (updated with department filter)
# ==============================================================
@login_required_view
def po_report_item_excel(request):
    today = datetime.today().date()
    date_from = request.GET.get("date_from") or today.strftime("%Y-%m-%d")
    date_to = request.GET.get("date_to") or today.strftime("%Y-%m-%d")

    base_filters = {"purchase_order__po_date__range": [date_from, date_to]}

    if request.GET.get("po_number"):
        base_filters["purchase_order__po_number"] = request.GET["po_number"]
    if request.GET.get("oa_number"):
        base_filters["purchase_order__oa_number"] = request.GET["oa_number"]
    if request.GET.get("company"):
        base_filters["purchase_order__company_id"] = request.GET["company"]
    if request.GET.get("po_status"):
        base_filters["purchase_order__po_status"] = request.GET["po_status"]
    if request.GET.get("department"):
        base_filters["purchase_order__department"] = request.GET["department"]

    items = (
        PurchaseOrderItem.objects.select_related(
            "purchase_order",
            "purchase_order__company",
            "purchase_order__created_by",
        )
        .filter(**base_filters)
        .order_by("purchase_order__id", "id")
    )

    grand_totals = items.aggregate(
        total_quantity=Coalesce(
            Sum("quantity_value"),
            Value(0),
            output_field=DecimalField(max_digits=12, decimal_places=3),
        ),
        total_value=Coalesce(
            Sum("material_value"),
            Value(0),
            output_field=DecimalField(max_digits=12, decimal_places=2),
        ),
    )

    html = render_to_string(
        "po/po_report_item_excel.html",
        {
            "items": items,
            "grand_totals": grand_totals,
            "can_view_value": can_view_value(request.user),
        },
    )

    response = HttpResponse(html)
    response["Content-Type"] = "application/vnd.ms-excel"
    response["Content-Disposition"] = (
        f'attachment; filename="PO_Items_{date_from}_to_{date_to}.xls"'
    )
    response["Pragma"] = "no-cache"
    response["Expires"] = "0"
    return response


# ------------------------------
# PO PROCESS LIST / UPDATE / HISTORY / EXCEL
# ------------------------------
@login_required_view
def po_process_list(request, po_id):
    po = get_object_or_404(PurchaseOrder, pk=po_id)

    latest_remark_subquery = (
        POProcessHistory.objects.filter(po_process=OuterRef("pk"))
        .order_by("-changed_at")
        .values("remark")[:1]
    )

    processes = (
        po.processes.select_related(
            "department_process",
            "current_status",
            "last_updated_by",
        )
        .annotate(latest_remark=Subquery(latest_remark_subquery))
        .order_by("department_process__sequence")
    )

    item_status_map = {}
    for process in processes:
        if process.department_process.has_item_tracking:
            item_status_map[process.id] = {
                s.po_item_id: s
                for s in POProcessItemStatus.objects.filter(
                    po_process=process
                ).select_related("status")
            }

    # Total PO items count
    total_items = po.items.count()

    return render(
        request,
        "po/po_process_list.html",
        {
            "po": po,
            "processes": processes,
            "item_status_map": item_status_map,
            "total_items": total_items,
            "po_items": po.items.all(),
        },
    )


# ------------------------------
# PO PROCESS UPDATE
# ------------------------------
def can_edit_po_process(user, po_process):
    """
    Admin can edit all.
    Department users can edit only their department processes.
    """
    if is_admin(user):
        return True

    return getattr(user, "department", None) == po_process.department_process.department


@login_required_view
def po_process_update(request, process_id):
    po_process = get_object_or_404(POProcess, pk=process_id)
    po = po_process.purchase_order
    has_item_tracking = po_process.department_process.has_item_tracking

    # 🔐 Permission check
    if not can_edit_po_process(request.user, po_process):
        return HttpResponseForbidden(
            "You do not have permission to update this process."
        )

    # Get all PO items
    po_items = po.items.all()

    # Get existing item statuses for this process → dict {item_id: POProcessItemStatus}
    existing_statuses = {
        s.po_item_id: s
        for s in POProcessItemStatus.objects.filter(
            po_process=po_process
        ).select_related("status")
    }

    # Get all active statuses for item dropdown
    status_choices = ProcessStatusMaster.objects.filter(is_active=True)

    if request.method == "POST":
        form = POProcessUpdateForm(
            request.POST,
            instance=po_process,
            user=request.user,
        )

        if form.is_valid():
            if has_item_tracking:
                # Get selected items and status from POST
                selected_item_ids = request.POST.getlist("selected_items")
                selected_status_id = request.POST.get("item_status")
                remark = form.cleaned_data.get("remark", "")

                if not selected_item_ids or not selected_status_id:
                    messages.error(
                        request, "Please select at least one item and a status."
                    )
                else:
                    try:
                        selected_status = ProcessStatusMaster.objects.get(
                            id=selected_status_id
                        )

                        # Save or update POProcessItemStatus for each selected item
                        for item_id in selected_item_ids:
                            POProcessItemStatus.objects.update_or_create(
                                po_process=po_process,
                                po_item_id=item_id,
                                defaults={
                                    "status": selected_status,
                                    "updated_by": request.user,
                                },
                            )

                        # Save remark to history
                        POProcessHistory.objects.create(
                            po_process=po_process,
                            status=selected_status,
                            remark=remark,
                            changed_by=request.user,
                        )

                        # Update last_updated_by
                        po_process.last_updated_by = request.user
                        po_process.save(update_fields=["last_updated_by"])

                        # Auto set process status based on all item statuses
                        from .forms import auto_set_process_status

                        auto_set_process_status(po_process)

                        # Auto check and update PO status
                        from .forms import check_and_update_po_status

                        check_and_update_po_status(po)

                        messages.success(request, "Item statuses updated successfully.")
                        return redirect("po:po_process_list", po_id=po.id)

                    except ProcessStatusMaster.DoesNotExist:
                        messages.error(request, "Invalid status selected.")

            else:
                # Normal process update
                form.save()
                messages.success(request, "Process status updated successfully.")
                return redirect("po:po_process_list", po_id=po.id)

    else:
        form = POProcessUpdateForm(
            instance=po_process,
            user=request.user,
        )

    context = {
        "form": form,
        "po": po,
        "po_process": po_process,
        "has_item_tracking": has_item_tracking,
        "po_items": po_items,
        "existing_statuses": existing_statuses,
        "status_choices": status_choices,
    }

    return render(
        request,
        "po/po_process_update.html",
        context,
    )


# ------------------------------
# PO PROCESS HISTORY VIEW
# ------------------------------
@login_required_view
def po_process_history(request, process_id):
    po_process = get_object_or_404(POProcess, pk=process_id)
    po = po_process.purchase_order

    history = po_process.history.select_related("status", "changed_by").order_by(
        "-changed_at"
    )

    item_statuses = []
    if po_process.department_process.has_item_tracking:
        item_statuses = (
            POProcessItemStatus.objects.filter(po_process=po_process)
            .select_related("status", "po_item", "updated_by")
            .order_by("po_item__id")
        )

    context = {
        "po": po,
        "po_process": po_process,
        "history": history,
        "item_statuses": item_statuses,
        "has_item_tracking": po_process.department_process.has_item_tracking,
    }

    return render(
        request,
        "po/po_process_history.html",
        context,
    )


# ------------------------------
# PO PROCESS EXPORT TO EXCEL
# ------------------------------
@login_required_view
def po_process_excel(request, po_id):
    po = get_object_or_404(PurchaseOrder, pk=po_id)

    processes = po.processes.select_related(
        "department_process",
        "current_status",
        "last_updated_by",
    ).order_by(
        "department_process__sequence",
    )

    filename = f"PO_{po.po_number}_processes.xls"

    # Render HTML table
    html = render_to_string(
        "po/po_process_excel.html",
        {
            "po": po,
            "processes": processes,
        },
    )

    # Excel headers (PHP-style)
    response = HttpResponse(html)
    response["Content-Type"] = "application/vnd.ms-excel"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    response["Pragma"] = "no-cache"
    response["Expires"] = "0"

    return response


@login_required_view
def po_report_summary_excel(request):
    today = datetime.today().date()
    date_from = request.GET.get("date_from") or today.strftime("%Y-%m-%d")
    date_to = request.GET.get("date_to") or today.strftime("%Y-%m-%d")

    base_filters = {"po_date__range": [date_from, date_to]}

    if request.GET.get("po_number"):
        base_filters["po_number"] = request.GET["po_number"]

    if request.GET.get("oa_number"):
        base_filters["oa_number"] = request.GET["oa_number"]

    if request.GET.get("company"):
        base_filters["company_id"] = request.GET["company"]

    if request.GET.get("po_status"):
        base_filters["po_status"] = request.GET["po_status"]

    pos = (
        PurchaseOrder.objects.select_related("company", "created_by")
        .filter(**base_filters)
        .annotate(
            total_quantity=Coalesce(
                Sum("items__quantity_value"),
                Value(0),
                output_field=DecimalField(max_digits=12, decimal_places=3),
            ),
            total_value=Coalesce(
                Sum("items__material_value"),
                Value(0),
                output_field=DecimalField(max_digits=12, decimal_places=2),
            ),
        )
        .order_by("-id")
    )

    html = render_to_string(
        "po/po_report_summary_excel.html",
        {
            "pos": pos,
            "can_view_value": can_view_value(request.user),
        },
    )

    response = HttpResponse(html)
    response["Content-Type"] = "application/vnd.ms-excel"
    response["Content-Disposition"] = (
        f'attachment; filename="PO_Summary_Report_{date_from}_to_{date_to}.xls"'
    )
    response["Pragma"] = "no-cache"
    response["Expires"] = "0"
    return response


@login_required_view
def po_report_item_excel(request):
    today = datetime.today().date()
    date_from = request.GET.get("date_from") or today.strftime("%Y-%m-%d")
    date_to = request.GET.get("date_to") or today.strftime("%Y-%m-%d")

    base_filters = {"purchase_order__po_date__range": [date_from, date_to]}

    if request.GET.get("po_number"):
        base_filters["purchase_order_id"] = request.GET["po_number"]

    if request.GET.get("oa_number"):
        base_filters["purchase_order_id"] = request.GET["oa_number"]

    if request.GET.get("company"):
        base_filters["purchase_order__company_id"] = request.GET["company"]

    if request.GET.get("po_status"):
        base_filters["purchase_order__po_status"] = request.GET["po_status"]

    items = (
        PurchaseOrderItem.objects.select_related(
            "purchase_order",
            "purchase_order__company",
            "purchase_order__created_by",
        )
        .filter(**base_filters)
        .order_by("purchase_order__id")
    )

    grand_totals = items.aggregate(
        total_quantity=Coalesce(
            Sum("quantity_value"),
            Value(0),
            output_field=DecimalField(max_digits=12, decimal_places=3),
        ),
        total_value=Coalesce(
            Sum("material_value"),
            Value(0),
            output_field=DecimalField(max_digits=12, decimal_places=2),
        ),
    )

    html = render_to_string(
        "po/po_report_item_excel.html",
        {
            "items": items,
            "grand_totals": grand_totals,
            "can_view_value": can_view_value(request.user),
        },
    )

    response = HttpResponse(html)
    response["Content-Type"] = "application/vnd.ms-excel"
    response["Content-Disposition"] = (
        f'attachment; filename="PO_Item_Report_{date_from}_to_{date_to}.xls"'
    )
    response["Pragma"] = "no-cache"
    response["Expires"] = "0"
    return response


@login_required_view
def po_list(request):
    query = request.GET.get("q", "").strip()

    qs = PurchaseOrder.objects.select_related("created_by", "company").prefetch_related(
        "items"
    )

    if query:
        qs = qs.filter(
            Q(po_number__icontains=query)
            | Q(oa_number__icontains=query)
            | Q(company__name__icontains=query)
            | Q(items__material_code__icontains=query)
            | Q(items__material_description__icontains=query)
        )

    qs = (
        qs.annotate(
            creator_name=Coalesce(
                Concat(
                    F("created_by__first_name"),
                    Value(" "),
                    F("created_by__last_name"),
                ),
                F("created_by__username"),
                Value("—"),
                output_field=CharField(),
            ),
            total_quantity=Coalesce(
                Sum("items__quantity_value"),
                Value(0),
                output_field=DecimalField(max_digits=12, decimal_places=3),
            ),
            total_value=Coalesce(
                Sum("items__material_value"),
                Value(0),
                output_field=DecimalField(max_digits=12, decimal_places=2),
            ),
            # True (>0) if any BOM exists for this PO
            has_bom=Count("boms", distinct=True),
            # True (>0) if any Indent exists for this PO
            has_indent=Count("indents", distinct=True),
        )
        .distinct()
        .order_by("-id")
    )

    paginator = Paginator(qs, 20)
    page_obj = paginator.get_page(request.GET.get("page"))

    context = {
        "page_obj": page_obj,
        "q": query,
        "can_view_value": can_view_value(request.user),
    }

    return render(request, "po/po_list.html", context)


@login_required_view
def po_print(request, pk):
    po = get_object_or_404(
        PurchaseOrder.objects.select_related("company", "created_by").prefetch_related(
            "items"
        ),
        pk=pk,
    )
    return render(
        request,
        "po/po_print.html",
        {
            "po": po,
            "can_view_value": can_view_value(request.user),
        },
    )


@login_required_view
def ajax_po_items_list(request, pk):
    """
    Returns PO items as JSON for the items modal in po_list.
    GET /po/<pk>/ajax-items/
    """
    po = get_object_or_404(PurchaseOrder, pk=pk)
    show_value = can_view_value(request.user)

    items_qs = po.items.values(
        "material_code",
        "material_description",
        "quantity_value",
        "uom",
        "material_value",
        "status",
    )

    # Build status display map from model choices
    status_map = dict(PurchaseOrderItem.STATUS_CHOICES)

    data = []
    for item in items_qs:
        row = {
            "code": item["material_code"] or "—",
            "description": item["material_description"],
            "quantity": str(item["quantity_value"] or 0),
            "uom": item["uom"],
            "status": status_map.get(item["status"], item["status"]),
        }
        if show_value:
            val = item["material_value"]
            row["value"] = "{:.2f}".format(val) if val is not None else "—"
        data.append(row)

    return JsonResponse(
        {
            "items": data,
            "show_value": show_value,
            "po_number": po.po_number,
        }
    )


@login_required_view
def po_process_report(request):
    # ------------------------------
    # FILTER INPUTS
    # ------------------------------
    date_from = request.GET.get("date_from")
    date_to = request.GET.get("date_to")
    processes = request.GET.getlist("processes")
    po_status = request.GET.get("po_status")
    company = request.GET.get("company")
    po_number = request.GET.get("po_number")

    # ------------------------------
    # FILTER VALIDATION
    # ------------------------------
    filter_used = bool(processes and (date_from or date_to))

    rows = []

    if filter_used:
        process_qs = POProcess.objects.select_related(
            "purchase_order",
            "department_process",
            "current_status",
            "purchase_order__company",
        )

        # PROCESS FILTER
        process_qs = process_qs.filter(department_process_id__in=processes)

        # DATE FILTER
        if date_from:
            process_qs = process_qs.filter(purchase_order__po_date__gte=date_from)

        if date_to:
            process_qs = process_qs.filter(purchase_order__po_date__lte=date_to)

        # OTHER FILTERS
        if po_status:
            process_qs = process_qs.filter(purchase_order__po_status=po_status)

        if company:
            process_qs = process_qs.filter(purchase_order__company_id=company)

        if po_number:
            process_qs = process_qs.filter(
                purchase_order__po_number__icontains=po_number
            )

        process_qs = (
            process_qs.prefetch_related(
                "purchase_order__items",
                "item_statuses__status",
                "item_statuses__po_item",
            )
            .order_by(
                "purchase_order__id",
                "department_process__sequence",
            )
            .distinct()
        )

        # BUILD ROWS
        for process in process_qs:
            po = process.purchase_order
            items = po.items.all()

            status_map = {s.po_item_id: s for s in process.item_statuses.all()}

            for item in items:
                item_status_obj = status_map.get(item.id)

                if process.department_process.has_item_tracking:
                    status_name = (
                        item_status_obj.status.name if item_status_obj else item.status
                    )
                else:
                    status_name = process.current_status.name

                rows.append(
                    {
                        "po_id": po.id,
                        "po_number": po.po_number,
                        "po_date": po.po_date,
                        "company": po.company.name if po.company else "—",
                        "process": process.department_process.name,
                        "department": process.department_process.department,
                        "process_status": process.current_status.name,
                        "item_description": item.material_description,
                        "quantity": item.quantity_value,
                        "uom": item.uom,
                        "status": status_name,
                    }
                )

    # ------------------------------
    # PAGINATION
    # ------------------------------
    page_obj = None
    if filter_used:
        paginator = Paginator(rows, 50)
        page_obj = paginator.get_page(request.GET.get("page"))

    context = {
        "rows": page_obj,
        "page_obj": page_obj,
        "filter_used": filter_used,
        "process_list": DepartmentProcessMaster.objects.filter(is_active=True),
        "companies": CompanyMaster.objects.order_by("name"),
        "filters": {
            "date_from": date_from or "",
            "date_to": date_to or "",
            "processes": processes,
            "po_status": po_status or "",
            "company": company or "",
            "po_number": po_number or "",
        },
    }

    return render(request, "po/po_process_report.html", context)


@login_required_view
def po_process_report_excel(request):
    date_from = request.GET.get("date_from")
    date_to = request.GET.get("date_to")
    processes = request.GET.getlist("processes")
    po_status = request.GET.get("po_status")
    company = request.GET.get("company")
    po_number = request.GET.get("po_number")

    rows = []

    if processes and (date_from or date_to):

        process_qs = POProcess.objects.select_related(
            "purchase_order",
            "department_process",
            "current_status",
            "purchase_order__company",
        ).filter(department_process_id__in=processes)

        if date_from:
            process_qs = process_qs.filter(purchase_order__po_date__gte=date_from)

        if date_to:
            process_qs = process_qs.filter(purchase_order__po_date__lte=date_to)

        if po_status:
            process_qs = process_qs.filter(purchase_order__po_status=po_status)

        if company:
            process_qs = process_qs.filter(purchase_order__company_id=company)

        if po_number:
            process_qs = process_qs.filter(
                purchase_order__po_number__icontains=po_number
            )

        process_qs = (
            process_qs.prefetch_related(
                "purchase_order__items",
                "item_statuses__status",
                "item_statuses__po_item",
            )
            .order_by(
                "purchase_order__id",
                "department_process__sequence",
            )
            .distinct()
        )

        for process in process_qs:
            po = process.purchase_order
            items = po.items.all()

            status_map = {s.po_item_id: s for s in process.item_statuses.all()}

            for item in items:
                item_status_obj = status_map.get(item.id)

                if process.department_process.has_item_tracking:
                    status_name = (
                        item_status_obj.status.name if item_status_obj else item.status
                    )
                else:
                    status_name = process.current_status.name

                rows.append(
                    {
                        "po_number": po.po_number,
                        "po_date": po.po_date,
                        "company": po.company.name if po.company else "—",
                        "process": process.department_process.name,
                        "item_description": item.material_description,
                        "quantity": item.quantity_value,
                        "status": status_name,
                    }
                )

    # ------------------------------
    # RENDER EXCEL
    # ------------------------------
    html = render_to_string("po/po_process_report_excel.html", {"rows": rows})

    response = HttpResponse(html)
    response["Content-Type"] = "application/vnd.ms-excel"
    response["Content-Disposition"] = "attachment; filename=po_process_report.xls"

    return response


# =====================================================================================
# =====================================================================================
# =====================================================================================
# =====================================================================================
# =====================================================================================


# =====================================================================================
# AJAX PO ITEMS FOR TARGET
# =====================================================================================
@login_required_view
def ajax_po_items_for_target(request, po_id):
    po = get_object_or_404(PurchaseOrder, pk=po_id)

    # Get already targeted item ids for this PO if editing
    target_id = request.GET.get("target_id")
    selected_item_ids = []
    if target_id:
        selected_item_ids = list(
            POTargetItem.objects.filter(po_target_id=target_id).values_list(
                "po_item_id", flat=True
            )
        )

    items = po.items.values(
        "id",
        "material_code",
        "material_description",
        "quantity_value",
        "uom",
        "material_value",
    )
    data = [
        {
            "id": item["id"],
            "code": item["material_code"] or "—",
            "description": item["material_description"],
            "quantity": str(item["quantity_value"] or 0),
            "uom": item["uom"],
            "value": str(item["material_value"] or 0),
            "selected": item["id"] in selected_item_ids,
        }
        for item in items
    ]
    return JsonResponse({"items": data})


# =====================================================================================
# PO TARGET LIST
# =====================================================================================
@login_required_view
def po_target_list(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden()

    targets = (
        POTarget.objects.select_related("purchase_order", "purchase_order__company")
        .prefetch_related("target_items__po_item")
        .order_by("-year", "-month")
    )

    paginator = Paginator(targets, 20)
    page_obj = paginator.get_page(request.GET.get("page"))

    context = {
        "page_obj": page_obj,
    }
    return render(request, "po/po_target_list.html", context)


# =====================================================================================
# PO TARGET CREATE
# =====================================================================================
@login_required_view
def po_target_create(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden()

    form = POTargetForm()

    if request.method == "POST":
        form = POTargetForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            po = cd["purchase_order"]
            month = cd["month"]
            year = cd["year"]
            item_ids = cd["item_ids"]

            agg = PurchaseOrderItem.objects.filter(
                id__in=item_ids, purchase_order=po
            ).aggregate(
                total=Coalesce(
                    Sum("material_value"),
                    Value(0),
                    output_field=DecimalField(max_digits=15, decimal_places=2),
                )
            )

            with transaction.atomic():
                target = POTarget.objects.create(
                    purchase_order=po,
                    month=month,
                    year=year,
                    target_value=agg["total"],
                )
                POTargetItem.objects.bulk_create(
                    [POTargetItem(po_target=target, po_item_id=iid) for iid in item_ids]
                )

            messages.success(request, "Target created successfully.")
            return redirect("po:po_target_list")

    context = {
        "form": form,
        "title": "Create Target",
    }
    return render(request, "po/po_target_form.html", context)


# =====================================================================================
# PO TARGET EDIT
# =====================================================================================
@login_required_view
def po_target_edit(request, pk):
    if not request.user.is_superuser:
        return HttpResponseForbidden()

    target = get_object_or_404(
        POTarget.objects.select_related("purchase_order").prefetch_related(
            "target_items__po_item"
        ),
        pk=pk,
    )

    form = POTargetForm(
        instance=target,
        initial={
            "month": target.month,
            "year": target.year,
        },
    )

    if request.method == "POST":
        form = POTargetForm(request.POST, instance=target)
        if form.is_valid():
            cd = form.cleaned_data
            month = cd["month"]
            year = cd["year"]
            item_ids = cd["item_ids"]

            agg = PurchaseOrderItem.objects.filter(
                id__in=item_ids,
                purchase_order=target.purchase_order,
            ).aggregate(
                total=Coalesce(
                    Sum("material_value"),
                    Value(0),
                    output_field=DecimalField(max_digits=15, decimal_places=2),
                )
            )

            with transaction.atomic():
                target.month = month
                target.year = year
                target.target_value = agg["total"]
                target.save()

                # Replace old items with new selection
                target.target_items.all().delete()
                POTargetItem.objects.bulk_create(
                    [POTargetItem(po_target=target, po_item_id=iid) for iid in item_ids]
                )

            messages.success(request, "Target updated successfully.")
            return redirect("po:po_target_list")

    context = {
        "form": form,
        "target": target,
        "title": f"Edit Target — {target.purchase_order.po_number}",
    }
    return render(request, "po/po_target_form.html", context)


# =====================================================================================
# PO TARGET DELETE
# =====================================================================================
@login_required_view
def po_target_delete(request, pk):
    if not request.user.is_superuser:
        return HttpResponseForbidden()

    target = get_object_or_404(POTarget, pk=pk)

    if request.method == "POST":
        target.delete()
        messages.success(request, "Target deleted successfully.")
        return redirect("po:po_target_list")

    return redirect("po:po_target_list")


# =====================================================================================
# PO TARGET REPORT
# =====================================================================================
@login_required_view
def po_target_report(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden()

    from .models import MONTH_CHOICES

    month = request.GET.get("month")
    year = request.GET.get("year")

    filter_used = bool(month and year)

    data = []
    total_target = 0
    total_achieved = 0

    if filter_used:
        qs = (
            POTarget.objects.select_related("purchase_order", "purchase_order__company")
            .prefetch_related("target_items__po_item")
            .filter(month=month, year=year)
        )

        month_name_map = dict(MONTH_CHOICES)

        for target in qs:
            po = target.purchase_order

            achieved = PurchaseOrderItem.objects.filter(
                id__in=target.target_items.values_list("po_item_id", flat=True),
                status="COMPLETED",
            ).aggregate(
                total=Coalesce(
                    Sum("material_value"),
                    Value(0),
                    output_field=DecimalField(max_digits=15, decimal_places=2),
                )
            )[
                "total"
            ]

            target_val = target.target_value or 0
            pct = (achieved / target_val * 100) if target_val > 0 else 0

            total_target += target_val
            total_achieved += achieved

            data.append(
                {
                    "po_number": po.po_number,
                    "company": po.company.name if po.company else "—",
                    "month": month_name_map.get(target.month, target.month),
                    "year": target.year,
                    "target": target_val,
                    "achieved": achieved,
                    "percentage": round(pct, 2),
                    "items": [ti.po_item for ti in target.target_items.all()],
                }
            )

    overall_pct = (total_achieved / total_target * 100) if total_target > 0 else 0

    context = {
        "data": data,
        "filter_used": filter_used,
        "total_target": total_target,
        "total_achieved": total_achieved,
        "overall_percentage": round(overall_pct, 2),
        "filters": {
            "month": month or "",
            "year": year or "",
        },
        "month_choices": MONTH_CHOICES,
    }

    return render(request, "po/po_target_report.html", context)


# =====================================================================================
# PO TARGET REPORT
# =====================================================================================
@login_required_view
def po_target_report_excel(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden()

    from .models import MONTH_CHOICES

    month = request.GET.get("month")
    year = request.GET.get("year")

    data = []

    if month and year:
        qs = (
            POTarget.objects.select_related("purchase_order", "purchase_order__company")
            .prefetch_related("target_items__po_item")
            .filter(month=month, year=year)
        )

        month_name_map = dict(MONTH_CHOICES)

        for target in qs:
            po = target.purchase_order

            achieved = PurchaseOrderItem.objects.filter(
                id__in=target.target_items.values_list("po_item_id", flat=True),
                status="COMPLETED",
            ).aggregate(
                total=Coalesce(
                    Sum("material_value"),
                    Value(0),
                    output_field=DecimalField(max_digits=15, decimal_places=2),
                )
            )[
                "total"
            ]

            target_val = target.target_value or 0
            pct = (achieved / target_val * 100) if target_val > 0 else 0

            data.append(
                {
                    "po_number": po.po_number,
                    "company": po.company.name if po.company else "—",
                    "month": month_name_map.get(target.month, target.month),
                    "year": target.year,
                    "target": target_val,
                    "achieved": achieved,
                    "percentage": round(pct, 2),
                    "items": [ti.po_item for ti in target.target_items.all()],
                }
            )

    html = render_to_string(
        "po/po_target_report_excel.html",
        {"data": data},
    )

    response = HttpResponse(html)
    response["Content-Type"] = "application/vnd.ms-excel"
    response["Content-Disposition"] = (
        f'attachment; filename="PO_Target_Report_{month}_{year}.xls"'
    )
    response["Pragma"] = "no-cache"
    response["Expires"] = "0"
    return response


# =====================================================================================
# PO TARGET YEARLY REPORT  (month-wise for a selected year)
# Add these two functions inside po/views.py
# =====================================================================================


@login_required_view
def po_target_yearly_report(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden()

    year = request.GET.get("year", "").strip()
    filter_used = bool(year)

    SHORT_MONTHS = [
        "Jan",
        "Feb",
        "Mar",
        "Apr",
        "May",
        "Jun",
        "Jul",
        "Aug",
        "Sep",
        "Oct",
        "Nov",
        "Dec",
    ]

    data = []
    total_target = Decimal("0")
    total_achieved = Decimal("0")

    if filter_used:
        try:
            year_int = int(year)
        except ValueError:
            filter_used = False
            year_int = None

        if filter_used:
            # Build a row for every month 1-12
            for month_num in range(1, 13):
                # Sum all POTarget rows for this month/year
                targets_qs = POTarget.objects.filter(month=month_num, year=year_int)

                month_target = targets_qs.aggregate(
                    total=Coalesce(
                        Sum("target_value"),
                        Value(0),
                        output_field=DecimalField(max_digits=15, decimal_places=2),
                    )
                )["total"]

                # Sum achieved (COMPLETED items) linked to those targets
                target_ids = targets_qs.values_list("id", flat=True)
                item_ids = POTargetItem.objects.filter(
                    po_target_id__in=target_ids
                ).values_list("po_item_id", flat=True)

                month_achieved = PurchaseOrderItem.objects.filter(
                    id__in=item_ids, status="COMPLETED"
                ).aggregate(
                    total=Coalesce(
                        Sum("material_value"),
                        Value(0),
                        output_field=DecimalField(max_digits=15, decimal_places=2),
                    )
                )[
                    "total"
                ]

                pct = (
                    round(month_achieved / month_target * 100, 2)
                    if month_target > 0
                    else 0
                )

                total_target += month_target
                total_achieved += month_achieved

                data.append(
                    {
                        "month_num": month_num,
                        "month_name": SHORT_MONTHS[month_num - 1],
                        "year": year_int,
                        "target": month_target,
                        "achieved": month_achieved,
                        "percentage": pct,
                    }
                )

    overall_pct = (
        round(total_achieved / total_target * 100, 2) if total_target > 0 else 0
    )

    context = {
        "data": data,
        "filter_used": filter_used,
        "year": year,
        "total_target": total_target,
        "total_achieved": total_achieved,
        "overall_percentage": overall_pct,
    }

    return render(request, "po/po_target_yearly_report.html", context)


# =====================================================================================
# PO TARGET YEARLY REPORT — EXCEL EXPORT
# =====================================================================================
@login_required_view
def po_target_yearly_report_excel(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden()

    year = request.GET.get("year", "").strip()

    SHORT_MONTHS = [
        "Jan",
        "Feb",
        "Mar",
        "Apr",
        "May",
        "Jun",
        "Jul",
        "Aug",
        "Sep",
        "Oct",
        "Nov",
        "Dec",
    ]

    data = []
    total_target = Decimal("0")
    total_achieved = Decimal("0")

    if year:
        try:
            year_int = int(year)
        except ValueError:
            year_int = None

        if year_int:
            for month_num in range(1, 13):
                targets_qs = POTarget.objects.filter(month=month_num, year=year_int)

                month_target = targets_qs.aggregate(
                    total=Coalesce(
                        Sum("target_value"),
                        Value(0),
                        output_field=DecimalField(max_digits=15, decimal_places=2),
                    )
                )["total"]

                target_ids = targets_qs.values_list("id", flat=True)
                item_ids = POTargetItem.objects.filter(
                    po_target_id__in=target_ids
                ).values_list("po_item_id", flat=True)

                month_achieved = PurchaseOrderItem.objects.filter(
                    id__in=item_ids, status="COMPLETED"
                ).aggregate(
                    total=Coalesce(
                        Sum("material_value"),
                        Value(0),
                        output_field=DecimalField(max_digits=15, decimal_places=2),
                    )
                )[
                    "total"
                ]

                pct = (
                    round(month_achieved / month_target * 100, 2)
                    if month_target > 0
                    else 0
                )

                total_target += month_target
                total_achieved += month_achieved

                data.append(
                    {
                        "month_name": SHORT_MONTHS[month_num - 1],
                        "year": year_int,
                        "target": month_target,
                        "achieved": month_achieved,
                        "percentage": pct,
                    }
                )

    overall_pct = (
        round(total_achieved / total_target * 100, 2) if total_target > 0 else 0
    )

    html = render_to_string(
        "po/po_target_yearly_report_excel.html",
        {
            "data": data,
            "year": year,
            "total_target": total_target,
            "total_achieved": total_achieved,
            "overall_percentage": overall_pct,
        },
    )

    response = HttpResponse(html)
    response["Content-Type"] = "application/vnd.ms-excel"
    response["Content-Disposition"] = (
        f'attachment; filename="Target_Revenue_Yearly_{year}.xls"'
    )
    response["Pragma"] = "no-cache"
    response["Expires"] = "0"
    return response


# =====================================================================================
# PO COMMENTS — LOAD & SAVE (Admin Only)
# =====================================================================================


@login_required_view
def po_comments_api(request, po_id):
    """
    GET  → returns all items with their existing comments for this PO
    POST → saves/updates a comment for a specific PO item
    """
    from suntech_erp.permissions import is_admin

    if not is_admin(request.user):
        return JsonResponse({"error": "Unauthorized"}, status=403)

    po = get_object_or_404(PurchaseOrder, pk=po_id)

    if request.method == "GET":
        items = po.items.all().order_by("id")

        # Build a map of po_item_id → comment
        existing = {
            c.po_item_id: {"id": c.id, "comment": c.comment}
            for c in POComment.objects.filter(purchase_order=po)
        }

        data = [
            {
                "id": item.id,
                "material_code": item.material_code or "—",
                "material_description": item.material_description,
                "quantity_value": str(item.quantity_value or 0),
                "uom": item.uom,
                "comment_id": existing.get(item.id, {}).get("id"),
                "comment": existing.get(item.id, {}).get("comment", ""),
            }
            for item in items
        ]

        return JsonResponse({"po_number": po.po_number, "items": data})

    if request.method == "POST":
        try:
            body = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        po_item_id = body.get("po_item_id")
        comment_text = body.get("comment", "").strip()

        if not po_item_id:
            return JsonResponse({"error": "po_item_id is required"}, status=400)

        po_item = get_object_or_404(PurchaseOrderItem, pk=po_item_id, purchase_order=po)

        obj, created = POComment.objects.update_or_create(
            purchase_order=po,
            po_item=po_item,
            defaults={
                "comment": comment_text,
                "commented_by": request.user,
            },
        )

        return JsonResponse(
            {
                "success": True,
                "created": created,
                "comment_id": obj.id,
                "comment": obj.comment,
            }
        )

    return JsonResponse({"error": "Method not allowed"}, status=405)
