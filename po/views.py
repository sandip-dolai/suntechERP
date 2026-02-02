from django.db.models import (
    F,
    Q,
    Value,
    CharField,
    OuterRef,
    Subquery,
    Sum,
    DecimalField,
)
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from suntech_erp.permissions import login_required_view, admin_required
from django.db import transaction, IntegrityError

from django.db.models.functions import Concat, Coalesce, TruncMonth
from .models import PurchaseOrder, PurchaseOrderItem, POProcess, POProcessHistory
from .forms import PurchaseOrderForm, PurchaseOrderItemFormSet, POProcessUpdateForm
from master.models import CompanyMaster
from datetime import datetime
from django.http import HttpResponseForbidden, HttpResponse
from django.template.loader import render_to_string
import json


def can_view_value(user):
    return user.is_superuser or getattr(user, "department", None) == "Admin"


# ------------------------------
# PO CREATE (header + items)
# ------------------------------
@login_required_view
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


# ------------------------------
# PO DELETE
# ------------------------------
@login_required_view
def po_delete(request, pk):
    po = get_object_or_404(PurchaseOrder, pk=pk)

    if request.method == "POST":
        po.po_status = "CANCELLED"
        po.save()

        messages.warning(request, "Purchase Order cancelled (not deleted).")
        return redirect("po:po_list")

    return render(request, "po/po_delete.html", {"po": po})


