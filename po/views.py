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
)
from .forms import PurchaseOrderForm, PurchaseOrderItemFormSet, POProcessUpdateForm
from master.models import CompanyMaster, ProcessStatusMaster
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
@login_required_view
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


@login_required_view
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

        agg = po_qs.aggregate(
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
        paginator = Paginator(po_qs, 20)
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
    date_to   = request.GET.get("date_to")   or today.strftime("%Y-%m-%d")
 
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
            "pos":           pos,
            "total_qty":     agg["total_qty"],
            "total_value":   agg["total_value"],
            "can_view_value": can_view_value(request.user),
        },
    )
 
    response = HttpResponse(html)
    response["Content-Type"]        = "application/vnd.ms-excel"
    response["Content-Disposition"] = (
        f'attachment; filename="PO_Summary_{date_from}_to_{date_to}.xls"'
    )
    response["Pragma"]  = "no-cache"
    response["Expires"] = "0"
    return response


# ==============================================================
# PO REPORT ITEM EXCEL (updated with department filter)
# ==============================================================
@login_required_view
def po_report_item_excel(request):
    today = datetime.today().date()
    date_from = request.GET.get("date_from") or today.strftime("%Y-%m-%d")
    date_to   = request.GET.get("date_to")   or today.strftime("%Y-%m-%d")
 
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
            "items":          items,
            "grand_totals":   grand_totals,
            "can_view_value": can_view_value(request.user),
        },
    )
 
    response = HttpResponse(html)
    response["Content-Type"]        = "application/vnd.ms-excel"
    response["Content-Disposition"] = (
        f'attachment; filename="PO_Items_{date_from}_to_{date_to}.xls"'
    )
    response["Pragma"]  = "no-cache"
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