@login_required_view
def po_report(request):
    # ------------------------------
    # VIEW MODE
    # ------------------------------
    view_mode = request.GET.get("view", "summary").lower()

    # ------------------------------
    # 🔹 GLOBAL SUMMARY (NOT FILTERED)
    # ------------------------------
    all_pos = PurchaseOrder.objects.all()

    total_po_count = all_pos.count()
    completed_po_count = all_pos.filter(po_status="COMPLETED").count()
    pending_po_count = total_po_count - completed_po_count

    # Annotate PO total value
    po_value_qs = all_pos.annotate(
        total_value=Coalesce(
            Sum("items__material_value"),
            Value(0),
            output_field=DecimalField(max_digits=12, decimal_places=2),
        )
    )

    # Total PO Value
    total_po_value = po_value_qs.aggregate(
        total=Coalesce(
            Sum("total_value"),
            Value(0),
            output_field=DecimalField(max_digits=12, decimal_places=2),
        )
    )["total"]

    # Dispatched PO Value (COMPLETED POs)
    dispatched_po_value = po_value_qs.filter(po_status="COMPLETED").aggregate(
        total=Coalesce(
            Sum("total_value"),
            Value(0),
            output_field=DecimalField(max_digits=12, decimal_places=2),
        )
    )["total"]

    pending_po_value = total_po_value - dispatched_po_value

    dispatch_percentage = (
        (dispatched_po_value / total_po_value) * 100 if total_po_value > 0 else 0
    )

    # ------------------------------
    # FILTERS (FOR TABLE ONLY)
    # ------------------------------
    today = datetime.today().date()
    date_from = request.GET.get("date_from") or today.strftime("%Y-%m-%d")
    date_to = request.GET.get("date_to") or today.strftime("%Y-%m-%d")

    filter_used = (
        "po_number" in request.GET
        or "oa_number" in request.GET
        or "company" in request.GET
        or "date_from" in request.GET
        or "po_status" in request.GET
    )

    base_filters = {"po_date__range": [date_from, date_to]}

    if request.GET.get("po_number"):
        base_filters["id"] = request.GET["po_number"]

    if request.GET.get("oa_number"):
        base_filters["id"] = request.GET["oa_number"]

    if request.GET.get("company"):
        base_filters["company_id"] = request.GET["company"]

    if request.GET.get("po_status"):
        base_filters["po_status"] = request.GET["po_status"]

    # ------------------------------
    # CHART DATA (FILTERED)
    # ------------------------------
    chart_data = []

    if filter_used:
        chart_qs = (
            PurchaseOrder.objects.filter(**base_filters)
            .annotate(month=TruncMonth("po_date"))
            .values("month")
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
            .order_by("month")
        )

        for row in chart_qs:
            chart_data.append(
                {
                    "month": row["month"].strftime("%b %Y"),
                    "quantity": float(row["total_quantity"]),
                    "value": float(row["total_value"]),
                }
            )

    # ------------------------------
    # PO LIST (FILTERED)
    # ------------------------------
    po_qs = PurchaseOrder.objects.none()

    if filter_used:
        po_qs = (
            PurchaseOrder.objects.select_related("created_by", "company")
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
        )

    # ------------------------------
    # ITEM VIEW (FILTERED)
    # ------------------------------
    items = None
    grand_totals = None

    if view_mode == "items" and filter_used:
        items = PurchaseOrderItem.objects.select_related(
            "purchase_order", "purchase_order__company"
        ).filter(purchase_order__in=po_qs)

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

    # ------------------------------
    # CONTEXT
    # ------------------------------
    context = {
        # View
        "view": view_mode,
        # Summary (GLOBAL)
        "summary": {
            "total_po_count": total_po_count,
            "completed_po_count": completed_po_count,
            "pending_po_count": pending_po_count,
            "total_po_value": total_po_value,
            "dispatched_po_value": dispatched_po_value,
            "pending_po_value": pending_po_value,
            "dispatch_percentage": round(dispatch_percentage, 2),
        },
        # Table Data
        "pos": po_qs,
        "items": items,
        "grand_totals": grand_totals,
        # Filters
        "filter_used": filter_used,
        "companies": CompanyMaster.objects.order_by("name"),
        "po_list": PurchaseOrder.objects.order_by("-id"),
        "filters": {
            "po_number": request.GET.get("po_number", ""),
            "oa_number": request.GET.get("oa_number", ""),
            "company": request.GET.get("company", ""),
            "po_status": request.GET.get("po_status", ""),
            "date_from": date_from,
            "date_to": date_to,
        },
        # Permissions
        "can_view_value": can_view_value(request.user),
        # Chart
        "chart_data": json.dumps(chart_data),
    }

    return render(request, "po/po_report.html", context)


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

    return render(
        request,
        "po/po_process_list.html",
        {
            "po": po,
            "processes": processes,
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
    if user.is_superuser or user.is_staff:
        return True

    return getattr(user, "department", None) == po_process.department_process.department


@login_required_view
def po_process_update(request, process_id):
    po_process = get_object_or_404(POProcess, pk=process_id)
    po = po_process.purchase_order

    # 🔐 Permission check
    if not can_edit_po_process(request.user, po_process):
        return HttpResponseForbidden(
            "You do not have permission to update this process."
        )

    if request.method == "POST":
        form = POProcessUpdateForm(
            request.POST,
            instance=po_process,
            user=request.user,
        )
        if form.is_valid():
            form.save()
            messages.success(request, "Process status updated successfully.")
            return redirect(
                "po:po_process_list",
                po_id=po.id,
            )
    else:
        form = POProcessUpdateForm(
            instance=po_process,
            user=request.user,
        )

    context = {
        "form": form,
        "po": po,
        "po_process": po_process,
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

    context = {
        "po": po,
        "po_process": po_process,
        "history": history,
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
        base_filters["id"] = request.GET["po_number"]

    if request.GET.get("oa_number"):
        base_filters["id"] = request.GET["oa_number"]

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

    pos = PurchaseOrder.objects.select_related(
        "created_by", "company"
    ).prefetch_related("items")

    if query:
        pos = pos.filter(
            Q(po_number__icontains=query)
            | Q(oa_number__icontains=query)
            | Q(company__name__icontains=query)
            | Q(items__material_code__icontains=query)
            | Q(items__material_description__icontains=query)
        )

    pos = (
        pos.annotate(
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
        )
        .distinct()
        .order_by("-id")
    )

    context = {
        "pos": pos,
        "search_query": query,
        "can_view_value": can_view_value(request.user),
    }

    return render(request, "po/po_list.html", context)
